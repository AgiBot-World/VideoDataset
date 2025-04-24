#pragma once
extern "C" {
#include <libavformat/avformat.h>
}
#include <libavcodec/avcodec.h>

/**
 * @class ScopedAVPacket
 * @brief A wrapper class for AVPacket that ensures proper resource management.
 */
class ScopedAVPacket {
public:
    /**
     * @brief Constructor for ScopedAVPacket.
     */
    ScopedAVPacket();

    /**
     * @brief Destructor for ScopedAVPacket.
     */
    ~ScopedAVPacket();

    /**
     * @brief Overloaded arrow operator to access the underlying AVPacket.
     * @return A pointer to the AVPacket.
     */
    AVPacket* operator->() noexcept;

private:
    // Pointer to the AVPacket
    AVPacket* pkt;
};

namespace FFmpegUtils {
    /**
     * @brief Performs a safe seek operation to a specific frame in a media stream.
     *
     * This function attempts to seek to the specified target PTS (Presentation Time Stamp)
     * in the given video stream. If the seek operation fails, it closes the input format context
     * and throws a runtime error.
     *
     * @param fmt_ctx Pointer to the AVFormatContext representing the media file.
     * @param video_stream_idx Index of the video stream to seek in.
     * @param target_pts The target PTS to seek to.
     * @throws std::runtime_error If the frame seek operation fails.
     */
    inline void seek_to_frame(AVFormatContext* fmt_ctx, int video_stream_idx, int64_t target_pts) {
        if (av_seek_frame(fmt_ctx, video_stream_idx, target_pts, AVSEEK_FLAG_BACKWARD) < 0) {
            avformat_close_input(&fmt_ctx);
            throw std::runtime_error("Frame seek operation failed");
        }
    }

    /**
     * @brief Opens a media file and initializes its format context.
     *
     * This function initializes FFmpeg network protocols if necessary, then attempts to open
     * the specified media file and find its stream information. If either step fails, it returns
     * nullptr.
     *
     * @param path Path to the media file.
     * @return Pointer to the initialized AVFormatContext, or nullptr on failure.
     */
    inline AVFormatContext* open_file(const char* path) {
        avformat_network_init();
        AVFormatContext* fmt_ctx = nullptr;
        if (avformat_open_input(&fmt_ctx, path, nullptr, nullptr) < 0)
            return nullptr;

        if (avformat_find_stream_info(fmt_ctx, nullptr) < 0) {
            avformat_close_input(&fmt_ctx);
            return nullptr;
        }

        return fmt_ctx;
    }

    /**
     * @brief Finds the best video stream in a given format context.
     *
     * This function uses FFmpeg's default stream selection criteria to find the best video stream
     * in the provided AVFormatContext.
     *
     * @param fmt_ctx Pointer to the AVFormatContext containing streams.
     * @return Index of the best video stream, or -1 if no video stream is found.
     */
    inline int find_video_stream(AVFormatContext* fmt_ctx) {
        return av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);
    }

    /**
     * @brief Calculates the target PTS (Presentation Time Stamp) for a given frame.
     *
     * This function calculates the target PTS based on the frame rate of the stream and the target frame number.
     *
     * @param stream Pointer to the AVStream for which to calculate the target PTS.
     * @param target_frame The target frame number.
     * @return The calculated target PTS.
     */
    inline int64_t calculate_target_pts(AVStream* stream, int target_frame) {
        const double fps = av_q2d(stream->avg_frame_rate);
        const double target_time = target_frame / fps;
        return av_rescale_q(
            static_cast<int64_t>(target_time * AV_TIME_BASE),
            AV_TIME_BASE_Q,
            stream->time_base
        );
    }

    /**
     * @brief Creates a bitstream filter for H.264 or H.265 streams.
     *
     * This function creates a bitstream filter for H.264 or H.265 streams based on the codec ID.
     * If the codec ID is neither H.264 nor H.265, it returns nullptr.
     *
     * @param codec_id The codec ID of the stream.
     * @param codecpar Pointer to the AVCodecParameters of the stream.
     * @return Pointer to the initialized AVBSFContext, or nullptr on failure.
     */
    inline AVBSFContext* create_bitstream_filter(AVCodecID codec_id, AVCodecParameters* codecpar) {
        const char* filter_name = nullptr;
        if (codec_id == AV_CODEC_ID_H264) filter_name = "h264_mp4toannexb";
        else if (codec_id == AV_CODEC_ID_HEVC) filter_name = "hevc_mp4toannexb";
        if (!filter_name) return nullptr;

        const AVBitStreamFilter* bsf = av_bsf_get_by_name(filter_name);
        AVBSFContext* bsfc = nullptr;
        av_bsf_alloc(bsf, &bsfc);
        avcodec_parameters_copy(bsfc->par_in, codecpar);
        av_bsf_init(bsfc);
        return bsfc;
    }
}
