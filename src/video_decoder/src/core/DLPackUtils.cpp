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

#include <pybind11/stl.h>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include "core/PyCAIMemoryView.hpp"


namespace py = pybind11;
#include "core/DLPackUtils.hpp"


static std::string ProcessBufferInfoFormat(const std::string& fmt)
{
    // pybind11 (as of v2.6.2) doesn't recognize formats 'l' and 'L',
    // which according to https://docs.python.org/3/library/struct.html#format-characters
    // are equal to 'i' and 'I', respectively.
    if (fmt == "l")
    {
        return "i";
    }
    else if (fmt == "L")
    {
        return "I";
    }
    else
    {
        return fmt;
    }
}

py::dtype ToDType(const py::buffer_info& info)
{
    std::string fmt = ProcessBufferInfoFormat(info.format);

    PyObject* ptr = nullptr;
    if ((py::detail::npy_api::get().PyArray_DescrConverter_(py::str(fmt).ptr(), &ptr) == 0) || !ptr)
    {
        PyErr_Clear();
        return py::dtype(info);
    }
    else
    {
        return py::dtype(fmt);
    }
}

py::dtype ToDType(const std::string& fmt)
{
    py::buffer_info buf;
    buf.format = ProcessBufferInfoFormat(fmt);

    return ToDType(buf);
}

DLPackTensor::DLPackTensor() noexcept
    : m_tensor{}
{
}

DLPackTensor::DLPackTensor(DLManagedTensor &&managedTensor)
    : m_tensor{std::move(managedTensor)}
{
    managedTensor = {};
}

DLPackTensor::DLPackTensor(const DLTensor &tensor)
    : DLPackTensor(DLManagedTensor{tensor})
{
}

DLPackTensor::DLPackTensor(const py::buffer_info &info, const DLDevice &dev)
    : m_tensor{}
{
    DLTensor &dlTensor = m_tensor.dl_tensor;
    dlTensor.data      = info.ptr;


    //TBD dtype

    dlTensor.dtype.code = kDLInt;
    dlTensor.dtype.bits = 8;
    dlTensor.dtype.lanes = 1;

    dlTensor.ndim        = info.ndim;
    dlTensor.device      = dev;
    dlTensor.byte_offset = 0;

    m_tensor.deleter = [](DLManagedTensor *self)
    {
        delete[] self->dl_tensor.shape;
        self->dl_tensor.shape = nullptr;

        delete[] self->dl_tensor.strides;
        self->dl_tensor.strides = nullptr;
    };

    try
    {
        dlTensor.shape = new int64_t[info.ndim];
        std::copy_n(info.shape.begin(), info.shape.size(), dlTensor.shape);

        dlTensor.strides = new int64_t[info.ndim];
        for (int i = 0; i < info.ndim; ++i)
        {
            if (info.strides[i] % info.itemsize != 0)
            {
                throw std::runtime_error("Stride must be a multiple of the element size in bytes");
            }

            dlTensor.strides[i] = info.strides[i] / info.itemsize;
        }
    }
    catch (...)
    {
        m_tensor.deleter(&m_tensor);
        throw;
    }
}


DLPackTensor::DLPackTensor(DLPackTensor &&that) noexcept
    : m_tensor{std::move(that.m_tensor)}
{
    that.m_tensor = {};
}

DLPackTensor::~DLPackTensor()
{
    if (m_tensor.deleter)
    {
        m_tensor.deleter(&m_tensor);
    }
}

DLPackTensor &DLPackTensor::operator=(DLPackTensor &&that) noexcept
{
    if (this != &that)
    {
        if (m_tensor.deleter)
        {
            m_tensor.deleter(&m_tensor);
        }
        m_tensor = std::move(that.m_tensor);

        that.m_tensor = {};
    }
    return *this;
}

const DLTensor *DLPackTensor::operator->() const
{
    return &m_tensor.dl_tensor;
}

DLTensor *DLPackTensor::operator->()
{
    return &m_tensor.dl_tensor;
}

const DLTensor &DLPackTensor::operator*() const
{
    return m_tensor.dl_tensor;
}

DLTensor &DLPackTensor::operator*()
{
    return m_tensor.dl_tensor;
}



