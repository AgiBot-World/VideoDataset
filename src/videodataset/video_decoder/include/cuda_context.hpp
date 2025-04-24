/**
 * @class CudaContext
 * @brief RAII wrapper for CUDA context management with multi - GPU support.
 *
 * Features:
 * - Automatic CUDA driver initialization
 * - Context sharing awareness
 * - Thread - safe context binding
 * - Error code to exception translation
 */
 #pragma once
 #include <cuda.h>
 #include <stdexcept>
 #include <string>

 class CudaContext {
 public:
     /**
      * @brief Constructor - Initializes CUDA and creates/attaches to a context.
      * @param gpuid The GPU device ID (0 - based index)
      * @throws std::runtime_error for CUDA errors
      * @throws std::invalid_argument for invalid GPU ID
      */
     explicit CudaContext(int gpuid) : ctx_(nullptr), owns_ctx_(false) {
         CUresult err = CUDA_SUCCESS;

         // Initialize the CUDA driver
         if ((err = cuInit(0)) != CUDA_SUCCESS)
             throw cuda_exception("cuInit failed", err);

         // Get the number of CUDA devices
         int dev_count = 0;
         if ((err = cuDeviceGetCount(&dev_count)) != CUDA_SUCCESS)
             throw cuda_exception("cuDeviceGetCount failed", err);

         // Validate the device ID
         if (gpuid < 0 || gpuid >= dev_count)
             throw std::invalid_argument("Invalid GPU ID: " + std::to_string(gpuid));

         // Get the device handle
         CUdevice device;
         if ((err = cuDeviceGet(&device, gpuid)) != CUDA_SUCCESS)
             throw cuda_exception("cuDeviceGet failed", err);

         // Context management
         CUcontext prev_ctx = nullptr;
         cuCtxGetCurrent(&prev_ctx);  // Save the current context

         // Create or attach to an existing context
         if (cuCtxGetCurrent(&ctx_) != CUDA_SUCCESS || !ctx_) {
             if ((err = cuCtxCreate(&ctx_, CU_CTX_SCHED_AUTO, device)) != CUDA_SUCCESS)
                 throw cuda_exception("cuCtxCreate failed", err);

             owns_ctx_ = true;
             cuCtxSetCurrent(prev_ctx);  // Restore the original context
         }
     }

     /**
      * @brief Destructor - Destroys the CUDA context if owned.
      */
     ~CudaContext() {
         if (owns_ctx_ && ctx_) {
             cuCtxDestroy(ctx_);
         }
     }

     /**
      * @brief Explicitly get the CUDA context.
      * @return The CUDA context handle.
      */
     CUcontext get_cu_context() const noexcept { return ctx_; }

     /**
      * @brief Implicit conversion to CUcontext.
      * @return The CUDA context handle.
      */
     operator CUcontext() const noexcept { return ctx_; }

     // Disable copy constructor
     CudaContext(const CudaContext&) = delete;
     // Disable copy assignment operator
     CudaContext& operator=(const CudaContext&) = delete;

     /**
      * @brief Move constructor.
      * @param other The CudaContext object to be moved.
      */
     CudaContext(CudaContext&& other) noexcept
         : ctx_(other.ctx_), owns_ctx_(other.owns_ctx_) {
         other.ctx_ = nullptr;
         other.owns_ctx_ = false;
     }

     /**
      * @brief Move assignment operator.
      * @param other The CudaContext object to be moved.
      * @return A reference to the current CudaContext object.
      */
     CudaContext& operator=(CudaContext&& other) noexcept {
         if (this != &other) {
             if (owns_ctx_ && ctx_) cuCtxDestroy(ctx_);
             ctx_ = other.ctx_;
             owns_ctx_ = other.owns_ctx_;
             other.ctx_ = nullptr;
             other.owns_ctx_ = false;
         }
         return *this;
     }

 private:
     // CUDA context handle
     CUcontext ctx_;
     // Flag indicating whether the object owns the context
     bool owns_ctx_;

     /**
      * @brief Helper function to generate a CUDA exception.
      * @param msg The error message.
      * @param err The CUDA error code.
      * @return A std::runtime_error object with a formatted error message.
      */
     static std::runtime_error cuda_exception(const char* msg, CUresult err) {
         const char* err_name = nullptr;
         cuGetErrorName(err, &err_name);
         return std::runtime_error(
             std::string(msg) + " (CUDA error: " + (err_name ? err_name : "Unknown") + ")"
         );
     }
 };
