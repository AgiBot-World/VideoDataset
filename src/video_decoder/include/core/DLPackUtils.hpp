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

#ifndef DLPACKUTILS_HPP
#define DLPACKUTILS_HPP

#include <pybind11/buffer_info.h>
#include <dlpack/dlpack.h>

namespace py = pybind11;

class DLPackTensor final
{
public:
    DLPackTensor() noexcept;
    explicit DLPackTensor(const DLTensor &tensor);
    explicit DLPackTensor(DLManagedTensor &&tensor);
    explicit DLPackTensor(const py::buffer_info &info, const DLDevice &dev);

    DLPackTensor(DLPackTensor &&that) noexcept;
    ~DLPackTensor();

    DLPackTensor &operator=(DLPackTensor &&that) noexcept;

    const DLTensor *operator->() const;
    DLTensor       *operator->();

    const DLTensor &operator*() const;
    DLTensor       &operator*();

private:
    DLManagedTensor m_tensor;
};




#endif // DLPACKUTILS_HPP
