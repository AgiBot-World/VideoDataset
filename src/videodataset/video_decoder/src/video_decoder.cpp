#include "video_decoder.hpp"
#include "cuda_context.hpp"

VideoDecoder::VideoDecoder(int gpuid, std::string codec)
    : cuda_ctx(gpuid), // Initialized cuda context
    gpuId(gpuid),
    codec(codec) {}
