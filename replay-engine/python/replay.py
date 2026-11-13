"""Run the Rust engine and summarize executions using exact decimal arithmetic."""
import argparse
import csv
from decimal import Decimal
import io
from pathlib import Path
import subprocess

def summarize(text):
    fills = list(csv.DictReader(io.StringIO(text)))
    qty = sum(int(f['quantity']) for f in fills)
    notional = sum((Decimal(f['price']) * int(f['quantity']) for f in fills), Decimal(0))
    fees = sum((Decimal(f['maker_fee']) + Decimal(f['taker_fee']) for f in fills), Decimal(0))
    return {'fills': len(fills), 'quantity': qty, 'vwap_minor_units': str(notional / qty) if qty else None, 'total_fees': str(fees)}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('events', type=Path)
    p.add_argument('--engine', type=Path, default=Path(__file__).resolve().parents[1] / 'target/release/replay-engine')
    p.add_argument('--maker-bps', default='0'); p.add_argument('--taker-bps', default='0')
    p.add_argument('--ticks', default='0:1'); p.add_argument('--multiplier', default='1')
    a = p.parse_args()
    with a.events.open() as source:
        result = subprocess.run([str(a.engine.resolve()), '--maker-bps', a.maker_bps, '--taker-bps', a.taker_bps, '--ticks', a.ticks, '--multiplier', a.multiplier], stdin=source, capture_output=True, text=True)
    if result.returncode:
        p.exit(result.returncode, result.stderr)
    print(result.stdout, end='')
    print(summarize(result.stdout))
