#pragma once
#include "NvDecoder.h"
#include "FFmpegDemuxer.h"
#include "cuda_context.hpp"
#include <stdexcept>
#include <vector>
#include <cuda.h>

/**
 * @struct DecodedFrame
 * @brief Represents a decoded video frame with its timestamp and data views.
 */
struct DecodedFrame {
    // Timestamp of the decoded frame
    int64_t timestamp;
    // Data views (YUV components) of the decoded video frame
    std::vector<CUdeviceptr> views;
};

/**
 * @class CustomDecoder
 * @brief A custom decoder class that inherits from NvDecoder.
 */
class CustomDecoder : public NvDecoder {
public:
    /**
     * @brief Inherits the constructors from NvDecoder.
     */
    using NvDecoder::NvDecoder;

    /**
     * @brief Decodes the given encoded video data.
     *
     * @param encodedData Pointer to the encoded video data.
     * @param dataSize Size of the encoded video data.
     * @param decodeFlags Decoding flags (default is 0).
     * @return A vector of tuples containing CUdeviceptr and timestamp of the decoded frames.
     */
    std::vector<std::tuple<CUdeviceptr, int64_t>>
    VideoDecode(const uint8_t* encodedData, int dataSize, int decodeFlags = 0);
};

/**
 * @class DecoderCore
 * @brief Core class for video decoding operations.
 */
class DecoderCore {
public:
    /**
     * @class DecoderException
     * @brief Custom exception class for decoder errors.
     */
    class DecoderException : public std::runtime_error {
    public:
        /**
         * @brief Constructor for DecoderException.
         *
         * @param msg Error message.
         */
        DecoderException(const std::string& msg)
            : std::runtime_error("Decoder Error: " + msg) {}
    };

    /**
     * @brief Constructor for DecoderCore.
     *
     * @param ctx CUDA context.
     * @param codec_id AVCodecID of the video codec.
     */
    DecoderCore(CUcontext ctx, AVCodecID codec_id);

    /**
     * @brief Destructor for DecoderCore.
     */
    ~DecoderCore();

    /**
     * @brief Decodes a packet of video data.
     *
     * @param data Pointer to the video data packet.
     * @param size Size of the video data packet.
     * @return A vector of decoded frames.
     */
    std::vector<DecodedFrame> decode_packet(const uint8_t* data, int size);

    /**
     * @brief Gets the width of the decoded video frames.
     *
     * @return Width of the decoded video frames.
     */
    int width() const;

    /**
     * @brief Gets the height of the decoded video frames.
     *
     * @return Height of the decoded video frames.
     */
    int height() const;

    /**
     * @brief Gets the CUDA video surface format of the decoded video frames.
     *
     * @return CUDA video surface format.
     */
    cudaVideoSurfaceFormat format() const;

private:
    /**
     * @brief Creates a DecodedFrame object from the given data pointer and timestamp.
     *
     * @param data_ptr CUdeviceptr to the video frame data.
     * @param timestamp Timestamp of the video frame.
     * @return A DecodedFrame object.
     */
    DecodedFrame create_frame(CUdeviceptr data_ptr, int64_t timestamp);

    // Pointer to the NvDecoder object
    NvDecoder* decoder_ = nullptr;
};
