#include "video_decoder.hpp"
#include "cuda_context.hpp"
#include "PyCAIMemoryView.hpp"
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
 VideoDecoder::VideoDecoder(int gpuid, const std::string& codec)
    : cuda_ctx(gpuid),
      codec_type(AV_CODEC_ID_HEVC),
      fmt_ctx_(nullptr),
      pkt(nullptr),
      pktFiltered(nullptr)
{
    // Parse codec type
    if (codec == "h265") {
        codec_type = AV_CODEC_ID_HEVC;
    } else if (codec == "h264") {
        codec_type = AV_CODEC_ID_H264;
    } else if (codec == "av1") {
        codec_type = AV_CODEC_ID_AV1;
    } else if (codec == "vp9") {
        codec_type = AV_CODEC_ID_VP9;
    } else {
        throw std::runtime_error("Unsupported codec type: " + codec);
    }

    if (codec_id_ == AV_CODEC_ID_NONE)
        throw std::invalid_argument("Unsupported codec: " + codec);

    // Initialize decoder instance
    decoder = new NvDecoder(
        cuda_ctx,
        true,    // Use device frame buffer
        FFmpeg2NvCodecId(codec_type),
        true     // Low-latency mode
    );

    // Allocate packet memory
    pkt = av_packet_alloc();
    pktFiltered = av_packet_alloc();
    if (!pkt || !pktFiltered) {
        throw std::runtime_error("Failed to allocate AV packets");
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

    if (pkt) {
        av_packet_free(&pkt);
        std::cout << "VideoDecoder: AVPacket released\n";
    }

    // if (decoder_core_) {
    //     delete decoder_core_;
    //     std::cout << "VideoDecoder: DecoderCore released\n";
    // }
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
    DecodedFrame resultFrame;
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

    try {
        std::vector<DecodedFrame> decodedFrames;
        int64_t current_pts = 0;
        std::vector<std::tuple<CUdeviceptr, int64_t>> frameData;

        // Frame reading loop
        while (av_read_frame(fmt_ctx_, pkt) >= 0) {
            // Clean filtered packet
            if (pktFiltered->data) {
                av_packet_unref(pktFiltered);
            }

            // Skip non-video packets
            if (pkt->stream_index != video_stream_idx) {
                av_packet_unref(pkt);
                continue;
            }

            // Check timestamp boundary
            if (pkt->pts > target_pts) {
                av_packet_unref(pkt);
                break;
            }

            current_pts = pkt->pts;

            // Strict restoration of original filtering logic
            AVPacket* processed_pkt = pkt;
            // Process video packet (bitstream filtering for H.264/H.265)
            if (codec_type == AV_CODEC_ID_H264 || codec_type == AV_CODEC_ID_HEVC) {
                ck(av_bsf_send_packet(bsf_ctx_, pkt));
                ck(av_bsf_receive_packet(bsf_ctx_, pktFiltered));
                frameData = decoder->VideoDecode(pktFiltered->data, pktFiltered->size, CUVID_PKT_ENDOFPICTURE);
            } else {
                frameData = decoder->VideoDecode(pkt->data, pkt->size, CUVID_PKT_ENDOFPICTURE);
            }

            // Convert decoded data to frame structure
            std::transform(
                frameData.begin(),
                frameData.end(),
                std::back_inserter(decodedFrames),
                [=](std::tuple<CUdeviceptr, int64_t> tup) {
                    DecodedFrame frame;
                    // Get decoder parameters
                    const size_t width = decoder->GetWidth();
                    const size_t height = decoder->GetHeight();
                    const CUdeviceptr data_ptr = std::get<0>(tup);
                    const int64_t timestamp = std::get<1>(tup);

                    // Build YUV memory view
                    frame.timestamp = timestamp;
                    // Y component view
                    frame.views.push_back(CAIMemoryView{
                        {height, width, 1},         // Shape
                        {width, 1, 1},             // Strides
                        "|u1",                     // Data type
                        reinterpret_cast<size_t>(decoder->GetStream()),  // Stream ID
                        data_ptr,                  // Data pointer
                        false                      // Read-only flag
                    });
                    // UV component view (assumes contiguous memory)
                    frame.views.push_back(CAIMemoryView{
                        {height/2, width/2, 2},    // Shape
                        {width/2*2, 2, 1},         // Strides
                        "|u1",                     // Data type
                        reinterpret_cast<size_t>(decoder->GetStream()),
                        data_ptr + width * height,  // UV offset
                        false
                    });

                    // Load DLPack data (original implementation preserved)
                    std::vector<size_t> dl_shape{ static_cast<size_t>(height * 1.5), width };
                    std::vector<size_t> dl_stride{ width, 1 };
                    frame.extBuf->LoadDLPack(dl_shape, dl_stride, "|u1", gpuId,
                                           reinterpret_cast<size_t>(decoder->GetStream()),
                                           data_ptr, false);
                    return frame;
                }
            );
        }

        // Cleanup resources
        avformat_close_input(&fmt_ctx_);
        if (bsf_ctx_) {
            av_bsf_free(&bsf_ctx_);
        }

        // Validate decoding results
        if (decodedFrames.empty()) {
            throw std::runtime_error("No frames decoded");
        }
        return decodedFrames[0];

    } catch (...) {
        // Cleanup on exception
        avformat_close_input(&fmt_ctx_);
        if (bsf_ctx_) {
            av_bsf_free(&bsf_ctx_);
        }
        throw std::runtime_error("Decoding process failed");
    }

    return resultFrame;  // Fallback return (should not be reached in practice)
}
