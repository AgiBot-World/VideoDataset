#include <pybind11/pybind11.h>
#include "video_decoder.hpp"
#include "cuda_context.hpp"

PYBIND11_MODULE(_decoder, m) {
    pybind11::class_<VideoDecoder>(m, "VideoDecoder")
        .def("decode", &VideoDecoder::decode)
        .def(pybind11::init<int, std::string>())
        .def_readwrite("gpuId", &VideoDecoder::gpuId)
        .def_readwrite("codec", &VideoDecoder::codec);
}
