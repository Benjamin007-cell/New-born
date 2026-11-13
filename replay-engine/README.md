# Fixed-Income & Order-Book Replay Engine

Rust matching core with a Python replay/reporting interface. Research simulator; synthetic demonstration data. One book per instrument/run.

## Run
Requires Rust stable and Python 3.9+.

```sh
cargo test
cargo build --release
python3 python/replay.py data/events.csv --maker-bps -1 --taker-bps 2 --ticks 0:1,10000:5 --multiplier 0.01
python3 -m unittest discover -s tests
```

## Behavior
- Deterministic event order; timestamps must be nondecreasing, ties follow input order.
- Price-time priority, passive-order execution prices, partial fills and cancellation.
- Integer prices in caller-defined minor units; integer quantities. IDs are unique for an entire run.
- Inclusive piecewise tick schedule. Each price must be divisible by its applicable tick; lower bounds are not grid origins.
- Maker/taker fees in basis points, including negative rebates. Fees are floating point estimates in price units, rounded to eight decimals in CSV.
- For bonds quoted per 100 face, use multiplier 0.01 and quantity in face units. Coupon accrual, settlement, yield conversion and currency conversion are outside this version.
- Cancel/re-add with a NEW ID models replacement and loses queue priority. No market orders, auctions, hidden liquidity or self-trade prevention.
- Cancellation searches active orders linearly. This is an inspectable reference engine, not a latency benchmark. Depth totals saturate at u64::MAX.

## Data contract
Plain six-column CSV, no quoted commas. `timestamp,action,id,side,price,quantity`; action is `add` or `cancel`. Cancel ignores the last three fields. IDs allow ASCII alphanumerics, `_` and `-`. Prices/quantities/timestamps are unsigned integers. Invalid input stops replay with a line-numbered error; prior output is partial and must be discarded by batch consumers. Python wrapper suppresses partial results on failure.

Custom venues require their own validated ticks, fees and instrument conventions; supplied settings are examples, not official NGX rules. Sample trade quantities are 200, 50, 100, demonstrating FIFO and cancellation.
