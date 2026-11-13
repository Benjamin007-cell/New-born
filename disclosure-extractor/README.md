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

## Real filing preparation and browser review

```sh
python -m disclosure.prepare report.pdf candidates.jsonl --document issuer-2024 --issuer Issuer --url https://example.org/report.pdf
python -m disclosure.review candidates.jsonl review.html
```

Open the generated HTML locally. Review source context, select clauses, choose categories, remove false suggestions, and mark checked records reviewed. Save checkpoints before closing the page. Exported reviewed JSONL preserves source provenance. The worksheet counts Python Unicode characters even for non-BMP symbols; it does not use raw PDF offsets. Keyword-selected negatives and positives are candidates, not a representative test set. Candidate preparation supports PDF and DOCX (including table-cell paragraphs); extracted table fragments need manual context checks.

The trainer now requires `annotation_status: reviewed` in every train/validation record. Importing a completed CSV sets this field; the browser worksheet also sets it when the reviewer checks a record. This is a reviewer attestation, not independent proof of annotation quality.

A 43-record pilot from Dangote Cement's 2024 annual report and Microsoft's 2024 10-K has been prepared locally. [Source manifest and status](data/pilot-manifest.json) are public; report excerpts and worksheets are not included in this repository. There are no human-reviewed real-filing labels or real-filing model weights yet. Two issuers are insufficient for a three-way issuer-disjoint benchmark.

## Training integration check

```sh
PYTHONPATH=. python scripts/smoke_training.py /tmp/disclosure-smoke
```

Requires the optional training dependencies. Creates a tiny random BERT and synthetic fixtures locally without downloading model weights, then trains, saves, reloads and predicts. This passed locally with PyTorch 2.8.0 and Transformers 4.57.6. It verifies the pipeline only; no financial accuracy or useful pretrained model is implied. The generated model is a test artifact and should not be deployed. [Recorded result](data/training-smoke-result.json).

## Final validation safeguards

Records reject malformed entities, duplicate IDs, overlapping spans and entity text inconsistent with offsets. When issuer metadata is present, it must appear on every training/validation record and the issuer sets must be disjoint. Training refuses nonempty output directories so existing checkpoints cannot be silently replaced. Use a fresh directory for each training or synthetic integration run.
