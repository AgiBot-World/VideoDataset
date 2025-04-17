#pragma once
#include <cuda.h>

// Manages a CUDA context for GPU operations
// Handles context creation and destruction with proper ownership tracking
class CudaContext {
    public:
        CUcontext ctx;      // CUDA context handle
        bool own_ctx;       // Ownership flag (true if this class created the context)

        // Creates a CUDA context for the specified GPU device
        // @param gpuid: The GPU device ID to create context for
        CudaContext(int gpuid);

        // Destructor - automatically cleans up the CUDA context if owned
        ~CudaContext();
    };
