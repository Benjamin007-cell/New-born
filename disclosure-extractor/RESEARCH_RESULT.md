# Expanded disclosure extraction experiment

Completed a six-issuer weak-label study using a class-weighted DistilBERT token classifier. This is provisional research, not a verified 88.4% accuracy claim.

## Measured results

- Best validation exact-span F1: 50.60% on Unilever.
- Selected model test exact-span F1: 23.33%; precision 18.42%; recall 31.82%.
- Previous model on the SAME test sample: 0.00% F1.
- Test sample: 58 extracted sentences from MTN Nigeria, with 22 weak-labeled entities.
- Target: 88.4% entity F1. The target was NOT reached.

## Data and training

Training: 108 unique records, 54 positive and 54 negative, from Microsoft, Dangote Cement, Apple and GTCO 2024 filings. Positive labels comprise 31 audit notes, 14 covenant sentences and nine FX sensitivity sentences. Validation: 61 Unilever records. Test: 58 MTN Nigeria records. Exact normalized duplicates were removed across the corpus; near-duplicate templates can remain. Some training passages are debt-related exhibits in filing packages.

The labeling policy is heuristic and sentence-level. No independent human annotation or adjudication has been performed. Known generic accounting and currency-exposure false positives were corrected using training-only examples before the final splits were frozen. The model was trained for 12 epochs using inverse-square-root token-class weights, balanced training records, learning rate 5e-5, warmup 0.1, weight decay 0.01 and seed 42. Validation F1 selected the checkpoint. The MTN text and labels were not loaded during the final training/checkpoint-selection run. One final test evaluation was run for the selected model; a pre-existing model was evaluated separately on the same fixed test sample for comparison. No test-result-driven retraining was performed.

## Limits

This score measures agreement with rules on keyword-selected extracted sentences. It is not a gold-standard benchmark of unrestricted financial disclosure extraction. Whole-sentence weak labels, table concatenation, selection bias, small class counts and one test issuer limit generalization. The conditional record-bootstrap range in evaluation.json reflects only this sample and labeling policy. It cannot establish performance across issuers or uncertainty in annotation correctness.

The original 88.4% resume claim remains unsupported by independently reviewed evidence. Do not describe the machine-label score as human-validated accuracy. More independently annotated filings, multiple test issuers and adjudicated clause boundaries are still necessary for a credible broad performance claim.

## Use

The separate downloadable bundle contains final safetensors weights, tokenizer, frozen datasets, predictions, source hashes, class weights, training history and evaluation. Intermediate optimizer checkpoints are excluded. In the project directory, install requirements and run:

```sh
python -m disclosure extract input.jsonl predictions.jsonl --model /absolute/path/to/improved-extractor/model
```

Reproduce the exact test decoder with `python -m disclosure.research test corpus model-run test-result.json`. The test routine refuses to overwrite an existing report. The weak-label research entry point is separate from the reviewed-data training entry point.

Base model: https://huggingface.co/distilbert/distilbert-base-uncased (Apache-2.0). Fine-tuning modifies token-classification weights. Code is MIT; filings retain their respective rights. Model weights and excerpts are delivered separately from the public source repository.
