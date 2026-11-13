# Finance Research Projects

Two standalone research tools by Benjamin007-cell, with runnable examples and automated checks.

| Project | Implementation | Start here |
| --- | --- | --- |
| Fixed-Income & Order-Book Replay Engine | Rust matching core; Python replay and execution summaries | [Replay guide](replay-engine/README.md) |
| Financial Disclosure & Covenant Extractor | Python rules; PyTorch and Hugging Face token classification; annotation tools | [Extractor guide](disclosure-extractor/README.md) |

## Replay engine

Supports deterministic event replay, price-time priority, partial fills, cancellation, piecewise tick schedules and configurable maker/taker fees. Prices and quantities use integer units. Bond quotation conventions are controlled through a notional multiplier.

```sh
cd replay-engine
cargo test
cargo build --release
python3 python/replay.py data/events.csv
```

## Disclosure extractor

Includes PDF/DOCX candidate preparation with source hashes, an offline browser annotation worksheet, reviewed-label import, leakage checks, transformer training and overall/per-category exact-span evaluation.

```sh
cd disclosure-extractor
python3 -m unittest discover -s tests
python3 -m disclosure extract data/demo.jsonl predictions.jsonl
python3 -m disclosure evaluate data/demo.jsonl predictions.jsonl
```

Read the project guide for optional training dependencies and the annotation procedure.

## Verified status and limits

- Rust compilation, unit tests, CLI integration tests and replay demo passed in GitHub Actions.
- Python unit tests and the rule-based extraction/evaluation demo passed.
- A tiny randomly initialized BERT completed a synthetic training, saving, reloading and inference check locally. This is an integration check, not an accuracy benchmark or a useful financial model.
- A local 43-record review pilot was prepared from official Dangote Cement 2024 and Microsoft 2024 filings. Source links, hashes and status are in [the pilot manifest](disclosure-extractor/data/pilot-manifest.json). Excerpts are excluded from this public repository.
- A real-filing experimental fine-tune has now run using provisional AI annotations. Its weights are delivered separately, and it scored 0.0 exact-span F1 on 25 validation records. No independently validated F1 score is supplied. The proposed 88.4% score has not been established and must not be presented as achieved.

These are research implementations. The replay engine does not model settlement, accrued interest or venue-specific auctions; extraction quality requires dataset-specific annotation and evaluation. Each project documents its limits and includes an MIT license for its code. Third-party filings retain their own rights.

[Automated checks](https://github.com/Benjamin007-cell/New-born/actions)

## Latest experiment

An expanded six-issuer study produced a class-weighted model with 23.33% exact-span F1 on 58 issuer-held-out, weak-labeled records, versus 0.0 for the earlier model on the same sample. The 88.4% target was not reached. See [the full result and limitations](disclosure-extractor/RESEARCH_RESULT.md). The earlier experiment above remains part of the project history.
