import json
import re
from pathlib import Path
TYPES = {'COVENANT', 'FX_SENSITIVITY', 'AUDIT_NOTE'}

def read_records(path):
    records = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    ids = set()
    for r in records:
        if not isinstance(r.get('id'), str) or not r['id'] or r['id'] in ids:
            raise ValueError('IDs must be unique nonempty strings')
        ids.add(r['id'])
        if not isinstance(r.get('text'), str) or not isinstance(r.get('entities'), list):
            raise ValueError('Each record needs text and entities')
        end = 0
        for e in sorted(r['entities'], key=lambda x: x['start']):
            if type(e['start']) is not int or type(e['end']) is not int or e['label'] not in TYPES or not (end <= e['start'] < e['end'] <= len(r['text'])):
                raise ValueError('Invalid or overlapping entity span')
            end = e['end']
    return records

def baseline(text):
    """Transparent sentence-level rules, not a trained transformer."""
    rules = [('COVENANT', r'\b(covenant|debt.service.coverage|leverage ratio)\b'),
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
    Path(path).write_text(''.join(json.dumps(r) + '\n' for r in records))
