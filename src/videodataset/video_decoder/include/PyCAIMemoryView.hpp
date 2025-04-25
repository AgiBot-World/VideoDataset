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

#pragma once
#include <pybind11/stl.h>
#include <sstream>
#include <cuda.h>
#include <pybind11/pybind11.h>
#include <string>
#include <vector>
#include "nvEncodeAPI.h"
#include "NvCodecUtils.h"
#include "ExternalBuffer.hpp"
using namespace std;
//using namespace chrono;

namespace py = pybind11;

/**
* @brief providing seek functionality within demuxer.
*/

#define ThrowOnCudaError_STRINGIFY(s)  ThrowOnCudaError_STRINGIFY_(s)
#define ThrowOnCudaError_STRINGIFY_(s) #s
#define ThrowOnCudaError(expr)                                                 \
  {                                                                            \
    auto res = (expr);                                                         \
    if (CUDA_SUCCESS != res)                                                   \
    {                                                                          \
      std::stringstream ss;                                                    \
      ss << __FILE__ << ":";                                                   \
      ss << __LINE__ << std::endl;                                             \
      const char * errName = nullptr;                                          \
      if (CUDA_SUCCESS != cuGetErrorName(res, &errName))                       \
      {                                                                        \
        ss << "CUDA error with code " << res << std::endl;                     \
      }                                                                        \
      else                                                                     \
      {                                                                        \
        ss << "CUDA error: " << errName << std::endl;                          \
      }                                                                        \
      const char * errDesc = nullptr;                                          \
      cuGetErrorString(res, &errDesc);                                         \
      if (!errDesc)                                                            \
      {                                                                        \
        ss << "No error string available" << std::endl;                        \
      }                                                                        \
      else                                                                     \
      {                                                                        \
        ss << errDesc << std::endl;                                            \
      }                                                                        \
      ss << "while executing: " ThrowOnCudaError_STRINGIFY(expr) << std::endl; \
      throw std::runtime_error(ss.str());                                      \
    }                                                                          \
  }

namespace
{

    class CuCtxGuard
    {
        CUcontext m_ctx;

    public:
        CuCtxGuard(CUcontext ctx) : m_ctx(ctx)
        {
            cuCtxPushCurrent_v2(ctx);
        }

        ~CuCtxGuard()
        {
            cuCtxPopCurrent(&m_ctx);
        }
    };
}  // namespace

#define ENUM_VALUE_STRINGIFY(s)  ENUM_VALUE_STRINGIFY_(s)
#define ENUM_VALUE_STRINGIFY_(s) #s
#define ENUM_VALUE(prefix, s)    value(ENUM_VALUE_STRINGIFY(s), prefix##_##s)
#define DEF_CONSTANT(s)          attr(ENUM_VALUE_STRINGIFY(s)) = py::cast(s)
#define DEF_READWRITE(type, s)   def_readwrite(ENUM_VALUE_STRINGIFY(s), &type::s)


enum Pixel_Format {
    Pixel_Format_UNDEFINED = 0,
    Pixel_Format_NV12 = 3,
    Pixel_Format_YUV444 = 4,
    Pixel_Format_P016 = 5,
    Pixel_Format_YUV444_16Bit = 6

};


struct CAIMemoryView
{
  std::vector<size_t>  shape;
  std::vector<size_t>  stride;
  std::string          typestr;
  CUstream             stream = nullptr;
  CUdeviceptr          data;
  bool                 readOnly;
    public:
  CAIMemoryView(std::vector<size_t> _shape, std::vector<size_t> _stride, std::string _typeStr, size_t _streamid, CUdeviceptr _data,  bool _readOnly)
 {
      shape = _shape;
      stride= _stride;
      typestr = _typeStr;
      data = _data;
      readOnly= _readOnly;
      stream = reinterpret_cast<CUstream>(_streamid);
  }
};

struct DecodedFrame
{
    int64_t                    timestamp;
    std::vector<CAIMemoryView> views;
    Pixel_Format format;
    std::shared_ptr<ExternalBuffer> extBuf;
    DecodedFrame(){
        extBuf = std::make_shared<ExternalBuffer>();
    }
};



CAIMemoryView  coerceToCudaArrayView(py::object cuda_array, NV_ENC_BUFFER_FORMAT bufferFormat, size_t width, size_t height, int planeIdx = 0);
