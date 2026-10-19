"""Validate every reference trace using the dependency-free reference model."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("reference", ROOT / "reference.py")
assert SPEC and SPEC.loader
reference = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reference)


def main() -> None:
    json.loads((ROOT / "schema" / "commercial_intervention_trace.schema.json").read_text())
    payload = json.loads((ROOT / "fixtures" / "reference_traces.json").read_text())
    traces = payload["traces"]
    if len(traces) != 4:
        raise SystemExit(f"expected 4 reference traces, found {len(traces)}")
    for trace in traces:
        reference.verify_trace(trace)
    print(f"validated {len(traces)} reference traces and parsed schema")


if __name__ == "__main__":
    main()

