#include "catch2/catch_all.hpp"
#include "video_decoder.hpp"

#include <cstddef>
#include <filesystem>
#include <sstream>

namespace fs = std::filesystem;

class VideoFixture {
public:
    fs::path video_path;
    const size_t width = 1280;
    const size_t height = 720;
    const size_t duration = 1;
    const std::string codec = "libx265";

    VideoFixture() {
        video_path = fs::temp_directory_path() / "test_video.mp4";

        if (system("ffmpeg -version") != 0) {
            SKIP("FFmpeg not found in system PATH");
        }

        std::ostringstream commandFormatter;
        commandFormatter << "ffmpeg -y -f lavfi -i mandelbrot=size=" << width << "x" << height << ":rate=30 "
                         << "-t " << duration << " -c:v " << codec << " -pix_fmt yuv420p -r 30 -g 16 -bf 0 -f mp4 "
                         << video_path.string();

        auto ret = system(commandFormatter.str().c_str());
        if (ret != 0 || !fs::exists(video_path)) {
            FAIL("Failed to generate test video");
        }
    }

    ~VideoFixture() {
        if (fs::exists(video_path)) {
            try {
                fs::remove(video_path);
            }
            catch (...) {
            }
        }
    }

    VideoFixture(const VideoFixture&) = delete;
    VideoFixture& operator=(const VideoFixture&) = delete;
    VideoFixture(VideoFixture&&) = delete;
    VideoFixture& operator=(VideoFixture&&) = delete;
};

TEST_CASE_METHOD(VideoFixture, "VideoDecoder.decode", "[VideoDecoder]") {
    SECTION("Verify video file existence") {
        REQUIRE(fs::file_size(video_path) > 1024);
    }

    SECTION("Decode video") {
        VideoDecoder(0, "h265").decode(video_path, 0);
    }
}
