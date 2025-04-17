/**
 * @class CudaContext
 * @brief RAII wrapper for CUDA context management.
 *
 * Automatically initializes and manages the lifecycle of a CUDA context.
 * If the context is created by this object, it will be destroyed upon object destruction.
 */
 #pragma once
 #include <cuda.h>  // 添加 CUDA 驱动 API 头文件
 #include <stdexcept>

 class CudaContext {
 public:
     /**
      * @brief Constructor - Initializes CUDA and creates/attaches to a context.
      * @param gpuid The GPU device ID to use (must be valid).
      * @throws std::runtime_error if CUDA initialization fails.
      * @throws std::invalid_argument if GPU ID is invalid.
      */
     CudaContext(int gpuid) : ctx_(nullptr), owns_ctx_(false) {
         CUresult err = CUDA_SUCCESS;

         // Initialize CUDA driver API
         if ((err = cuInit(0)) != CUDA_SUCCESS)
             throw std::runtime_error("CUDA init failed");

         // Get number of available CUDA devices
         int devCount = 0;
         if ((err = cuDeviceGetCount(&devCount)) != CUDA_SUCCESS)
             throw std::runtime_error("Get device count failed");

         // Validate GPU ID
         if (gpuid < 0 || gpuid >= devCount)
             throw std::invalid_argument("Invalid GPU ID");

         // Get CUDA device handle
         CUdevice device;
         if ((err = cuDeviceGet(&device, gpuid)) != CUDA_SUCCESS)
             throw std::runtime_error("Get device failed");

         // Check if a context already exists; if not, create a new one
         if (cuCtxGetCurrent(&ctx_) != CUDA_SUCCESS || !ctx_) {
             if ((err = cuCtxCreate(&ctx_, CU_CTX_SCHED_AUTO, device)) != CUDA_SUCCESS)
                 throw std::runtime_error("Context creation failed");
             owns_ctx_ = true;  // Mark ownership if we created the context
         }
     }

     /**
      * @brief Destructor - Destroys the context if this object owns it.
      */
     ~CudaContext() {
         if (owns_ctx_ && ctx_) {
             cuCtxDestroy(ctx_);
         }
     }

     /**
      * @brief Implicit conversion to CUcontext.
      * @return The underlying CUDA context handle.
      */
     operator CUcontext() const { return ctx_; }

 private:
     CUcontext ctx_;    // CUDA context handle
     bool owns_ctx_;    // Flag indicating ownership (needs cleanup)
 };
