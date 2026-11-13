# Financial Disclosure & Covenant Extractor

A runnable rule baseline plus a PyTorch/Hugging Face token-classification fine-tuning pipeline for debt covenants, FX sensitivity disclosures and audit notes. Accepts text from NGX annual reports and SEC 10-K filings supplied by the user. No real filings, annotated corpus or trained weights are bundled.

**Status:** new implementation. No real-world F1 score is claimed. The proposed 88.4% entity F1 has not been established. Synthetic examples demonstrate interfaces only.

## Quick demo (Python 3.9+, no dependencies)
```sh
python3 -m disclosure extract data/demo.jsonl predictions.jsonl
python3 -m disclosure evaluate data/demo.jsonl predictions.jsonl
python3 -m unittest discover -s tests
```
The baseline finds keywords and emits whole-sentence spans. It is not the transformer model. Demo gold intentionally includes a decimal-containing sentence to illustrate sentence-boundary limitations. Demo metrics are not a benchmark.

## Train and run a transformer (Python 3.10+ recommended)
```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m disclosure pdf annual-report.pdf pages.jsonl
python -m disclosure train train.jsonl validation.jsonl models/covenants --epochs 3
python -m disclosure extract test.jsonl test-predictions.jsonl --model models/covenants
python -m disclosure evaluate test.jsonl test-predictions.jsonl
```
Model downloads require internet. Training requires your own annotated data; GPU recommended. PDF extraction needs text PDFs; scanned filings require external OCR. Inspect layout/order and split pages into paragraphs before annotation/training. Overlength records are rejected instead of silently truncated. Inference runs on CPU by default. Dependencies are bounded, not a reproducible lockfile; record the installed versions and model revision for published experiments.

## Annotation contract
Each JSONL record contains `id`, `source_document`, `text`, `entities`. Entities have `start`, `end` (end exclusive Python Unicode character offsets) and `label`: `COVENANT`, `FX_SENSITIVITY`, or `AUDIT_NOTE`. Text must remain identical after annotation. Use empty entity arrays for negatives. Flat, nonoverlapping spans only. Training requires spans aligned with tokenizer boundaries. Preserve source document and page metadata for review.

Annotate complete disclosure clauses using a written boundary policy; have a second annotator adjudicate disagreements. Split by issuer and reporting period AND document, keeping related filings out of different splits. The trainer rejects shared source documents, IDs and exact texts; issuer/near-duplicate checks remain the dataset curator's responsibility. Freeze a held-out test set before model selection. Report micro exact-match entity F1, per-class results, corpus size, source mix, model version and confidence intervals. The CLI reports overall exact-match metrics, including false positives/negatives; it does not substitute token accuracy for entity F1.

## Scope and limitations
Rule extraction can miss paraphrases and mishandle abbreviations or decimal punctuation. Transformer inference quality depends on annotations and training. No automated investment decisions or factual inference from absent text. Review extracted spans against the filing; preserve provenance and document licensing.

Implementation reference: [Hugging Face token classification](https://huggingface.co/docs/transformers/tasks/token_classification) and [Trainer documentation](https://huggingface.co/docs/transformers/main_classes/trainer).

## Prepare human labels

Follow [the annotation workflow](ANNOTATION.md) to export review worksheets, verify exact span offsets and import reviewed labels. Evaluation reports overall and per-category metrics.
