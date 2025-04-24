#include "video_decoder.hpp"
#include "cuda_context.hpp"
#include "Logger.h"

// Global logger instance initialization
simplelogger::Logger *logger = simplelogger::LoggerFactory::CreateConsoleLogger();


/**
 * @brief Decodes the given encoded video data using NvDecoder.
 *
 * This function decodes the provided encoded video data and returns a vector of tuples
 * where each tuple contains a CUdeviceptr to the decoded frame data and its corresponding timestamp.
 * It also pre-allocates memory for performance optimization and validates the output format of the decoded frames.
 *
 * @param encodedData Pointer to the encoded video data.
 * @param dataSize Size of the encoded video data.
 * @param decodeFlags Decoding flags.
 * @return A vector of tuples containing CUdeviceptr and timestamp of the decoded frames.
 * @throws std::runtime_error if an unsupported video format is encountered during the decoding process.
 */
std::vector<std::tuple<CUdeviceptr, int64_t>> NvDecoder::VideoDecode(
    const uint8_t* encodedData,
    int dataSize,
    int decodeFlags)
{
    const int numFrames = this->Decode(encodedData, dataSize, decodeFlags);
    std::vector<std::tuple<CUdeviceptr, int64_t>> decodedFrames;
    decodedFrames.reserve(numFrames);  // Pre-allocate memory for performance optimization

    for (int frameIndex = 0; frameIndex < numFrames; ++frameIndex) {
        // Retrieve frame data and timestamp
        int64_t timestamp = 0;
        CUdeviceptr frameData = reinterpret_cast<CUdeviceptr>(this->GetFrame(&timestamp));

        // Validate output format compatibility
        const auto outputFormat = this->GetOutputFormat();
        switch (outputFormat) {
            case cudaVideoSurfaceFormat_NV12:
            case cudaVideoSurfaceFormat_P016:
            case cudaVideoSurfaceFormat_YUV444:
            case cudaVideoSurfaceFormat_YUV444_16Bit:
                // Supported base formats, no special handling needed
                break;

            default:
                throw std::runtime_error("Unsupported video format: "
                    + std::to_string(static_cast<int>(outputFormat)));
        }

        decodedFrames.emplace_back(frameData, timestamp);
    }

    return decodedFrames;
}


/**
 * @brief Constructor for VideoDecoder.
 *
 * Initializes the VideoDecoder with the specified GPU ID and codec type.
 * It maps the codec string to the appropriate AVCodecID, validates the codec,
 * and initializes the DecoderCore with the corresponding CUDA context and codec ID.
 *
 * @param gpuid The GPU device ID (0-based index) to be used for CUDA operations.
 * @param codec A string representing the video codec (e.g., "h264", "h265", "vp9", "av1").
 * @throws std::invalid_argument if an unsupported codec is provided.
 * @throws std::runtime_error if there is an issue during the initialization of DecoderCore.
 */
VideoDecoder::VideoDecoder(int gpuid, std::string codec)
    : cuda_ctx(gpuid),
      codec_type(codec),
      fmt_ctx_(nullptr),
      decoder_core_(nullptr)
{
    // Initialize codec type mapping
    codec_id_ = codec == "h264" ? AV_CODEC_ID_H264 :
                codec == "h265" ? AV_CODEC_ID_HEVC :
                codec == "vp9"  ? AV_CODEC_ID_VP9  :
                codec == "av1"  ? AV_CODEC_ID_AV1  : AV_CODEC_ID_NONE;

    if (codec_id_ == AV_CODEC_ID_NONE)
        throw std::invalid_argument("Unsupported codec: " + codec);

    // Initialize the decoder core (pass the CUDA context)
    try {
        decoder_core_ = new DecoderCore(cuda_ctx.get_cu_context(), codec_id_);
    } catch (const std::exception& e) {
        throw std::runtime_error("DecoderCore initialization failed: " + std::string(e.what()));
    }
}

/**
 * @brief Destructor for VideoDecoder.
 *
 * Frees all the allocated resources including AVFormatContext, Bitstream filter context, AVPacket, and DecoderCore.
 * Logs the release of each resource.
 */
// Destructor: Release all resources
VideoDecoder::~VideoDecoder() {
    if (fmt_ctx_) {
        avformat_close_input(&fmt_ctx_);
        std::cout << "VideoDecoder: AVFormatContext released\n";
    }

    if (bsf_ctx_) {
        av_bsf_free(&bsf_ctx_);
        std::cout << "VideoDecoder: Bitstream filter released\n";
    }

    if (pkt_) {
        av_packet_free(&pkt_);
        std::cout << "VideoDecoder: AVPacket released\n";
    }

    if (decoder_core_) {
        delete decoder_core_;
        std::cout << "VideoDecoder: DecoderCore released\n";
    }
}

/**
 * @brief The main decoding function for VideoDecoder.
 *
 * Performs the complete decoding process for a given video file.
 * It opens the file, finds the video stream, calculates the target PTS, seeks to the target frame,
 * initializes the bitstream filter if needed, and then decodes the frames until the target frame is found.
 *
 * @param path The path to the video file to be decoded.
 * @param target_frame The frame number that is the target for decoding.
 * @return A DecodedFrame object representing the target frame that was successfully decoded.
 * @throws std::runtime_error if there are issues such as file opening failure, decoding failure, or target frame not found.
 */
// Main decoding function
DecodedFrame VideoDecoder::decode(const std::string& path, int target_frame) {
    // Stage 1: File initialization and stream discovery
    fmt_ctx_ = FFmpegUtils::open_file(path.c_str());
    const int video_stream_idx = FFmpegUtils::find_video_stream(fmt_ctx_);
    AVStream* video_stream = fmt_ctx_->streams[video_stream_idx];

    // Stage 2: Calculate target PTS and seek
    const int64_t target_pts = FFmpegUtils::calculate_target_pts(video_stream, target_frame);
    FFmpegUtils::seek_to_frame(fmt_ctx_, video_stream_idx, target_pts);

    // Stage 3: Bitstream filter initialization
    bsf_ctx_ = FFmpegUtils::create_bitstream_filter(
        codec_id_,
        fmt_ctx_->streams[video_stream_idx]->codecpar
    );

    // Stage 4: Strict restoration of original decoding loop
    AVPacket* pkt = av_packet_alloc();
    AVPacket* pktFiltered = av_packet_alloc();
    DecodedFrame result_frame;
    bool frame_found = false;

    while (av_read_frame(fmt_ctx_, pkt) >= 0) {
        // Original filtered packet cleanup logic
        if (pktFiltered->data) {
            av_packet_unref(pktFiltered);
        }

        // Non-video stream processing (remain unchanged)
        if (pkt->stream_index != video_stream_idx) {
            av_packet_unref(pkt);
            continue;
        }

        // Original timestamp boundary check (critical restoration point)
        if (pkt->pts > target_pts) {
            av_packet_unref(pkt);
            break;
        }

        // Strict restoration of original filtering logic
        AVPacket* processed_pkt = pkt;
        if (codec_id_ == AV_CODEC_ID_H264 || codec_id_ == AV_CODEC_ID_HEVC) {
            if (av_bsf_send_packet(bsf_ctx_, pkt) < 0 ||
                av_bsf_receive_packet(bsf_ctx_, pktFiltered) < 0) {
                av_packet_unref(pkt);
                throw std::runtime_error("Bitstream filter failed");
            }
            processed_pkt = pktFiltered;
        }

        // Strict preservation of original decoding call (two parameters)
        auto frames = decoder_core_->decode_packet(
            processed_pkt->data,
            processed_pkt->size
        );

        // Original frame checking logic
        for (const auto& frame : frames) {
            if (frame.timestamp >= target_pts) {
                result_frame = frame;
                frame_found = true;
                goto cleanup;  // Preserve original break logic
            }
        }

        av_packet_unref(processed_pkt);
        av_packet_unref(pkt);
    }

cleanup:
    av_packet_free(&pkt);
    av_packet_free(&pktFiltered);

    if (!frame_found) {
        throw std::runtime_error("Target frame not found");
    }
    return result_frame;
}

/**
 * @brief Applies the bitstream filter to the given AVPacket.
 *
 * If the bitstream filter context exists, it sends the packet to the filter and receives the filtered packet.
 * If any operation fails, it throws a runtime error and frees the allocated resources.
 *
 * @param pkt Pointer to the AVPacket to be filtered.
 * @return A pointer to the filtered AVPacket, or the original packet if the bitstream filter context is not available.
 * @throws std::runtime_error if there are issues during the bitstream filter operations such as sending or receiving packets.
 */
// Private method: Apply the bitstream filter
AVPacket* VideoDecoder::apply_bitstream_filter(AVPacket* pkt) {
    if (!bsf_ctx_) return pkt;

    AVPacket* filtered_pkt = av_packet_alloc();
    try {
        if (av_bsf_send_packet(bsf_ctx_, pkt) < 0) {
            throw std::runtime_error("Failed to send packet to filter");
        }

        if (av_bsf_receive_packet(bsf_ctx_, filtered_pkt) < 0) {
            throw std::runtime_error("Failed to receive filtered packet");
        }

    } catch (...) {
        av_packet_free(&filtered_pkt);
        throw;
    }

    return filtered_pkt;
}
