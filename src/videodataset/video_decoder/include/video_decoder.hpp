#pragma once
#include "cuda_context.hpp"
#include <string>
#include "ffmpeg_utils.hpp"
#include <memory>
#include "decoder_core.hpp"

// Structure representing a decoded video frame

// Video decoder class with CUDA acceleration
class VideoDecoder {
private:
    CudaContext cuda_ctx;  // CUDA context for GPU operations
    // Add new member variables
    AVBSFContext* bsf_ctx_ = nullptr; // Bitstream filter context
    AVPacket* pkt_ = nullptr; // Packet pointer
    std::string codec_type;
    AVCodecID codec_id_;
    AVFormatContext* fmt_ctx_;
    DecoderCore* decoder_core_;
    bool check_frames(const std::vector<DecodedFrame>& frames, int64_t target_pts, DecodedFrame& result);
    AVPacket* apply_bitstream_filter(AVPacket* pkt);
public:
    // Constructor: creates a video decoder instance
    // @param gpuid: GPU device ID to use for decoding
    // @param codec: Name of the video codec (e.g., "h264", "hevc")
    VideoDecoder(int gpuid, std::string codec);
    ~VideoDecoder();
    DecodedFrame decode(const std::string &videoPath, const int targetFrame);
    AVFormatContext* open(const std::string &videoPath);

    int gpuId;         // ID of the GPU being used for decoding
    std::string codec;  // Video codec format being decoded
};
