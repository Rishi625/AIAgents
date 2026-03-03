# Sample Complex Repo (Intentional Bugs)

This folder is a larger demo target for the agentic fixer.

It includes multiple modules:
- pricing logic
- shipping thresholds
- tax computation and checkout composition

## Run Tests

```bash
python -m pytest -q
```

## Intentional Bug Areas

- `app/pricing.py`: coupon percentage parsed incorrectly.
- `app/shipping.py`: threshold comparison edge case.
- `app/checkout.py`: tax scaling bug.
