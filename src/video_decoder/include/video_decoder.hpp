#pragma once

#include "core/FFmpegDemuxer.h"
#include "core/NvDecoder.h"
#include "core/PyCAIMemoryView.hpp"

class VideoDecoder {
private:
    CUcontext cu_ctx = nullptr; // CUDA context for GPU operations
    CUdevice dev = 0;
    AVBSFContext* bsf_ctx_ = nullptr; // Bitstream filter context
    AVPacket* pkt = nullptr;          // Packet pointer
    AVPacket* pktFiltered = nullptr;
    AVCodecID codec_type;
    AVCodecID codec_id_;
    AVFormatContext* fmt_ctx_;
    NvDecoder* decoder = nullptr;

public:
    // Constructor: creates a video decoder instance
    // @param gpuId: GPU device ID to use for decoding
    // @param codec: Name of the video codec (e.g., "h264", "hevc")
    VideoDecoder(int gpuId, const std::string& codec);
    ~VideoDecoder();
    DecodedFrame decode(const std::string& videoPath, const int targetFrame);
    AVFormatContext* open(const std::string& videoPath);
    int gpuId;         // ID of the GPU being used for decoding
    std::string codec; // Video codec format being decoded
};
