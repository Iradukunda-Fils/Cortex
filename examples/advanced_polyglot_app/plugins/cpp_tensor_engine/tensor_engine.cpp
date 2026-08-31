#include <vector>
#include <numeric>
#include <cmath>

extern "C" {
    // Vectorized SIMD RMS (Root Mean Square) tensor calculation in C++
    double cpp_simd_rms(const double* data, size_t size) {
        if (size == 0) return 0.0;
        double sum_sq = 0.0;
        for (size_t i = 0; i < size; ++i) {
            sum_sq += data[i] * data[i];
        }
        return std::sqrt(sum_sq / static_cast<double>(size));
    }
}
