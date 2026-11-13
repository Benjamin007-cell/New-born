"""Fine-tune token classification; refuses truncation and leaking document groups."""
from . import LABELS
from .core import read_records

def encode_record(row, tokenizer):
    encoded = tokenizer(row['text'], return_offsets_mapping=True, truncation=False)
    limit = min(tokenizer.model_max_length, 512)
    if len(encoded['input_ids']) > limit:
        raise ValueError('Split record {} into shorter paragraphs; no silent truncation'.format(row['id']))
    labels = []
    offsets = encoded.pop('offset_mapping')
    entities = sorted(row['entities'], key=lambda e: e['start'])
    covered = set()
    for start, end in offsets:
        if start == end:
            labels.append(-100); continue
        overlapping = [(i,e) for i,e in enumerate(entities) if start < e['end'] and end > e['start']]
        if not overlapping:
            labels.append(0); continue
        i,e = overlapping[0]
        if len(overlapping) > 1 or start < e['start'] or end > e['end']:
            raise ValueError('Entity boundary must align with tokenizer offsets in {}'.format(row['id']))
        prefix = 'I-' if i in covered else 'B-'
        covered.add(i)
        labels.append(LABELS.index(prefix + e['label']))
    if len(covered) != len(entities):
        raise ValueError('An entity has no tokens in {}'.format(row['id']))
    encoded['labels'] = labels
    return encoded

def train(train_path, validation_path, output, base_model, epochs):
    import json
    from pathlib import Path
    from datasets import Dataset
    from transformers import AutoTokenizer, AutoModelForTokenClassification, DataCollatorForTokenClassification, Trainer, TrainingArguments, set_seed
    train_rows, val_rows = read_records(train_path), read_records(validation_path)
    if not train_rows or not val_rows or epochs <= 0:
        raise ValueError('Need nonempty train/validation sets and positive epochs')
    if any(r.get('annotation_status') != 'reviewed' for r in train_rows + val_rows):
        raise ValueError('Training requires reviewed annotations; import the completed worksheet first')
    # Paragraphs from the same source must remain in the same split.
    if any(not r.get('source_document') for r in train_rows + val_rows):
        raise ValueError('Training records require source_document to prevent document leakage')
    if {r['source_document'] for r in train_rows} & {r['source_document'] for r in val_rows}:
        raise ValueError('Document leakage across train and validation')
    if {r['id'] for r in train_rows} & {r['id'] for r in val_rows}:
        raise ValueError('Duplicate IDs across splits')
    if {r['text'] for r in train_rows} & {r['text'] for r in val_rows}:
        raise ValueError('Duplicate text across splits')
    set_seed(42)
    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    datasets = [Dataset.from_list([encode_record(r, tokenizer) for r in rows]) for rows in [train_rows, val_rows]]
    model = AutoModelForTokenClassification.from_pretrained(base_model, num_labels=len(LABELS), id2label=dict(enumerate(LABELS)), label2id={v:i for i,v in enumerate(LABELS)})
    args = TrainingArguments(output_dir=output, learning_rate=2e-5, per_device_train_batch_size=8, per_device_eval_batch_size=8, num_train_epochs=epochs, eval_strategy='epoch', save_strategy='epoch', seed=42, report_to='none')
    trainer = Trainer(model=model, args=args, train_dataset=datasets[0], eval_dataset=datasets[1], processing_class=tokenizer, data_collator=DataCollatorForTokenClassification(tokenizer))
    trainer.train(); trainer.save_model(output); tokenizer.save_pretrained(output)
    Path(output, 'run_metadata.json').write_text(json.dumps({'base_model':base_model, 'epochs':epochs, 'seed':42, 'train_documents':len({r['source_document'] for r in train_rows}), 'validation_documents':len({r['source_document'] for r in val_rows}), 'validation_loss':trainer.evaluate(), 'note':'Run extract and evaluate on held-out gold records for entity F1; loss is not F1.'}, indent=2))
