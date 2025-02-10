#include "catch2/catch_all.hpp"
#include "video_decoder.hpp"

#include <pybind11/embed.h>
#include <catch2/catch_test_macros.hpp>
#include <chrono>
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
        const auto timestamp =
            std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch())
                .count();
        video_path = fs::temp_directory_path() / std::to_string(timestamp) / "test_video.mp4";

        if (!fs::exists(video_path.parent_path())) {
            fs::create_directories(video_path.parent_path());
        }

        if (system("ffmpeg -version") != 0) {
            SKIP("FFmpeg not found in system PATH");
        }

        std::ostringstream commandFormatter;
        commandFormatter << "ffmpeg -y -f lavfi -i mandelbrot=size=" << width << "x" << height << ":rate=30 " << "-t "
                         << duration << " -c:v " << codec << " -pix_fmt yuv420p -g 16 -bf 0 -f mp4 "
                         << video_path.string();

        auto ret = system(commandFormatter.str().c_str());
        if (ret != 0 || !fs::exists(video_path)) {
            FAIL("Failed to generate test video");
        }
    }

    ~VideoFixture() {
        if (fs::exists(video_path.parent_path())) {
            try {
                fs::remove(video_path.parent_path());
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
    pybind11::scoped_interpreter guard{};
    auto frames = VideoDecoder(0, "h265").decodeToNps(video_path, {0, 3, 6, 9});
    REQUIRE(frames.size() == 4);
    auto np_frame = VideoDecoder(0, "h265").decodeToNp(video_path, 9);
    REQUIRE(np_frame.ndim() == 3);
    auto tensor_frame = VideoDecoder(0, "h265").decodeToTensor(video_path, 9);
    REQUIRE(tensor_frame.dim() == 3);
}
