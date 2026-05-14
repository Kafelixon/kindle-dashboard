#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace py = pybind11;

static std::vector<std::uint8_t> floyd_steinberg(
    const std::vector<std::uint8_t>& pixels,
    int width,
    int height,
    int levels) {
  if (width <= 0 || height <= 0) {
    throw std::invalid_argument("width and height must be positive");
  }
  if (levels < 2 || levels > 256) {
    throw std::invalid_argument("levels must be between 2 and 256");
  }
  if (pixels.size() != static_cast<std::size_t>(width * height)) {
    throw std::invalid_argument("pixel count does not match width * height");
  }

  std::vector<float> work(pixels.begin(), pixels.end());
  std::vector<std::uint8_t> out(pixels.size());
  const float step = 255.0f / static_cast<float>(levels - 1);

  for (int y = 0; y < height; ++y) {
    for (int x = 0; x < width; ++x) {
      const int index = y * width + x;
      const float old_value = std::clamp(work[index], 0.0f, 255.0f);
      const float new_value = std::round(old_value / step) * step;
      const float error = old_value - new_value;
      out[index] = static_cast<std::uint8_t>(std::clamp(new_value, 0.0f, 255.0f));

      if (x + 1 < width) work[index + 1] += error * 7.0f / 16.0f;
      if (y + 1 < height) {
        if (x > 0) work[index + width - 1] += error * 3.0f / 16.0f;
        work[index + width] += error * 5.0f / 16.0f;
        if (x + 1 < width) work[index + width + 1] += error * 1.0f / 16.0f;
      }
    }
  }

  return out;
}

PYBIND11_MODULE(_dither, m) {
  m.doc() = "C++ dithering routines for Kindle dashboard images";
  m.def("floyd_steinberg", &floyd_steinberg, py::arg("pixels"), py::arg("width"),
        py::arg("height"), py::arg("levels") = 16);
}
