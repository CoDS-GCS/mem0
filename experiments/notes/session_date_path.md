# Session-date path: dataset → stored memory → answer prompt (Run A, v2.2.1 @ 94c3fe9)

Tracing one session of LoCoMo conversation 0 from the dataset date to the extractor's
Observation Date, to the stored payload, to the answer prompt. All line numbers verified
against the files in this tree (mem0/ is identical between 94c3fe9 and the current HEAD).

## Hops

| # | Hop | File:line | What happens to the date |
|---|-----|-----------|--------------------------|
| 1 | dataset field | `datasets/locomo/locomo10.json` | Each session has `session_<n>_date_time`, a human string, e.g. `"1:56 pm on 8 May, 2023"`. |
| 2 | harness reads it | `benchmarks/locomo/run.py:149-151` | `get_sorted_sessions` pairs `session_<n>` with `session_<n>_date_time`. |
| 3 | harness parses + converts | `benchmarks/locomo/run.py:307` → `134-141` → `125-133` | `locomo_date_to_epoch(date_str)`: `parse_locomo_date` reads the string as a **naive** datetime, then `.replace(tzinfo=timezone.utc)` and `int(...timestamp())`. Result = **unix epoch seconds, date interpreted as UTC.** |
| 4 | harness add call | `benchmarks/locomo/run.py:340` | `mem0.add(messages, user_id, timestamp=session_epoch)` — passes the epoch int as `timestamp`. |
| 5 | client builds HTTP body | `benchmarks/common/mem0_client.py:142-143` (`_add_oss`) | `payload["timestamp"] = timestamp` (the epoch int). POSTed to `{host}/memories` (L159). **The date is in the request body.** |
| 6 | server AddRequest | `docker/mem0/main.py:174-181` | `AddRequest` has **no `timestamp` field** and Pydantic defaults to ignoring unknown keys → **`timestamp` is silently dropped here.** (`observation_date` field exists but is never forwarded either, L216-217.) |
| 7 | server → SDK | `docker/mem0/main.py:203-223` | `add_memories` builds `params` from user_id/agent_id/run_id/metadata/custom_instructions only, then `mem.add(req.messages, **params)`. No date reaches the SDK. |
| 8 | SDK `Memory.add()` | `mem0/memory/main.py:760-768, 787, 817-818` | `add(..., timestamp=None, ...)`; `timestamp` is documented "Platform-only … Not supported in OSS" and **if non-None raises `ValueError`** (`get_temporal_feature_error_message`, see `notices.py`). Because hop 6 dropped it, the call arrives with `timestamp=None`, so no error — but no date either. |
| 9 | extraction prompt (Observation Date) | `mem0/memory/main.py:950-955` → `mem0/configs/prompts.py:1016-1041`, `1007-1013` | `_add_to_vector_store` calls `generate_additive_extraction_prompt(...)` **without `timestamp`**. The function *accepts* a `timestamp=` kwarg that would set Observation Date, but it is not passed, so `_resolve_dates` defaults `observation_date = current_date = datetime.now(timezone.utc).date()` → **Observation Date = machine clock (run day), not the session date.** Relative phrases ("yesterday", "recently") are resolved against this (prompts.py:524-533, 635). |
| 10 | stored payload created_at/updated_at | `mem0/memory/main.py:1035-1037` | `if "created_at" not in mem_metadata: mem_metadata["created_at"] = datetime.now(timezone.utc).isoformat()`; `updated_at = created_at`. **created_at = run time, not the session date.** (This is the additive ADD-only pipeline; no UPDATE path runs here.) |
| 11 | search result | `mem0/memory/main.py:1248-1255` (and search at 1365/1375-1376) | Each result carries `created_at`/`updated_at` from the payload unchanged. |
| 12 | answer prompt | `benchmarks/locomo/prompts.py:172, 176-179` | Memories sorted by `created_at`; each line printed as `(<human date of created_at>) <memory>` via `_to_human_date`. **The date the answerer sees = created_at = run time.** |

## Net effect (Run A)

The session date is present in the HTTP body (hop 5) but **dropped at the server's `AddRequest`
(hop 6)**. It never reaches the SDK, so the extractor's Observation Date (hop 9) and the stored
`created_at` (hop 10) are both the machine clock on the run day. The answerer is therefore shown
run-day dates instead of 2023 session dates (hop 12). This matches the observed temporal score
(6/37 at top_200).

## Unit / timezone of the harness timestamp

`timestamp` is **unix epoch seconds**, with the LoCoMo naive datetime **interpreted as UTC**
(`run.py:138-140`). Roundtrip check for every session of conversation 0
(`datetime.fromtimestamp(epoch, timezone.utc)` vs the LoCoMo string) — every day **and** time matches:

| session | LoCoMo date string | epoch | roundtrip (UTC) | same day+time |
|---|---|---|---|---|
| session_1  | 1:56 pm on 8 May, 2023        | 1683554160 | 2023-05-08T13:56:00+00:00 | ✅ |
| session_2  | 1:14 pm on 25 May, 2023       | 1685020440 | 2023-05-25T13:14:00+00:00 | ✅ |
| session_3  | 7:55 pm on 9 June, 2023       | 1686340500 | 2023-06-09T19:55:00+00:00 | ✅ |
| session_4  | 10:37 am on 27 June, 2023     | 1687862220 | 2023-06-27T10:37:00+00:00 | ✅ |
| session_5  | 1:36 pm on 3 July, 2023       | 1688391360 | 2023-07-03T13:36:00+00:00 | ✅ |
| session_6  | 8:18 pm on 6 July, 2023       | 1688674680 | 2023-07-06T20:18:00+00:00 | ✅ |
| session_7  | 4:33 pm on 12 July, 2023      | 1689179580 | 2023-07-12T16:33:00+00:00 | ✅ |
| session_8  | 1:51 pm on 15 July, 2023      | 1689429060 | 2023-07-15T13:51:00+00:00 | ✅ |
| session_9  | 2:31 pm on 17 July, 2023      | 1689604260 | 2023-07-17T14:31:00+00:00 | ✅ |
| session_10 | 8:56 pm on 20 July, 2023      | 1689886560 | 2023-07-20T20:56:00+00:00 | ✅ |
| session_11 | 2:24 pm on 14 August, 2023    | 1692023040 | 2023-08-14T14:24:00+00:00 | ✅ |
| session_12 | 1:50 pm on 17 August, 2023    | 1692280200 | 2023-08-17T13:50:00+00:00 | ✅ |
| session_13 | 3:31 pm on 23 August, 2023    | 1692804660 | 2023-08-23T15:31:00+00:00 | ✅ |
| session_14 | 1:33 pm on 25 August, 2023    | 1692970380 | 2023-08-25T13:33:00+00:00 | ✅ |
| session_15 | 3:19 pm on 28 August, 2023    | 1693235940 | 2023-08-28T15:19:00+00:00 | ✅ |
| session_16 | 12:09 am on 13 September, 2023| 1694563740 | 2023-09-13T00:09:00+00:00 | ✅ |
| session_17 | 10:31 am on 13 October, 2023  | 1697193060 | 2023-10-13T10:31:00+00:00 | ✅ |
| session_18 | 6:55 pm on 20 October, 2023   | 1697828100 | 2023-10-20T18:55:00+00:00 | ✅ |
| session_19 | 9:55 am on 22 October, 2023   | 1697968500 | 2023-10-22T09:55:00+00:00 | ✅ |

## Where Run C must intervene (to mirror the Platform `timestamp`)

Two SDK outputs must become the session date when (and only when) a `timestamp` is supplied:
- **hop 9** — pass the session date into `generate_additive_extraction_prompt(timestamp=<session date>)`
  so Observation Date = session date (the function already supports this kwarg).
- **hop 10** — set `created_at`/`updated_at` to the session datetime (ISO, clock time preserved).

Plus the plumbing that currently blocks it:
- **hop 8** — `Memory.add()` must accept `timestamp` instead of raising.
- **hop 6** — `AddRequest` must carry `timestamp` and forward it (behind `MEM0_FORWARD_TIMESTAMP`, default off).
