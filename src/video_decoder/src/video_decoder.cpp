#include "core/PyCAIMemoryView.hpp"
extern "C" {
#include <libavformat/avformat.h>
}
#include "video_decoder.hpp"

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
    : gpuId(gpuid),
      codec(codec),
      codec_type(AV_CODEC_ID_HEVC),
      cu_ctx(nullptr),
      destroy(false),
      decoder(nullptr),
      fmt_ctx_(nullptr),
      pkt(nullptr),
      pktFiltered(nullptr) {
    // Initialize CUDA driver
    ck(cuInit(0));

    // Validate GPU device availability
    int device_count = 0;
    ck(cuDeviceGetCount(&device_count));
    if (gpuid < 0 || gpuid >= device_count) {
        throw std::invalid_argument("GPU ordinal out of range. Should be within [0, " + std::to_string(device_count - 1)
                                    + "]");
    }

    // Get or create CUDA context
    ck(cuCtxGetCurrent(&cu_ctx));
    if (!cu_ctx) {
        ck(cuCtxCreate(&cu_ctx, 0, gpuid));
        destroy = true;
    }

    // Parse codec type
    if (codec == "h265") {
        codec_type = AV_CODEC_ID_HEVC;
    }
    else if (codec == "h264") {
        codec_type = AV_CODEC_ID_H264;
    }
    else if (codec == "av1") {
        codec_type = AV_CODEC_ID_AV1;
    }
    else if (codec == "vp9") {
        codec_type = AV_CODEC_ID_VP9;
    }
    else {
        throw std::runtime_error("Unsupported codec type: " + codec);
    }

    // Initialize decoder instance
    decoder = new NvDecoder(cu_ctx,
                            true, // Use device frame buffer
                            FFmpeg2NvCodecId(codec_type),
                            true // Low-latency mode
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
    delete decoder;
    if (destroy) {
        cuCtxDestroy(cu_ctx);
    }
    if (pkt) {
        av_packet_free(&pkt);
        std::cout << "VideoDecoder: AVPacket released\n";
    }
    if (pktFiltered) {
        av_packet_free(&pktFiltered);
    }
}

/**
 * @brief Initializes and opens a video file for decoding.
 *
 * Initializes FFmpeg network protocols, opens the specified video file, and prepares
 * the decoding context. Allocates and manages the following resources:
 * - AVFormatContext for format I/O operations
 * - Bitstream filter context (implicitly via FFmpeg APIs)
 * - Stream information through probing
 *
 * @param videoPath Path to the video file or streaming URL (RTSP/RTMP supported)
 * @return AVFormatContext* Pointer to the initialized format context
 * @throws std::runtime_error If file opening, stream info retrieval, or video stream detection fails
 * @note The caller becomes responsible for closing the returned format context using
 *       avformat_close_input() when finished
 */
AVFormatContext* VideoDecoder::open(const std::string& videoPath) {
    // Initialize FFmpeg network protocols (for RTSP/RTMP streams)
    avformat_network_init();

    AVFormatContext* fmt_ctx = nullptr;

    // Attempt to open video file
    if (avformat_open_input(&fmt_ctx, videoPath.c_str(), nullptr, nullptr) < 0) {
        std::cout << "Can't open file " << videoPath << std::endl;
        throw std::runtime_error("Failed to open video file");
    }

    // Retrieve stream information (probes file format)
    if (avformat_find_stream_info(fmt_ctx, nullptr) < 0) {
        avformat_close_input(&fmt_ctx); // Cleanup allocated context
        throw std::runtime_error("Failed to retrieve stream information");
    }

    // Find best video stream index (auto-selects decoder)
    const int video_stream_idx = av_find_best_stream(fmt_ctx,            // Format context
                                                     AVMEDIA_TYPE_VIDEO, // Media type: video
                                                     -1,                 // Auto-select stream index
                                                     -1,                 // No related streams
                                                     nullptr,            // No codec specified
                                                     0                   // Reserved flags
    );

    // Verify valid video stream found
    if (video_stream_idx < 0) {
        avformat_close_input(&fmt_ctx);
        throw std::runtime_error("No video stream found in file");
    }

    return fmt_ctx;
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
 * @throws std::runtime_error if there are issues such as file opening failure, decoding failure, or target frame not
 * found.
 */
// Main decoding function
DecodedFrame VideoDecoder::decode(const std::string& videoPath, const int targetFrame) {
    DecodedFrame resultFrame;

    // Open video file and get format context
    AVFormatContext* fmt_ctx = open(videoPath);

    // Find video stream index (re-validate)
    const int video_stream_idx = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);
    if (video_stream_idx < 0) {
        avformat_close_input(&fmt_ctx);
        throw std::runtime_error("Video stream validation failed");
    }

    // Calculate target timestamp from frame number
    AVStream* video_stream = fmt_ctx->streams[video_stream_idx];
    const double fps = av_q2d(video_stream->avg_frame_rate); // Calculate FPS
    const double target_time = targetFrame / fps;           // Target time (seconds)
    const int64_t target_pts = av_rescale_q(                 // Convert timebase
        static_cast<int64_t>(target_time * AV_TIME_BASE),
        AV_TIME_BASE_Q,
        video_stream->time_base);

    // Seek to target position (backward search mode)
    if (av_seek_frame(fmt_ctx, video_stream_idx, target_pts, AVSEEK_FLAG_BACKWARD) < 0) {
        avformat_close_input(&fmt_ctx);
        throw std::runtime_error("Frame seek operation failed");
    }

    // Initialize bitstream filter (H.264/H.265 require annex B format conversion)
    const AVBitStreamFilter* bsf = nullptr;
    AVBSFContext* bsfc = nullptr;
    if (codec_type == AV_CODEC_ID_H264 || codec_type == AV_CODEC_ID_HEVC) {
        const char* filter_name = (codec_type == AV_CODEC_ID_H264) ? "h264_mp4toannexb" : "hevc_mp4toannexb";

        bsf = av_bsf_get_by_name(filter_name);
        if (!bsf) {
            throw std::runtime_error("Bitstream filter not available");
        }

        // Initialize filter context
        ck(av_bsf_alloc(bsf, &bsfc));
        avcodec_parameters_copy(bsfc->par_in, fmt_ctx->streams[video_stream_idx]->codecpar);
        ck(av_bsf_init(bsfc));
    }

    try {
        std::vector<DecodedFrame> decodedFrames;
        int64_t current_pts = 0;
        std::vector<std::tuple<CUdeviceptr, int64_t>> frameData;

        // Frame reading loop
        while (av_read_frame(fmt_ctx, pkt) >= 0) {
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

            // Process video packet (bitstream filtering for H.264/H.265)
            if (codec_type == AV_CODEC_ID_H264 || codec_type == AV_CODEC_ID_HEVC) {
                ck(av_bsf_send_packet(bsfc, pkt));
                ck(av_bsf_receive_packet(bsfc, pktFiltered));
                frameData = decoder->VideoDecode(pktFiltered->data, pktFiltered->size, CUVID_PKT_ENDOFPICTURE);
            }
            else {
                frameData = decoder->VideoDecode(pkt->data, pkt->size, CUVID_PKT_ENDOFPICTURE);
            }

            // Convert decoded data to frame structure
            std::transform(frameData.begin(),
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
                                   {height, width, 1},                             // Shape
                                   {width, 1, 1},                                  // Strides
                                   "|u1",                                          // Data type
                                   reinterpret_cast<size_t>(decoder->GetStream()), // Stream ID
                                   data_ptr,                                       // Data pointer
                                   false                                           // Read-only flag
                               });
                               // UV component view (assumes contiguous memory)
                               frame.views.push_back(CAIMemoryView{{height / 2, width / 2, 2}, // Shape
                                                                   {width / 2 * 2, 2, 1},      // Strides
                                                                   "|u1",                      // Data type
                                                                   reinterpret_cast<size_t>(decoder->GetStream()),
                                                                   data_ptr + width * height, // UV offset
                                                                   false});

                               // Load DLPack data (original implementation preserved)
                               std::vector<size_t> dl_shape{static_cast<size_t>(height * 1.5), width};
                               std::vector<size_t> dl_stride{width, 1};
                               frame.extBuf->LoadDLPack(dl_shape,
                                                        dl_stride,
                                                        "|u1",
                                                        gpuId,
                                                        reinterpret_cast<size_t>(decoder->GetStream()),
                                                        data_ptr,
                                                        false);
                               return frame;
                           });
        }

        // Cleanup resources
        avformat_close_input(&fmt_ctx);
        if (bsfc) {
            av_bsf_free(&bsfc);
        }

        // Validate decoding results
        if (decodedFrames.empty()) {
            throw std::runtime_error("No frames decoded");
        }
        return decodedFrames[0];
    }
    catch (...) {
        // Cleanup on exception
        avformat_close_input(&fmt_ctx);
        if (bsfc) {
            av_bsf_free(&bsfc);
        }
        throw; // Preserve original exception
    }

    return resultFrame; // Fallback return (should not be reached in practice)
}
