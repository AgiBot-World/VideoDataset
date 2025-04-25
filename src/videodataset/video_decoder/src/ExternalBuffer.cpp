/*
 * This copyright notice applies to this file only
 *
 * SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: MIT
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */

#include "ExternalBuffer.hpp"

#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <functional> // for std::multiplies

using namespace py::literals;

static void CheckValidCUDABuffer(const void *ptr)
{
    if (ptr == nullptr)
    {
        throw std::runtime_error("NULL CUDA buffer not accepted");
    }

    //TBD
    //cudaPointerAttributes attrs = {};
    //cudaError_t           err   = cudaPointerGetAttributes(&attrs, ptr);
    //cudaGetLastError(); // reset the cuda error (if any)
    //if (err != cudaSuccess || attrs.type == cudaMemoryTypeUnregistered)
    //{
    //    throw std::runtime_error("Buffer is not CUDA-accessible");
    //}
}

//static std::string ToFormatString(const DLDataType &dtype)
//{
//    py::dtype dt = ToDType(ToNVCVDataType(dtype));
//    return dt.attr("str").cast<std::string>();
//}

ExternalBuffer::ExternalBuffer(DLPackTensor &&dlTensor)
{
    //{
    //    throw std::runtime_error("Only CUDA memory buffers can be wrapped");
    //}

    if (dlTensor->data != nullptr)
    {
        CheckValidCUDABuffer(dlTensor->data);
    }

    m_dlTensor = std::move(dlTensor);
}

py::tuple ExternalBuffer::shape() const
{
    py::tuple shape(m_dlTensor->ndim);
    for (size_t i = 0; i < shape.size(); ++i)
    {
        shape[i] = m_dlTensor->shape[i];
    }

    return shape;
}

py::tuple ExternalBuffer::strides() const
{
    py::tuple strides(m_dlTensor->ndim);

    for (size_t i = 0; i < strides.size(); ++i)
    {
        strides[i] = m_dlTensor->strides[i];
    }

    return strides;
}

std::string ExternalBuffer::dtype() const
{
    return std::string("|u1");
    //return (m_dlTensor->dtype);

}

void *ExternalBuffer::data() const
{
    return m_dlTensor->data;
}

py::capsule ExternalBuffer::dlpack(py::object stream) const
{
    struct ManagerCtx
    {
        DLManagedTensor tensor;
        std::shared_ptr<const ExternalBuffer> extBuffer;
    };

    auto ctx = std::make_unique<ManagerCtx>();

    // Set up tensor deleter to delete the ManagerCtx
    ctx->tensor.manager_ctx = ctx.get();
    ctx->tensor.deleter = [](DLManagedTensor *tensor)
    {
        auto *ctx = static_cast<ManagerCtx *>(tensor->manager_ctx);
        delete ctx;
    };

    // Copy tensor data
    ctx->tensor.dl_tensor = *m_dlTensor;

    // Manager context holds a reference to this External Buffer so that
    // GC doesn't delete this buffer while the dlpack tensor still refers to it.
    ctx->extBuffer = this->shared_from_this();

    // Creates the python capsule with the DLManagedTensor instance we're returning.
    py::capsule cap(&ctx->tensor, "dltensor", [](PyObject *ptr)
                    {
                        if(PyCapsule_IsValid(ptr, "dltensor"))
                        {
                            // If consumer didn't delete the tensor,
                            if(auto *dlTensor = static_cast<DLManagedTensor *>(PyCapsule_GetPointer(ptr, "dltensor")))
                            {
                                // Delete the tensor.
                                if(dlTensor->deleter != nullptr)
                                {
                                    dlTensor->deleter(dlTensor);
                                }
                            }
                        }
                    });

    // Now that the capsule is created and the manager ctx was transfered to it,
    // we can release the unique_ptr.
    ctx.release();

    return cap;
}

py::tuple ExternalBuffer::dlpackDevice() const
{
    return py::make_tuple(py::int_(static_cast<int>(m_dlTensor->device.device_type)),
                          py::int_(static_cast<int>(m_dlTensor->device.device_id)));
}

const DLTensor &ExternalBuffer::dlTensor() const
{
    return *m_dlTensor;
}

void ExternalBuffer::Export(py::module &m)
{
    py::class_<ExternalBuffer, std::shared_ptr<ExternalBuffer>>(m, "ExternalBuffer", py::dynamic_attr())
        .def_property_readonly("shape", &ExternalBuffer::shape, "Get the shape of the buffer as an array")
        .def_property_readonly("strides", &ExternalBuffer::strides, "Get the strides of the buffer")
        .def_property_readonly("dtype", &ExternalBuffer::dtype, "Get the data type of the buffer")
        .def("__dlpack__", &ExternalBuffer::dlpack, "stream"_a=1, "Export the buffer as a DLPack tensor")
        .def("__dlpack_device__", &ExternalBuffer::dlpackDevice, "Get the device associated with the buffer");
}

int ExternalBuffer::LoadDLPack( std::vector<size_t> _shape, std::vector<size_t> _stride, std::string _typeStr, int gpuid, size_t _streamid, CUdeviceptr _data, bool _readOnly)
{
    m_dlTensor->byte_offset = 0;

    // TODO: infer the device type from the memory buffer
    m_dlTensor->device.device_type = kDLCUDA;
    // TODO: infer the device from the memory buffer
    m_dlTensor->device.device_id = gpuid;

    // Convert data

    void* ptr = reinterpret_cast<void*>(_data);
    CheckValidCUDABuffer(ptr);
    m_dlTensor->data = ptr;

    // Convert DataType
    if (_typeStr != "|u1" && _typeStr != "B")  // TODO: can also be other letters
    {
        throw std::runtime_error("Could not create DL Pack tensor! Invalid typstr: " + _typeStr);
        return -1;
    }
    int itemSizeDT = sizeof(uint8_t);// dt.itemsize() 

    m_dlTensor->dtype.code = kDLUInt;
    m_dlTensor->dtype.bits = 8;
    m_dlTensor->dtype.lanes = 1;

    // Convert ndim
    m_dlTensor->ndim = _shape.size();

    // Convert shape
    m_dlTensor->shape = new int64_t[m_dlTensor->ndim];
    for (int i = 0; i < m_dlTensor->ndim; ++i)
    {
        m_dlTensor->shape[i] = _shape[i];
    }

    // Convert strides
    m_dlTensor->strides = new int64_t[m_dlTensor->ndim];
    for (int i = 0; i < m_dlTensor->ndim; ++i)
    {
        m_dlTensor->strides[i] = _stride[i];
        if (m_dlTensor->strides[i] % itemSizeDT != 0)
        {
            throw std::runtime_error("Stride must be a multiple of the element size in bytes");
            return -1;
        }
        m_dlTensor->strides[i] /= itemSizeDT;
    }

    return 0;
}
