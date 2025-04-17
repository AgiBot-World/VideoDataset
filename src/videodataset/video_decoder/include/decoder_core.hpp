#pragma once
#include "NvDecoder.h"
#include "FFmpegDemuxer.h"
#include "cuda_context.hpp"
#include <stdexcept>

class DecoderCore {
public:
    // Constructor: Initializes the decoder with CUDA context and codec type
    DecoderCore(CUcontext ctx, AVCodecID codec_id) {
        // Convert FFmpeg codec ID to NVIDIA codec type
        cudaVideoCodec nvCodec = FFmpeg2NvCodecId(codec_id);
        // Create NVIDIA decoder instance
        decoder_ = new NvDecoder(ctx, true, nvCodec, true);
    }

    // Destructor: Cleans up decoder resources
    ~DecoderCore() {
        if (decoder_) {
            delete decoder_;
        }
    }

    // Decodes video data packet
    // Parameters:
    //   data: Pointer to compressed video data
    //   size: Size of the data buffer
    //   flags: Decoding flags/options
    // Returns: Decoding result (type depends on NvDecoder implementation)
    auto decode(const uint8_t* data, int size, int flags) {
        // Forward the decode operation to the NVIDIA decoder
        return decoder_->Decode(data, size, flags);
    }

    // Add other required interface methods here...

private:
    // Pointer to NVIDIA decoder instance
    NvDecoder* decoder_ = nullptr;
};
