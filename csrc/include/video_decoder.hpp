#pragma once

#include <memory>
#include <string>

#include <torch/torch.h>

#include "core/PyCAIMemoryView.hpp"

class NvDecoder;

class VideoDecoder {
public:
    VideoDecoder(int gpuId, const std::string& codec);

    ~VideoDecoder();

    int gpuId() const noexcept { return gpuId_; }

    std::string codec() const noexcept { return codec_; }

    std::vector<py::array_t<uint8_t>> decodeToNps(const std::string& videoPath, const std::vector<int>& frameIndices);

    py::array_t<uint8_t> decodeToNp(const std::string& videoPath, int frameIndex);

    torch::Tensor decodeToTensor(const std::string& videoPath, int frameIndex);

    DecodedFrame decode(const std::string& videoPath, int frameIndex);

private:
    void checkDecodeFormat() const;

    std::unique_ptr<NvDecoder> nvDecoder_{nullptr};
    CUcontext cuCtx_{nullptr}; // CUDA context for GPU operations
    CUdevice gpuId_{0};
    std::string codec_; // Video codec format being decoded
};
