## Benchmarks

**1 potential regression(s)** detected (>5.0% slower)
**1 improvement(s)** detected

### Parse

| Benchmark | Base | PR | Change |
|-----------|------|-----|--------|
| `parse_large` | 321.800 µs | 360.000 µs | +11.9% ❌ |
| `parse_small` | 1.599 ms | 1.550 ms | -3.1% ✅ |

### Transform

| Benchmark | Base | PR | Change |
|-----------|------|-----|--------|
| `transform_large` | 318.000 µs | N/A | 🗑️ |
| `transform_new` | N/A | 500.000 µs | 🆕 |
| `transform_small` | 1.551 ms | 1.551 ms | +0.0% |