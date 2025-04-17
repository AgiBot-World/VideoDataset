#include "video_decoder.hpp"
#include "cuda_context.hpp"
#include "Logger.h"

// Global logger instance initialization
simplelogger::Logger *logger = simplelogger::LoggerFactory::CreateConsoleLogger();

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

    // Initialize decoder core
    decoder_core_ = new DecoderCore(cuda_ctx, codec_id_);
}

VideoDecoder::~VideoDecoder() {
    if (decoder_core_) delete decoder_core_;
    if (fmt_ctx_) avformat_close_input(&fmt_ctx_);
}

DecodedFrame VideoDecoder::decode(const std::string& path, int target_frame) {
    // Open media file
    if (!(fmt_ctx_ = FFmpegUtils::open_file(path.c_str())))
        throw std::runtime_error("Could not open file: " + path);

    // Find video stream
    int video_stream = FFmpegUtils::find_video_stream(fmt_ctx_);
    if (video_stream < 0)
        throw std::runtime_error("No video stream found");

    // TODO: Add timestamp calculation and decoding loop logic here
    return DecodedFrame{};
}
