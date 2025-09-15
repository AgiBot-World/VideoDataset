#include "video_decoder.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <queue>
#include <sstream>
#include <unordered_map>

#include <cuda.h>
#include <cuda_runtime_api.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavformat/avio.h>
/* Explicitly include bsf.h when building against FFmpeg 4.3 (libavcodec 58.45.100) or later for backward compatibility
 */
#if LIBAVCODEC_VERSION_INT >= 3824484
#include <libavcodec/bsf.h>
#endif

// #define __STDC_CONSTANT_MACROS
#include <libavcodec/codec_id.h>
}

#include "core/NvDecoder.h"

cudaVideoCodec avCodec2NvCodec(AVCodecID id) {
    switch (id) {
        case AV_CODEC_ID_MPEG1VIDEO:
            return cudaVideoCodec_MPEG1;
        case AV_CODEC_ID_MPEG2VIDEO:
            return cudaVideoCodec_MPEG2;
        case AV_CODEC_ID_MPEG4:
            return cudaVideoCodec_MPEG4;
        case AV_CODEC_ID_WMV3:
        case AV_CODEC_ID_VC1:
            return cudaVideoCodec_VC1;
        case AV_CODEC_ID_H264:
            return cudaVideoCodec_H264;
        case AV_CODEC_ID_HEVC:
            return cudaVideoCodec_HEVC;
        case AV_CODEC_ID_VP8:
            return cudaVideoCodec_VP8;
        case AV_CODEC_ID_VP9:
            return cudaVideoCodec_VP9;
        case AV_CODEC_ID_MJPEG:
            return cudaVideoCodec_JPEG;
        case AV_CODEC_ID_AV1:
            return cudaVideoCodec_AV1;
        default:
            return cudaVideoCodec_NumCodecs;
    }
}

AVCodecID getAVCodeID(const std::string& codec) {
    static const std::unordered_map<std::string, AVCodecID> codecMap = {{"hevc", AV_CODEC_ID_HEVC},
                                                                        {"h265", AV_CODEC_ID_HEVC},
                                                                        {"h264", AV_CODEC_ID_H264},
                                                                        {"av1", AV_CODEC_ID_AV1},
                                                                        {"vp9", AV_CODEC_ID_VP9}};

    auto it = codecMap.find(codec);
    if (it != codecMap.end()) {
        return it->second;
    }
    throw std::runtime_error("Unsupported codec type: " + codec);
}

class Demuxer {
public:
    explicit Demuxer(const std::string& videoPath) {
        this->fmtCtx.reset(createAVFormatContext(videoPath));

        // Retrieve stream information (probes file format)
        if (::avformat_find_stream_info(fmtCtx.get(), nullptr) < 0) {
            throw std::runtime_error("Failed to retrieve stream information");
        }

        // Find best video stream index (auto-selects decoder)
        if ((this->videoStreamIdx = ::av_find_best_stream(fmtCtx.get(),       // Format context
                                                          AVMEDIA_TYPE_VIDEO, // Media type: video
                                                          -1,                 // Auto-select stream index
                                                          -1,                 // No related streams
                                                          nullptr,            // No codec specified
                                                          0                   // Reserved flags
                                                          ))
            < 0) {
            throw std::runtime_error("No video stream found in file");
        }

        this->eVideoCodec = fmtCtx->streams[videoStreamIdx]->codecpar->codec_id;
        this->bMp4H264 = eVideoCodec == AV_CODEC_ID_H264
                         && (!strcmp(fmtCtx->iformat->long_name, "QuickTime / MOV")
                             || !strcmp(fmtCtx->iformat->long_name, "FLV (Flash Video)")
                             || !strcmp(fmtCtx->iformat->long_name, "Matroska / WebM"));
        this->bMp4HEVC = eVideoCodec == AV_CODEC_ID_HEVC
                         && (!strcmp(fmtCtx->iformat->long_name, "QuickTime / MOV")
                             || !strcmp(fmtCtx->iformat->long_name, "FLV (Flash Video)")
                             || !strcmp(fmtCtx->iformat->long_name, "Matroska / WebM"));

        this->initBitstreamFilterContext();
        pkt.reset(av_packet_alloc());
        pktFiltered.reset(av_packet_alloc());
    }

    ~Demuxer() {
        if (!fmtCtx)
            return;
    }

    double getDuration() const { return static_cast<double>(fmtCtx->duration) / AV_TIME_BASE; }

    double getFps() const { return av_q2d(fmtCtx->streams[this->videoStreamIdx]->r_frame_rate); }

    AVCodecID getVideoCodec() const { return eVideoCodec; }

    int64_t seek(size_t frameIndex) {
        // seek to target timestamp from frame number
        AVStream* video_stream = fmtCtx->streams[videoStreamIdx];
        const double frameRate = av_q2d(video_stream->avg_frame_rate);
        const double target_time = static_cast<double>(frameIndex) / frameRate; // Target time (seconds)
        const int64_t targetTimestamp = av_rescale_q(                           // Convert timebase
            static_cast<int64_t>(target_time * AV_TIME_BASE),
            AV_TIME_BASE_Q,
            video_stream->time_base);

        // Seek to target position (backward search mode)
        if (av_seek_frame(fmtCtx.get(), videoStreamIdx, targetTimestamp, AVSEEK_FLAG_BACKWARD) < 0) {
            throw std::runtime_error("Frame seek operation failed");
        }
        return targetTimestamp;
    }

    bool demux(uint8_t** video, int* videoBytes, int64_t& timestamp) {
        if (!fmtCtx) {
            return false;
        }

        *videoBytes = 0;

        if (pkt->data) {
            av_packet_unref(pkt.get());
        }
        int e = 0;

        while ((e = av_read_frame(fmtCtx.get(), pkt.get())) >= 0 && pkt->stream_index != this->videoStreamIdx) {
            av_packet_unref(pkt.get());
        }

        if (e < 0) {
            return false;
        }

        // Process video packet (bitstream filtering for H.264/H.265)
        if (this->bMp4H264 || this->bMp4HEVC) {
            if (pktFiltered->data) {
                av_packet_unref(pktFiltered.get());
            }
            ck(av_bsf_send_packet(this->bsfCtx.get(), pkt.get()));
            ck(av_bsf_receive_packet(this->bsfCtx.get(), pktFiltered.get()));
            *video = pktFiltered->data;
            *videoBytes = pktFiltered->size;
            timestamp = pktFiltered->pts;
        }
        else {
            *video = pkt->data;
            *videoBytes = pkt->size;
            timestamp = pkt->pts;
        }
        return true;
    }

private:
    static AVFormatContext* createAVFormatContext(const std::string& videoPath) {
        avformat_network_init(); // Initialize FFmpeg network protocols (for RTSP/RTMP streams)

        AVFormatContext* fmtCtx = nullptr;
        if (avformat_open_input(&fmtCtx, videoPath.c_str(), nullptr, nullptr) < 0) {
            throw std::runtime_error("Failed to open video file");
        }
        return fmtCtx;
    }

    void initBitstreamFilterContext() {
        // Initialize bitstream filter (H.264/H.265 require annex B format conversion)
        AVBSFContext* bsfc{nullptr};
        if (this->bMp4H264 || this->bMp4HEVC) {
            const AVBitStreamFilter* bsf = av_bsf_get_by_name(this->bMp4H264 ? "h264_mp4toannexb" : "hevc_mp4toannexb");
            if (!bsf) {
                throw std::runtime_error("Bitstream filter not available");
            }
            ck(av_bsf_alloc(bsf, &bsfc));
            avcodec_parameters_copy(bsfc->par_in, fmtCtx->streams[this->videoStreamIdx]->codecpar);
            ck(av_bsf_init(bsfc));
        }

        this->bsfCtx.reset(bsfc);
    }

    std::unique_ptr<AVFormatContext, void (*)(AVFormatContext*)> fmtCtx{nullptr, [](AVFormatContext* p) {
                                                                            if (p) {
                                                                                avformat_close_input(&p);
                                                                            }
                                                                        }};
    std::unique_ptr<AVBSFContext, void (*)(AVBSFContext*)> bsfCtx{nullptr, [](AVBSFContext* p) {
                                                                      if (p) {
                                                                          av_bsf_free(&p);
                                                                      }
                                                                  }};
    std::unique_ptr<AVPacket, void (*)(AVPacket*)> pkt{nullptr, [](AVPacket* p) {
                                                           if (p) {
                                                               av_packet_free(&p);
                                                           }
                                                       }};
    std::unique_ptr<AVPacket, void (*)(AVPacket*)> pktFiltered{nullptr, [](AVPacket* p) {
                                                                   if (p)
                                                                       (av_packet_free(&p));
                                                               }};

    AVCodecID eVideoCodec;
    int videoStreamIdx;
    bool bMp4H264{false};
    bool bMp4HEVC{false};
};

VideoDecoder::VideoDecoder(int gpuId, const std::string& codec) {
    ck(cuInit(0));
    int device_count = 0;
    ck(cuDeviceGetCount(&device_count));
    if (gpuId < 0 || gpuId >= device_count) {
        throw std::invalid_argument("GPU ordinal out of range. Should be within [0, " + std::to_string(device_count - 1)
                                    + "]");
    }

    cuDeviceGet(&gpuId, gpuId);
    ck(cuDevicePrimaryCtxRetain(&cuCtx_, gpuId));
    cuCtxSetCurrent(cuCtx_);

    this->nvDecoder_ = std::make_unique<NvDecoder>(this->cuCtx_, true, avCodec2NvCodec(getAVCodeID(codec)), true);

    this->codec_ = codec;
    this->gpuId_ = gpuId;
}

VideoDecoder::~VideoDecoder() {
    this->nvDecoder_.reset();
    ck(cuDevicePrimaryCtxRelease(gpuId_));
}

DecodedFrame VideoDecoder::decode(const std::string& videoPath, int frameIndex) {
    std::vector<DecodedFrame> decodedFrames;
    decodedFrames.reserve(30);

    try {
        Demuxer demuxer(videoPath);
        auto frameTimestamp = demuxer.seek(static_cast<size_t>(frameIndex));

        std::vector<std::tuple<CUdeviceptr, int64_t>> decodedTuples;
        uint8_t* video = nullptr;
        int64_t timestamp = 0;
        int videoBytes = 0;
        while (demuxer.demux(&video, &videoBytes, timestamp) && timestamp <= frameTimestamp) {
            decodedTuples = this->nvDecoder_->VideoDecode(video, videoBytes, CUVID_PKT_ENDOFPICTURE, timestamp);
        }

        std::transform(decodedTuples.begin(), // Convert decoded data to frame structure
                       decodedTuples.end(),
                       std::back_inserter(decodedFrames),
                       [this](std::tuple<CUdeviceptr, int64_t> tup) {
                           DecodedFrame frame;
                           // Get decoder parameters
                           const size_t width = static_cast<size_t>(this->nvDecoder_->GetWidth());
                           const size_t height = static_cast<size_t>(this->nvDecoder_->GetHeight());
                           const CUdeviceptr data_ptr = std::get<0>(tup);
                           const int64_t pts = std::get<1>(tup);

                           // Build YUV memory view
                           frame.timestamp = pts;
                           // Y component view
                           frame.views.push_back(CAIMemoryView{
                               {height, width, 1},                                      // Shape
                               {width, 1, 1},                                           // Strides
                               "|u1",                                                   // Data type
                               reinterpret_cast<size_t>(this->nvDecoder_->GetStream()), // Stream ID
                               data_ptr,                                                // Data pointer
                               false                                                    // Read-only flag
                           });
                           // UV component view (assumes contiguous memory)
                           frame.views.push_back(CAIMemoryView{{height / 2, width / 2, 2}, // Shape
                                                               {width / 2 * 2, 2, 1},      // Strides
                                                               "|u1",                      // Data type
                                                               reinterpret_cast<size_t>(this->nvDecoder_->GetStream()),
                                                               data_ptr + width * height, // UV offset
                                                               false});

                           // Load DLPack data (original implementation preserved)
                           std::vector<size_t> dl_shape{static_cast<size_t>(height * 1.5), width};
                           std::vector<size_t> dl_stride{width, 1};
                           frame.extBuf->LoadDLPack(dl_shape,
                                                    dl_stride,
                                                    "|u1",
                                                    this->gpuId_,
                                                    reinterpret_cast<size_t>(this->nvDecoder_->GetStream()),
                                                    data_ptr,
                                                    false);
                           return frame;
                       });
    }
    catch (...) {
        throw; // Preserve original exception
    }

    // Validate decoding results
    if (decodedFrames.empty()) {
        throw std::runtime_error("No frames decoded");
    }

    return decodedFrames.back();
}

PYBIND11_MODULE(_decoder, m) {
    ExternalBuffer::Export(m);

    py::class_<VideoDecoder>(m, "VideoDecoder", R"pydoc(Video decoder with NvCodec acceleration.)pydoc")
        .def(py::init<const int, const std::string&>(),
             py::arg("gpu_id"),
             py::arg("codec"),
             py::doc(R"(Create a video decoder instance.

Args:
    gpuid (int): GPU device ID to use for decoding.
    codec (int): Codec of the video stream to be decoded which contains h265, hevc, h264, av1, v9.)"))
        .def("decode",
             &VideoDecoder::decode,
             py::arg("video_path"),
             py::arg("frame_index"),
             py::doc(R"pbdoc(Decode a single frame from a video file.

This function decodes a single frame from a video file using the provided demuxer and decoder objects.

Args:
    video_path (str): The path to the video file to be decoded.
    frame_index (int): The index of the frame to be decoded.

Returns:
    A DecodedFrame object representing the decoded frame.

Raises:
    RuntimeError: if there are issues such as file opening failure, decoding failure, or target frame not found.)pbdoc"))
        .def("gpuId", &VideoDecoder::gpuId, py::doc(R"(ID of the GPU being used for decoding)"))
        .def("codec", &VideoDecoder::codec, py::doc(R"(Video codec format being decoded)"));

    py::class_<DecodedFrame, std::shared_ptr<DecodedFrame>>(m, "DecodedFrame")
        .def_readonly("timestamp", &DecodedFrame::timestamp)
        .def_readonly("format", &DecodedFrame::format)
        .def_property_readonly(
            "shape",
            [](std::shared_ptr<DecodedFrame>& self) { return self->extBuf->shape(); },
            py::doc(R"(Get the shape of the buffer as an array)"))
        .def("__repr__",
             [](std::shared_ptr<DecodedFrame>& self) {
                 std::stringstream ss;
                 ss << "<DecodedFrame [";
                 ss << "timestamp=" << self->timestamp;
                 ss << ", " << py::str(py::cast(self->views));
                 ss << "]>";
                 return ss.str();
             })
        .def(
            "__dlpack__",
            [](std::shared_ptr<DecodedFrame>& self, py::object stream) { return self->extBuf->dlpack(stream); },
            py::arg("stream") = NULL,
            py::doc(R"(Export the buffer as a DLPack tensor)"))
        .def(
            "__dlpack_device__",
            [](std::shared_ptr<DecodedFrame>&) {
                return py::make_tuple(py::int_(static_cast<int>(DLDeviceType::kDLCUDA)), py::int_(static_cast<int>(0)));
            },
            py::doc(R"(Get the device associated with the buffer)"));

    py::class_<CAIMemoryView, std::shared_ptr<CAIMemoryView>>(m, "CAIMemoryView")
        .def(py::init<std::vector<size_t>, std::vector<size_t>, std::string, size_t, CUdeviceptr, bool>())
        .def_readonly("shape", &CAIMemoryView::shape)
        .def_readonly("stride", &CAIMemoryView::stride)
        .def_readonly("dataptr", &CAIMemoryView::data)
        .def("__repr__",
             [](std::shared_ptr<CAIMemoryView>& self) {
                 std::stringstream ss;
                 ss << "<CAIMemoryView ";
                 ss << py::str(py::cast(self->shape));
                 ss << ">";
                 return ss.str();
             })
        .def_readonly("data", &CAIMemoryView::data)
        .def_property_readonly("__cuda_array_interface__", [](std::shared_ptr<CAIMemoryView>& self) {
            py::dict dict;
            dict["version"] = 3;
            dict["shape"] = self->shape;
            dict["strides"] = self->stride;
            dict["typestr"] = self->typestr;
            dict["stream"] = self->stream == 0 ? int(size_t(self->stream)) : 2;
            dict["data"] = std::make_pair(self->data, false);
            dict["gpuIdx"] = 0;
            return dict;
        });
}
