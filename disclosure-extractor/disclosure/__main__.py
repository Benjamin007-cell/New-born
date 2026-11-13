import argparse
import json
from pathlib import Path
from .core import baseline, metrics, read_records, write_jsonl

def main():
    p = argparse.ArgumentParser(description='Extract financial disclosure spans; evaluate exact character boundaries.')
    sub = p.add_subparsers(dest='command', required=True)
    for name in ['extract', 'evaluate', 'pdf', 'train']:
        cmd = sub.add_parser(name)
        if name == 'extract':
            cmd.add_argument('input'); cmd.add_argument('output'); cmd.add_argument('--model')
        elif name == 'evaluate':
            cmd.add_argument('gold'); cmd.add_argument('predictions')
        elif name == 'pdf':
            cmd.add_argument('input'); cmd.add_argument('output')
        else:
            cmd.add_argument('train'); cmd.add_argument('validation'); cmd.add_argument('output')
            cmd.add_argument('--base-model', default='distilbert/distilbert-base-uncased')
            cmd.add_argument('--epochs', type=int, default=3)
    a = p.parse_args()
    if a.command == 'evaluate':
        print(json.dumps(metrics(read_records(a.gold), read_records(a.predictions)), indent=2))
    elif a.command == 'pdf':
        from pypdf import PdfReader
        rows = [{'id': '{}:{}'.format(Path(a.input).stem, i+1), 'source_document': Path(a.input).name, 'page': i+1, 'text': page.extract_text() or '', 'entities': []} for i, page in enumerate(PdfReader(a.input).pages)]
        if not any(r['text'].strip() for r in rows):
            raise ValueError('No text extracted; scanned PDFs require OCR first')
        write_jsonl(a.output, rows)
    elif a.command == 'train':
        from .train import train
        train(a.train, a.validation, a.output, a.base_model, a.epochs)
    else:
        rows = read_records(a.input)
        if a.model:
            from transformers import pipeline
            extractor = pipeline('token-classification', model=a.model, tokenizer=a.model, aggregation_strategy='simple')
            for r in rows:
                # Fail explicitly instead of silently truncating reports.
                limit = extractor.tokenizer.model_max_length
                if len(extractor.tokenizer(r['text'])['input_ids']) > limit:
                    raise ValueError('Record too long; split into paragraphs before model inference')
                entities = extractor(r['text'])
                r['entities'] = [{'start': int(e['start']), 'end': int(e['end']), 'label': e['entity_group'], 'score': float(e['score']), 'text': r['text'][int(e['start']):int(e['end'])]} for e in entities]
        else:
            for r in rows: r['entities'] = baseline(r['text'])
        write_jsonl(a.output, rows)

if __name__ == '__main__':
    main()
