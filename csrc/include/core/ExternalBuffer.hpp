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

#ifndef EXTERNAL_BUFFER_HPP
#define EXTERNAL_BUFFER_HPP

#include "DLPackUtils.hpp"

#include <cuda.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>


namespace py = pybind11;

class ExternalBuffer final : public std::enable_shared_from_this<ExternalBuffer>
{
public:
    static void Export(py::module &m);


    const DLTensor &dlTensor() const;

    py::tuple  shape() const;
    py::tuple  strides() const;
    std::string dtype() const;

    void *data() const;

    //bool load(PyObject *o);
    explicit ExternalBuffer(DLPackTensor&& dlTensor);


    ExternalBuffer() = default;
    py::capsule dlpack(py::object stream) const;
    int LoadDLPack(std::vector<size_t> _shape, std::vector<size_t> _stride, std::string _typeStr, int gpuid, size_t _streamid, CUdeviceptr _data, bool _readOnly);

private:


    friend py::detail::type_caster<ExternalBuffer>;

    DLPackTensor                    m_dlTensor;

    // __dlpack__ implementation

    // __dlpack_device__ implementation
    py::tuple dlpackDevice() const;
};



#endif // EXTERNAL_BUFFER_HPP
