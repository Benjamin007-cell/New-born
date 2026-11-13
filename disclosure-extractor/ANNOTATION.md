# Build the labeled corpus

No real filings or labels are supplied yet. Do not train or publish a benchmark using the demo data.

## Collect and prepare

Use annual reports from issuer/investor-relations pages and SEC filings. Save the original URL, issuer, period, filing type, page number and download date. Check reuse terms. Extract text with `python -m disclosure pdf report.pdf pages.jsonl`, inspect reading order, and split long pages into paragraph records before annotation. Every paragraph needs a unique `id` and a stable `source_document` identifying the full original filing. Retain metadata in each record.

## Create the review worksheet

```sh
python -m disclosure.labeling export paragraphs.jsonl labels.csv
```

Open the CSV in a text editor or spreadsheet. Preserve IDs, source_document and text exactly. Edit `entities_json`; mark `reviewed` as `yes` only after inspecting the complete paragraph against the original filing. Empty arrays `[]` mean a reviewed negative, not an unreviewed example. Automatically suggested labels require human correction.

Each span needs `start`, `end`, `label`, and `text`. Offsets count Python Unicode characters; `end` is exclusive. Example for `Debt covenant.`:

```json
[{"start":0,"end":13,"label":"COVENANT","text":"Debt covenant"}]
```

The importer verifies the quoted span against the original text and rejects changed text, missing records, overlaps and unreviewed records.

```sh
python -m disclosure.labeling import paragraphs.jsonl labels.csv reviewed.jsonl
```

## Boundary policy

- COVENANT: annotate the complete clause stating a financing restriction, ratio requirement, breach, waiver or compliance status. Exclude unrelated business descriptions. Include the threshold, units and conditions where stated.
- FX_SENSITIVITY: annotate the complete clause tying an exchange-rate change to a quantified financial effect, including shock magnitude, currency, effect and direction. General references to currency risk alone are negatives for this gold label, even though the loose rule baseline may flag them.
- AUDIT_NOTE: annotate the complete clause stating an audit opinion, qualification, key audit matter, or material going-concern audit disclosure. Routine auditor appointment or fee disclosures are negatives.
- Include final punctuation when it belongs to the clause; exclude leading/trailing whitespace and section headings. For a multi-sentence disclosure, annotate each relevant complete clause separately.
- This flat schema does not support overlapping or nested entities. Send ambiguous overlaps for adjudication; do not silently choose a category.

Have two reviewers independently annotate a pilot batch and adjudicate disagreements before scaling. Keep the annotation policy version and adjudication decisions. Confirm that boundaries align with the selected model tokenizer before training; the trainer rejects incompatible boundaries.

## Split and evaluate

Create train, validation and test JSONL files from reviewed records. Keep all paragraphs from an issuer and its related reporting periods in one split to reduce leakage. Keep all categories and negatives represented; document any classes absent from a split. Never optimize rules or training choices against the frozen test split.

The existing trainer rejects repeated source documents, IDs and exact texts across train/validation. It cannot detect all related issuers or near-duplicates, so review the manifest manually. Reserve test data separately.

Evaluation now reports exact character-span precision, recall, F1 and counts overall and for each class. A class with no gold entities reports zero F1 and zero gold count; treat this as insufficient evidence, not a measured class failure. Report corpus counts and held-out results alongside any headline F1. The claimed 88.4% is unverified until a real experiment supports it.
