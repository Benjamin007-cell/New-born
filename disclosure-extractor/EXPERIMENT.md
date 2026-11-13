# Experimental disclosure extractor

A DistilBERT token classifier fine-tuned for eight epochs on 22 Microsoft 2024 filing excerpts with nine AI-annotated entity spans. Training validation used 23 Dangote 2024 excerpts. A final provisional evaluation used those excerpts plus two Dangote FX table rows: 25 records and five entity spans.

## Result

Exact-span validation precision, recall and F1 were all **0.0**. The model emitted no entities and missed all five provisional entities. This checkpoint is not ready for reliable financial disclosure extraction. The proposed 88.4% entity F1 has not been achieved.

The software pipeline completed training, saving, reloading, inference and evaluation. That is an engineering result, not a successful extraction model.

## Annotation and evaluation limits

Labels were produced with AI-assisted review, not independent human annotation. Generic currency-risk text, accounting-standard descriptions, directors' routine going-concern statements and table-of-contents entries were treated as negatives. The corpus is tiny, keyword-selected and imbalanced. Clauses and table rows have different structures. Some financial-covenant material comes from debt-related exhibits inside the downloaded Microsoft filing package. FX table rows preserve extracted text and carry separate column-context metadata. Entity judgments are provisional and may need correction.

There is no independent test set or confidence interval. The issuers are disjoint between training and validation; this does not make the small validation result a generalizable benchmark. Do not use this checkpoint for investment decisions, covenant compliance or unattended document processing.

## Load the model

From the disclosure-extractor project, after installing requirements:

```sh
python -m disclosure extract input.jsonl predictions.jsonl --model /absolute/path/to/experimental-extractor/model
```

The separately supplied model bundle contains safetensors weights, tokenizer, source hashes, AI annotations, prediction files, evaluation report and runtime versions. Large weights and filing excerpts are excluded from the public GitHub repository. Use the code's rule baseline for the demonstration; it is separate from this unsuccessful experimental checkpoint.

## Provenance and license

Base model: https://huggingface.co/distilbert/distilbert-base-uncased (Apache-2.0). The fine-tuning modified token-classification weights on 2026-11-13. Retain APACHE-2.0.txt and NOTICE.txt with the model. Source filing rights are separate from the code and model license.
