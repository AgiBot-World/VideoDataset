#pragma once
extern "C" {
#include <libavformat/avformat.h>
}

namespace FFmpegUtils {
    /**
     * Opens a media file and initializes its format context.
     *
     * @param path Path to the media file.
     * @return Pointer to the initialized AVFormatContext, or nullptr on failure.
     * @note Automatically initializes FFmpeg network protocols if needed.
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
     * Finds the best video stream in a given format context.
     *
     * @param fmt_ctx Pointer to the AVFormatContext containing streams.
     * @return Index of the best video stream, or -1 if no video stream is found.
     * @note Uses FFmpeg's default stream selection criteria.
     */
    inline int find_video_stream(AVFormatContext* fmt_ctx) {
        return av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);
    }
}
