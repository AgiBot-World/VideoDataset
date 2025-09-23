#pragma once

#include <memory>
#include <string>

#include "core/PyCAIMemoryView.hpp"
#include "core/nvcuvid.h"

class NvDecoder;

class VideoDecoder {
public:
    VideoDecoder(int gpuId, const std::string& codec);

    ~VideoDecoder();

    int gpuId() const noexcept { return gpuId_; }

    std::string codec() const noexcept { return codec_; }

    DecodedFrame decode(const std::string& videoPath, int frameIndex);

private:
    void checkDecodeFormat() const;

    std::unique_ptr<NvDecoder> nvDecoder_{nullptr};
    CUcontext cuCtx_{nullptr}; // CUDA context for GPU operations
    CUdevice gpuId_{0};
    std::string codec_; // Video codec format being decoded
};
