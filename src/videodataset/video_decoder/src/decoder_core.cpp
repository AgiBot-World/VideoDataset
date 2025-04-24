#include "decoder_core.hpp"

/**
 * @brief Constructor for DecoderCore.
 *
 * Initializes the decoder core with the given CUDA context and codec ID.
 * It creates a CustomDecoder object and throws an exception if the creation fails.
 *
 * @param ctx The CUDA context to use for decoding.
 * @param codec_id The AVCodecID representing the video codec.
 * @throws DecoderCore::DecoderException if the NvDecoder creation fails.
 */
DecoderCore::DecoderCore(CUcontext ctx, AVCodecID codec_id) {
    cudaVideoCodec nvCodec = FFmpeg2NvCodecId(codec_id);
    decoder_ = new CustomDecoder(ctx, true, FFmpeg2NvCodecId(codec_id), true);
    if (!decoder_) throw DecoderException("Failed to create NvDecoder");
}

/**
 * @brief Destructor for DecoderCore.
 *
 * Deletes the CustomDecoder object created during construction.
 */
DecoderCore::~DecoderCore() {
    delete decoder_;
}

/**
 * @brief Decodes a packet of video data.
 *
 * Decodes the given packet of video data using the CustomDecoder.
 * It then converts the raw decoded frames into a vector of DecodedFrame objects.
 *
 * @param data Pointer to the encoded video data.
 * @param size Size of the encoded video data.
 * @return A vector of DecodedFrame objects representing the decoded frames.
 */
std::vector<DecodedFrame> DecoderCore::decode_packet(const uint8_t* data, int size) {
    auto raw_frames = decoder_->VideoDecode(data, size, CUVID_PKT_ENDOFPICTURE);

    std::vector<DecodedFrame> frames;
    for (auto& frame : raw_frames) {
        CUdeviceptr ptr = std::get<0>(frame);
        int64_t timestamp = std::get<1>(frame);
        frames.push_back(create_frame(ptr, timestamp));
    }
    return frames;
}

/**
 * @brief Gets the width of the decoded video frames.
 *
 * @return The width of the decoded video frames.
 */
int DecoderCore::width() const { return decoder_->GetWidth(); }

/**
 * @brief Gets the height of the decoded video frames.
 *
 * @return The height of the decoded video frames.
 */
int DecoderCore::height() const { return decoder_->GetHeight(); }

/**
 * @brief Gets the CUDA video surface format of the decoded video frames.
 *
 * @return The CUDA video surface format of the decoded video frames.
 */
cudaVideoSurfaceFormat DecoderCore::format() const { return decoder_->GetOutputFormat(); }

/**
 * @brief Creates a DecodedFrame object from the given data pointer and timestamp.
 *
 * @param data_ptr CUdeviceptr to the video frame data.
 * @param timestamp Timestamp of the video frame.
 * @return A DecodedFrame object.
 */
DecodedFrame DecoderCore::create_frame(CUdeviceptr data_ptr, int64_t timestamp) {
    DecodedFrame frame;
    frame.timestamp = timestamp;
    return frame;
}

/**
 * @brief Decodes the given encoded video data.
 *
 * Decodes the provided encoded video data and returns a vector of tuples
 * containing the CUdeviceptr to the decoded frame data and its timestamp.
 * It also validates the output format of the decoded frames.
 *
 * @param encodedData Pointer to the encoded video data.
 * @param dataSize Size of the encoded video data.
 * @param decodeFlags Decoding flags.
 * @return A vector of tuples containing CUdeviceptr and timestamp of the decoded frames.
 * @throws std::runtime_error if an unsupported video format is encountered.
 */
std::vector<std::tuple<CUdeviceptr, int64_t>> CustomDecoder::VideoDecode(
    const uint8_t* encodedData,
    int dataSize,
    int decodeFlags)
{
    const int numFrames = this->Decode(encodedData, dataSize, decodeFlags);
    std::vector<std::tuple<CUdeviceptr, int64_t>> decodedFrames;
    decodedFrames.reserve(numFrames);  // Pre - allocate memory for performance optimization

    for (int frameIndex = 0; frameIndex < numFrames; ++frameIndex) {
        // Retrieve frame data and timestamp
        int64_t timestamp = 0;
        CUdeviceptr frameData = reinterpret_cast<CUdeviceptr>(this->GetFrame(&timestamp));

        // Validate output format compatibility
        const auto outputFormat = this->GetOutputFormat();
        switch (outputFormat) {
            case cudaVideoSurfaceFormat_NV12:
            case cudaVideoSurfaceFormat_P016:
            case cudaVideoSurfaceFormat_YUV444:
            case cudaVideoSurfaceFormat_YUV444_16Bit:
                // Supported base formats, no special handling needed
                break;

            default:
                throw std::runtime_error("Unsupported video format: "
                    + std::to_string(static_cast<int>(outputFormat)));
        }

        decodedFrames.emplace_back(frameData, timestamp);
    }

    return decodedFrames;
}
