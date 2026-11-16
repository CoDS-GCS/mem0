# Metrics

- answerer model: `gpt-5`; memory-token encoding: `o200k_base`
- per-question cutoff: **200** (largest cutoff the answerer ran at)
- wrote `per_question_metrics.csv` (152 rows), `per_session_metrics.csv` (419 rows)
- judge cost is intentionally **not** measured.

## Per-question latency & tokens (overall)
### all questions
- search_latency_ms: n=152, mean=4778.4, p50=580.45, p95=58134.43
- total_latency_ms: n=152, mean=15538.81, p50=8754.48, p95=86140.24
- memory_tokens: n=141, mean=6716.63, p50=6661.0, p95=7301.0

## Per-question by category
### multi-hop
- search_latency_ms: n=32, mean=616.51, p50=559.0, p95=807.34
- total_latency_ms: n=32, mean=13449.09, p50=12135.75, p95=25683.42
- memory_tokens: n=32, mean=6671.12, p50=6570.5, p95=7281.85

### open-domain
- search_latency_ms: n=13, mean=624.26, p50=581.3, p95=875.0
- total_latency_ms: n=13, mean=11323.12, p50=11466.77, p95=15222.71
- memory_tokens: n=13, mean=6645.23, p50=6646.0, p95=6985.0

### single-hop
- search_latency_ms: n=70, mean=9658.33, p50=580.2, p95=58525.73
- total_latency_ms: n=70, mean=21093.06, p50=8560.11, p95=86552.04
- memory_tokens: n=59, mean=6665.66, p50=6636.0, p95=7269.0

### temporal
- search_latency_ms: n=37, mean=605.11, p50=593.4, p95=755.22
- total_latency_ms: n=37, mean=8319.28, p50=7712.59, p95=11709.54
- memory_tokens: n=37, mean=6862.35, p50=6869.0, p95=7370.0

## Memory building (conversation totals)
- add requests: 419; memories stored: 771
- total extraction tokens: prompt=3540698, completion=39787, total=3580485
- total add time (client): 1443558.4 ms over 419 measured add(s)
