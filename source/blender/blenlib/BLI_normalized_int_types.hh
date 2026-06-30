/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#pragma once

/** \file
 * \ingroup bli
 */

#include "BLI_math_vector.hh"

namespace blender {

namespace detail {

/* Plain bit-field storage for the packed components, deliberately kept free of
 * any `VecBase`-typed members.
 *
 * MSVC 14.44 (cl 19.44.x, both .35216 and .35228) hits a front-end internal
 * compiler error (C1001 in msc1.cpp) while *completing* a class template that
 * declares these bit-fields and also carries `VecBase` members/typedefs in the
 * same class. Isolating the bit-fields into their own base sidesteps the bug
 * while preserving the public `.x/.y/.z/.w` fields that GPU packing code writes
 * to directly (e.g. stashing selection flags into `w`). The component logic
 * lives in `NormalizedIntVec` below, which only *inherits* the bit-fields. */
/* NOTE: Plain (non-variadic, non-partially-specialized) templates. Declaring
 * the bit-fields inside a partial specialization of a variadic primary also
 * tickles the MSVC 14.44 C1001, so the two component counts get their own
 * straightforward storage template instead. */
template<typename T, int SizeX, int SizeY> struct NormalizedIntStorage2 {
  T x : SizeX;
  T y : SizeY;

  NormalizedIntStorage2() = default;
  constexpr NormalizedIntStorage2(T x_, T y_) : x(x_), y(y_) {}
};

template<typename T, int SizeX, int SizeY, int SizeZ, int SizeW> struct NormalizedIntStorage4 {
  T x : SizeX;
  T y : SizeY;
  T z : SizeZ;
  T w : SizeW;

  NormalizedIntStorage4() = default;
  constexpr NormalizedIntStorage4(T x_, T y_, T z_, T w_) : x(x_), y(y_), z(z_), w(w_) {}
};

template<typename T, int CompLen, int... CompBitCounts> struct NormalizedIntVec;

template<typename T, int SizeX, int SizeY>
struct NormalizedIntVec<T, 2, SizeX, SizeY> : NormalizedIntStorage2<T, SizeX, SizeY> {
  using Storage = NormalizedIntStorage2<T, SizeX, SizeY>;
  using VecT = VecBase<float, 2>;
  using IntVecT = VecBase<T, 2>;
  constexpr static bool is_signed = std::is_signed<T>();
  constexpr static T x_max = (1 << (SizeX - int(is_signed))) - 1;
  constexpr static T y_max = (1 << (SizeY - int(is_signed))) - 1;

  NormalizedIntVec() = default;
  constexpr NormalizedIntVec(IntVecT value) : Storage(value.x, value.y) {}

  operator IntVecT() const
  {
    return IntVecT(this->x, this->y);
  }

  static constexpr VecT max()
  {
    return VecT(x_max, y_max);
  }

  static constexpr VecT min()
  {
    if (is_signed) {
      return VecT(-x_max, -y_max);
    }
    return VecT(0.0f, 0.0f);
  }
};

template<typename T, int SizeX, int SizeY, int SizeZ, int SizeW>
struct NormalizedIntVec<T, 4, SizeX, SizeY, SizeZ, SizeW>
    : NormalizedIntStorage4<T, SizeX, SizeY, SizeZ, SizeW> {
  using Storage = NormalizedIntStorage4<T, SizeX, SizeY, SizeZ, SizeW>;
  using VecT = VecBase<float, 4>;
  using IntVecT = VecBase<T, 4>;
  constexpr static bool is_signed = std::is_signed<T>();
  constexpr static T x_max = (1 << (SizeX - int(is_signed))) - 1;
  constexpr static T y_max = (1 << (SizeY - int(is_signed))) - 1;
  constexpr static T z_max = (1 << (SizeZ - int(is_signed))) - 1;
  constexpr static T w_max = (1 << (SizeW - int(is_signed))) - 1;

  NormalizedIntVec() = default;
  constexpr NormalizedIntVec(IntVecT value) : Storage(value.x, value.y, value.z, value.w) {}

  operator IntVecT() const
  {
    return IntVecT(this->x, this->y, this->z, this->w);
  }

  static constexpr VecT max()
  {
    return VecT(x_max, y_max, z_max, w_max);
  }

  static constexpr VecT min()
  {
    if constexpr (is_signed) {
      return VecT(-x_max, -y_max, -z_max, -w_max);
    }
    return VecT(0.0f, 0.0f, 0.0f, 0.0f);
  }
};

}  // namespace detail

template<typename T, int CompLen, int... CompBitCounts>
  requires(std::is_same_v<T, int32_t> || std::is_same_v<T, uint32_t>)
struct NormalizedIntVecBase : detail::NormalizedIntVec<T, CompLen, CompBitCounts...> {
  using IntPacked = detail::NormalizedIntVec<T, CompLen, CompBitCounts...>;
  using typename IntPacked::IntVecT;
  using typename IntPacked::VecT;

  NormalizedIntVecBase() = default;

  NormalizedIntVecBase(IntVecT value) : IntPacked(value) {}

  /* Adding rounding would be the standard compliant conversion.
   * But this would introduce perf regression. */
  NormalizedIntVecBase(VecT val)
      : IntPacked(IntVecT(math::clamp(val * IntPacked::max(), IntPacked::min(), IntPacked::max())))
  {
  }

  operator VecT() const
  {
    return VecT(IntVecT(*this)) / IntPacked::max();
  }
};

using char4_norm = NormalizedIntVecBase<int32_t, 4, 8, 8, 8, 8>;
using uchar4_norm = NormalizedIntVecBase<uint32_t, 4, 8, 8, 8, 8>;
using short2_norm = NormalizedIntVecBase<int32_t, 2, 16, 16>;
using ushort2_norm = NormalizedIntVecBase<uint32_t, 2, 16, 16>;
using short4_norm = NormalizedIntVecBase<int32_t, 4, 16, 16, 16, 16>;
using ushort4_norm = NormalizedIntVecBase<uint32_t, 4, 16, 16, 16, 16>;
using int1010102_norm = NormalizedIntVecBase<int32_t, 4, 10, 10, 10, 2>;
using uint1010102_norm = NormalizedIntVecBase<uint32_t, 4, 10, 10, 10, 2>;

}  // namespace blender
