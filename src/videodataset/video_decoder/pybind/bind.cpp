#include <pybind11/pybind11.h>
#include "video_decoder.hpp"
#include "ExternalBuffer.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_decoder, m) {
    ExternalBuffer::Export(m);
    py::class_<VideoDecoder>(m, "VideoDecoder")
	.def(py::init<const int, const std::string>())
        .def("decode", &VideoDecoder::decode)
        .def_readwrite("gpuId", &VideoDecoder::gpuId)
        .def_readwrite("codec", &VideoDecoder::codec);
        // .def(py::pickle(
        //     [](const VideoDecoder& self) {
        //         return self.__getstate__();
        //     }, [](py::tuple t) {
        //         return VideoDecoder::__setstate__(t);
        // }));
    py::class_<DecodedFrame, std::shared_ptr<DecodedFrame>>(m, "DecodedFrame")
	.def_readonly("timestamp", &DecodedFrame::timestamp)
	.def_readonly("format", &DecodedFrame::format)
	.def_property_readonly("shape", [](std::shared_ptr<DecodedFrame>& self) {
			       return self->extBuf->shape(); }, "Get the shape of the buffer as an array")
	.def("__repr__", [](std::shared_ptr<DecodedFrame>& self){
			std::stringstream ss;
			ss << "<DecodedFrame [";
			ss << "timestamp=" << self->timestamp;
			ss << ", " << py::str(py::cast(self->views));
			ss << "]>";
			return ss.str();})
        .def("__dlpack__", [](std::shared_ptr<DecodedFrame>& self, py::object stream) {
		               return self->extBuf->dlpack(stream);}, py::arg("stream") = NULL, "Export the buffer as a DLPack tensor")
	.def("__dlpack_device__", [](std::shared_ptr<DecodedFrame>& self) {
			          return py::make_tuple(py::int_(static_cast<int>(DLDeviceType::kDLCUDA)),
				         py::int_(static_cast<int>(0)));}, "Get the device associated with the buffer");
    py::class_<CAIMemoryView, std::shared_ptr<CAIMemoryView>>(m, "CAIMemoryView")
	.def(py::init<std::vector<size_t>, std::vector<size_t>, std::string, size_t, CUdeviceptr, bool>())
	.def_readonly("shape", &CAIMemoryView::shape)
	.def_readonly("stride", &CAIMemoryView::stride)
	.def_readonly("dataptr", &CAIMemoryView::data)
	.def("__repr__", [](std::shared_ptr<CAIMemoryView>& self){
			    std::stringstream ss;
			    ss << "<CAIMemoryView ";
			    ss << py::str(py::cast(self->shape));																         ss << ">";
			    return ss.str();})
	.def_readonly("data", &CAIMemoryView::data)
	.def_property_readonly("__cuda_array_interface__",
			[](std::shared_ptr<CAIMemoryView>& self){
			   py::dict dict;dict["version"] = 3;
			   dict["shape"] = self->shape;
			   dict["strides"] = self->stride;
			   dict["typestr"] = self->typestr;
			   dict["stream"] = self->stream == 0 ? int(size_t(self->stream)) :2;
			   dict["data"] = std::make_pair(self->data, false);
			   dict["gpuIdx"] = 0;
			   return dict;
		       });
}
