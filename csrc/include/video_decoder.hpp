#pragma once

#include <memory>
#include <string>

#include <torch/torch.h>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include "core/nvcuvid.h"

class NvDecoder;

class VideoDecoder {
public:
    VideoDecoder(int gpuId, const std::string& codec);

    ~VideoDecoder();

    int gpuId() const noexcept { return gpuId_; }

    std::string codec() const noexcept { return codec_; }

    std::vector<pybind11::array_t<uint8_t>> decodeToNps(const std::string& videoPath, const std::vector<int>& frameIndices);

    pybind11::array_t<uint8_t> decodeToNp(const std::string& videoPath, int frameIndex);

    torch::Tensor decodeToTensor(const std::string& videoPath, int frameIndex);

private:
    void checkDecodeFormat() const;

    std::unique_ptr<NvDecoder> nvDecoder_{nullptr};
    CUcontext cuCtx_{nullptr}; // CUDA context for GPU operations
    CUdevice gpuId_{0};
    std::string codec_; // Video codec format being decoded
};
