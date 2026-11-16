{
  "manifest": {
    "run_name": "session-date",
    "benchmark": "locomo",
    "conversations": "0",
    "mem0_ref": "code/session-date",
    "mem0_commit": "46c6add7633cc4a4a04f9120b675c00cc1114a74",
    "experiments_commit": "971aff77d72986f6af3a9aeb9be1fd46e2080f11",
    "benchmarks_upstream_commit": "4b61c5d31b9c668a12b4f5e78064248a02c82d2b",
    "extraction_llm": "gpt-4o-mini",
    "embedder": "text-embedding-3-small",
    "answerer_model": "gpt-5",
    "judge_model": "gpt-5",
    "forward_timestamp": "1",
    "trace_enabled": "1",
    "extra_args": "",
    "started_utc": "2026-11-14T03:02:35Z",
    "trace": {
      "enabled": "1",
      "mem0_trace": {
        "present": true,
        "file": "mem0_trace.jsonl.gz",
        "events": 10091,
        "recorder_errors": 0,
        "raw_bytes": 80805123,
        "gz_bytes": 25482830
      },
      "eval_trace": {
        "present": true,
        "file": "eval_trace.jsonl.gz",
        "events": 1788,
        "recorder_errors": 0,
        "raw_bytes": 14763792,
        "gz_bytes": 2678906
      }
    }
  },
  "results_file": "locomo_results_20261114_060432.json",
  "results_file_mtime_utc": "2026-11-14T06:04:33Z",
  "metadata": {
    "benchmark": "locomo",
    "project_name": "locomo-conv0-session-date",
    "run_id": "3e48fbac",
    "timestamp": "20261114_060432",
    "answerer_model": "gpt-5",
    "judge_model": "gpt-5",
    "provider": "openai",
    "top_k": 200,
    "top_k_cutoffs": [
      "top_10",
      "top_20",
      "top_50",
      "top_200"
    ],
    "total_questions": 152,
    "categories": [
      1,
      2,
      3,
      4
    ]
  },
  "metrics_by_cutoff": {
    "top_10": {
      "overall": {
        "total": 152,
        "correct": 122,
        "accuracy": 80.26315789473685,
        "avg_score": 80.26315789473685
      },
      "by_category": {
        "multi-hop": {
          "total": 32,
          "correct": 24,
          "accuracy": 75.0,
          "avg_score": 75.0
        },
        "open-domain": {
          "total": 13,
          "correct": 12,
          "accuracy": 92.3076923076923,
          "avg_score": 92.3076923076923
        },
        "single-hop": {
          "total": 70,
          "correct": 51,
          "accuracy": 72.85714285714285,
          "avg_score": 72.85714285714285
        },
        "temporal": {
          "total": 37,
          "correct": 35,
          "accuracy": 94.5945945945946,
          "avg_score": 94.5945945945946
        }
      }
    },
    "top_20": {
      "overall": {
        "total": 152,
        "correct": 122,
        "accuracy": 80.26315789473685,
        "avg_score": 80.26315789473685
      },
      "by_category": {
        "multi-hop": {
          "total": 32,
          "correct": 24,
          "accuracy": 75.0,
          "avg_score": 75.0
        },
        "open-domain": {
          "total": 13,
          "correct": 12,
          "accuracy": 92.3076923076923,
          "avg_score": 92.3076923076923
        },
        "single-hop": {
          "total": 70,
          "correct": 51,
          "accuracy": 72.85714285714285,
          "avg_score": 72.85714285714285
        },
        "temporal": {
          "total": 37,
          "correct": 35,
          "accuracy": 94.5945945945946,
          "avg_score": 94.5945945945946
        }
      }
    },
    "top_50": {
      "overall": {
        "total": 152,
        "correct": 128,
        "accuracy": 84.21052631578947,
        "avg_score": 84.21052631578947
      },
      "by_category": {
        "multi-hop": {
          "total": 32,
          "correct": 25,
          "accuracy": 78.125,
          "avg_score": 78.125
        },
        "open-domain": {
          "total": 13,
          "correct": 13,
          "accuracy": 100.0,
          "avg_score": 100.0
        },
        "single-hop": {
          "total": 70,
          "correct": 54,
          "accuracy": 77.14285714285715,
          "avg_score": 77.14285714285715
        },
        "temporal": {
          "total": 37,
          "correct": 36,
          "accuracy": 97.2972972972973,
          "avg_score": 97.2972972972973
        }
      }
    },
    "top_200": {
      "overall": {
        "total": 152,
        "correct": 130,
        "accuracy": 85.52631578947368,
        "avg_score": 85.52631578947368
      },
      "by_category": {
        "multi-hop": {
          "total": 32,
          "correct": 27,
          "accuracy": 84.375,
          "avg_score": 84.375
        },
        "open-domain": {
          "total": 13,
          "correct": 13,
          "accuracy": 100.0,
          "avg_score": 100.0
        },
        "single-hop": {
          "total": 70,
          "correct": 54,
          "accuracy": 77.14285714285715,
          "avg_score": 77.14285714285715
        },
        "temporal": {
          "total": 37,
          "correct": 36,
          "accuracy": 97.2972972972973,
          "avg_score": 97.2972972972973
        }
      }
    }
  },
  "n_questions": 152,
  "ingestion": {
    "chunks_processed": 419,
    "chunks_failed": 0
  },
  "search_latency_ms": {
    "mean": 4778.395394736842,
    "median": 580.45
  },
  "calls_by_design": {
    "answer_calls": 608,
    "judge_calls": 608,
    "mem0_add_requests": 419
  },
  "retrieved_memory_tokens_o200k_base": {
    "top_10": {
      "mean": 261.42763157894734,
      "median": 278.0
    },
    "top_20": {
      "mean": 517.7302631578947,
      "median": 561.0
    },
    "top_50": {
      "mean": 1274.9868421052631,
      "median": 1379.0
    },
    "top_200": {
      "mean": 4931.230263157895,
      "median": 5207.5
    }
  }
}
