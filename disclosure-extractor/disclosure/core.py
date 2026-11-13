import json
import re
from pathlib import Path
TYPES = {'COVENANT', 'FX_SENSITIVITY', 'AUDIT_NOTE'}

def validate_records(records):
    ids = set()
    for r in records:
        if not isinstance(r, dict):
            raise ValueError('Each record must be an object')
        if not isinstance(r.get('id'), str) or not r['id'] or r['id'] in ids:
            raise ValueError('IDs must be unique nonempty strings')
        ids.add(r['id'])
        if not isinstance(r.get('text'), str) or not isinstance(r.get('entities'), list):
            raise ValueError('Each record needs text and entities')
        for e in r['entities']:
            if not isinstance(e, dict) or type(e.get('start')) is not int or type(e.get('end')) is not int:
                raise ValueError('Entities need integer start and end offsets')
            if not isinstance(e.get('label'), str) or e['label'] not in TYPES:
                raise ValueError('Unknown entity label')
            if not 0 <= e['start'] < e['end'] <= len(r['text']):
                raise ValueError('Invalid entity span')
            if 'text' in e and e['text'] != r['text'][e['start']:e['end']]:
                raise ValueError('Entity text does not match offsets')
        end = 0
        for e in sorted(r['entities'], key=lambda x: x['start']):
            if e['start'] < end:
                raise ValueError('Overlapping entity spans')
            end = e['end']
    return records


def read_records(path):
    records = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    return validate_records(records)


def baseline(text):
    """Transparent sentence-level rules, not a trained transformer."""
    rules = [('COVENANT', r'\b(covenants?|debt.service.coverage|leverage ratio)\b'),
             ('FX_SENSITIVITY', r'\b(exchange rate|foreign exchange|currency risk|fx sensitivity)\b'),
             ('AUDIT_NOTE', r'\b(auditor|audit opinion|going concern|key audit matter)\b')]
    out = []
    for match in re.finditer(r'[^.!?\n]+(?:[.!?]|$)', text):
        start = match.start() + len(match.group()) - len(match.group().lstrip())
        end = match.end() - (len(match.group()) - len(match.group().rstrip()))
        for label, pattern in rules:
            if re.search(pattern, match.group(), re.I):
                out.append({'start': start, 'end': end, 'label': label, 'text': text[start:end]})
                break  # flat schema: one label per sentence in baseline only
    return out

def metrics(gold, predicted):
    """Micro exact-match F1 on (document ID, character start, end, type)."""
    validate_records(gold)
    validate_records(predicted)
    if {r['id'] for r in gold} != {r['id'] for r in predicted}:
        raise ValueError('Gold and prediction document IDs must match')
    lookup = {r['id']: r['text'] for r in gold}
    if any(lookup[r['id']] != r['text'] for r in predicted):
        raise ValueError('Gold and prediction text must match exactly')
    def spans(rows):
        return {(r['id'], e['start'], e['end'], e['label']) for r in rows for e in r['entities']}
    g, p = spans(gold), spans(predicted)
    tp = len(g & p); precision = tp / len(p) if p else 0.0; recall = tp / len(g) if g else 0.0
    return {'precision': precision, 'recall': recall, 'f1': 2 * precision * recall / (precision + recall) if precision + recall else 0.0, 'true_positives': tp, 'false_positives': len(p-g), 'false_negatives': len(g-p), 'gold_entities': len(g)}

def write_jsonl(path, records):
    Path(path).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')


def evaluation_report(gold, predicted):
    report = {'overall': metrics(gold, predicted), 'per_class': {}}
    for label in sorted(TYPES):
        def filtered(rows):
            return [dict(r, entities=[e for e in r['entities'] if e['label'] == label]) for r in rows]
        report['per_class'][label] = metrics(filtered(gold), filtered(predicted))
    return report
