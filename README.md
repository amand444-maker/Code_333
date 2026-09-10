# Code_333

`Code_333` now includes a self-contained Python supply-chain telemetry analysis demo with:

- temporal signal fusion
- weighted relationship scoring
- focus-node risk ranking
- upstream path tracing across an entity graph

## Run the demo

```bash
python3 palantir_engine.py
```

## Run the tests

```bash
python3 -m unittest discover -s . -p 'test_*.py'
```