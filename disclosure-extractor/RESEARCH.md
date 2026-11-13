# Expanded weak-label research workflow

This workflow tests whether class balancing and a larger corpus improve the initial all-negative experimental model. It does not create an independently annotated benchmark.

## Data and splits

The research corpus uses six issuers' 2024 filings. Microsoft, Dangote Cement, Apple and GTCO supply training records. Unilever supplies validation records. MTN Nigeria supplies a separate test set. Source hashes and split hashes are recorded before the final training run.

All labels are deterministic weak labels. They identify complete extracted sentences containing targeted patterns. Neither label correctness nor the exclusion of real disclosures from negative examples has independent human verification. PDF extraction can concatenate tables and headings. Shared templates and related wording can remain even after exact normalized duplicate removal. This is a restricted sentence-span task, not a representative benchmark of unrestricted clause extraction from complete filings.

The training sample balances positive and negative records. The validation and test samples preserve their sampled class ratios. Keyword-based positive sampling and per-class caps change prevalence; reported precision is conditional on this selection and cannot be assumed for whole annual reports.

## Reproduce

Install the optional requirements. Supply a local JSON source manifest containing objects with `document`, `issuer`, `path`, `split`, and `url`. Each issuer must belong to one split only.

```sh
python -m disclosure.silver sources.json corpus
python -m disclosure.research train corpus model-run --base distilbert/distilbert-base-uncased --epochs 12
python -m disclosure.research test corpus model-run final-test.json
```

For exact repetition of the recorded experiment, use its separately delivered frozen corpus files. That corpus includes a training-only labeling-rule correction applied to the preselected sentences before freezing, so a fresh sampling run can select different records. The downloaded pretrained checkpoint used for the recorded run was saved locally before fine-tuning; its initialization is not claimed to be bit-for-bit reproducible by a fresh remote download.

## Training and selection

Inverse-square-root token-class weights address outside-label dominance and rare entity tags. The model is trained for 12 epochs with learning rate 5e-5, warmup ratio 0.1, weight decay 0.01 and seed 42. Validation exact-character-span F1 selects the saved checkpoint. The test labels and text are not loaded during training or checkpoint selection. The test routine verifies frozen file hashes and refuses to overwrite an existing test result.

BIO decoding preserves predicted character boundaries. Invalid initial I-tags start a new entity; same-class I-tags extend the active entity. No whole-sentence expansion, overlap credit or token-accuracy substitution is used to inflate exact-span F1.

## Interpretation

The reported test result measures agreement with heuristic labels on one held-out issuer. It is not independently validated financial extraction accuracy. A credible broader claim requires an independently reviewed corpus with adjudicated boundaries, more issuers and periods, multiple test issuers, and uncertainty estimates that account for issuer clustering. The 88.4% target is not an achieved result unless appropriate evidence establishes it.
