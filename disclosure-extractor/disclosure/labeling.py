"""Export annotation worksheets; import only explicitly reviewed records."""
import argparse
import csv
import json
from pathlib import Path
from .core import read_records, write_jsonl, TYPES

FIELDS = ['id', 'source_document', 'text', 'reviewed', 'entities_json']

def export_sheet(source, output):
    rows = read_records(source)
    if any(not r.get('source_document') for r in rows):
        raise ValueError('Every record needs source_document')
    with Path(output).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({'id':r['id'], 'source_document':r['source_document'], 'text':r['text'], 'reviewed':'no', 'entities_json':json.dumps(r['entities'], ensure_ascii=False)})

def import_sheet(source, worksheet, output):
    originals = read_records(source)
    by_id = {r['id']:r for r in originals}
    result = []
    seen = set()
    with Path(worksheet).open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['id'] not in by_id or row['id'] in seen:
                raise ValueError('Unknown or duplicate worksheet ID')
            seen.add(row['id'])
            original = by_id[row['id']]
            if row['text'] != original['text'] or row['source_document'] != original.get('source_document'):
                raise ValueError('Worksheet changed original text or provenance')
            if row['reviewed'].strip().lower() != 'yes':
                raise ValueError('Every record must be explicitly reviewed, including negatives')
            entities = json.loads(row['entities_json'])
            if not isinstance(entities, list):
                raise ValueError('entities_json must be a list')
            end = 0
            for e in sorted(entities, key=lambda e:e['start']):
                if type(e['start']) is not int or type(e['end']) is not int or e['label'] not in TYPES or not end <= e['start'] < e['end'] <= len(original['text']):
                    raise ValueError('Invalid or overlapping entity span')
                if 'text' not in e or original['text'][e['start']:e['end']] != e['text']:
                    raise ValueError('Each entity needs exact matching text to verify its offsets')
                end=e['end']
            result.append(dict(original, entities=entities))
    if seen != set(by_id):
        raise ValueError('Worksheet must include every source record')
    if Path(output).resolve() in {Path(source).resolve(), Path(worksheet).resolve()}:
        raise ValueError('Output must not overwrite source or worksheet')
    write_jsonl(output, result)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    e=sub.add_parser('export');e.add_argument('source');e.add_argument('worksheet')
    i=sub.add_parser('import');i.add_argument('source');i.add_argument('worksheet');i.add_argument('output')
    a=parser.parse_args()
    if a.action=='export': export_sheet(a.source,a.worksheet)
    else: import_sheet(a.source,a.worksheet,a.output)

if __name__=='__main__': main()
