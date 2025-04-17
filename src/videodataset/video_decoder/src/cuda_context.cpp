#include "cuda_context.hpp"
#include <stdexcept>

CudaContext::CudaContext(int gpuid) : ctx(nullptr), own_ctx(false) {
    // Initialize CUDA driver API
    cuInit(0);

    // Get number of available CUDA devices
    int count = 0;
    cuDeviceGetCount(&count);

    // Validate GPU ID
    if (gpuid < 0 || gpuid >= count)
        throw std::invalid_argument("Invalid GPU ID");

    // Check if there's existing CUDA context
    cuCtxGetCurrent(&ctx);

    // Create new context if none exists
    if (!ctx) {
        cuCtxCreate(&ctx, 0, gpuid);
        own_ctx = true;  // Flag that we own this context
    }
}

CudaContext::~CudaContext() {
    // Destroy context only if we own it
    if (own_ctx && ctx) cuCtxDestroy(ctx);
}
