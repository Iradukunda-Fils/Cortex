#include <stdint.h>
#include <stddef.h>

// High-speed vector dot product in C
double c_dot_product(const double* a, const double* b, size_t n) {
    double sum = 0.0;
    for (size_t i = 0; i < n; ++i) {
        sum += a[i] * b[i];
    }
    return sum;
}
