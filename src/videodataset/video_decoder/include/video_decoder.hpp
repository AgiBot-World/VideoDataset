#include "cuda_context.hpp"
#include <string>

// Structure representing a decoded video frame
struct DecodedFrame {
    int64_t timestamp;  // Presentation timestamp (PTS) of the frame (to be extended later)
};

// Video decoder class with CUDA acceleration
class VideoDecoder {
private:
    CudaContext cuda_ctx;  // CUDA context for GPU operations
public:
    // Constructor: creates a video decoder instance
    // @param gpuid: GPU device ID to use for decoding
    // @param codec: Name of the video codec (e.g., "h264", "hevc")
    VideoDecoder(int gpuid, std::string codec);

    int gpuId;         // ID of the GPU being used for decoding
    std::string codec;  // Video codec format being decoded
    std::string hello_cuda();
};
