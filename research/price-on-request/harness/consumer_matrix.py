#!/usr/bin/env python3
"""Consumer-behavior matrix for the price-on-request prototype (Worker C).

Four SEPARATED sections, all from real validators (no hand-waving):

  (a) old payload acceptance by NEW schemas
      rows: every fixture vectors.json marks baseline=="valid".
      Columns: fixture, proposed verdict, class (no-change / narrows).
  (b) new payload acceptance by OLD consumers
      rows: every fixture vectors.json marks proposed=="valid".
      Split: validating consumer (baseline jsonschema verdict + first error)
      vs lenient consumer (`.get("price", {}).get("amount", 0)` read, with the
      $0.00 misread demonstrated concretely).
  (c) generated SDK behavior (pydantic v2), per variant fixture:
      OLD side = pinned python-sdk models (ucp-sdk 0.4.6 @ 51bf73c,
      generated from the released schemas) accept/reject.
      NEW side = proposed-schema validation via jsonschema 4.10.3,
      clearly labeled: regenerating SDK models from the proposed schemas
      was NOT feasible here (datamodel_code_generator / uv / ruff are
      unavailable in this env), so there are no NEW-side generated models
      to run. Product fixtures are included where the SDK has a model.
  (d) lenient consumer behavior, per variant fixture:
      naive read `.get("price", {}).get("amount", 0)` -> displayed amount,
      plus the strict hand-rolled consumer `["price"]["amount"]` outcome
      (KeyError fail-loud) for contrast.

Emits Markdown tables to stdout. Exit code 0 iff the scripted assertions
hold; any violation prints FAIL and exits 1.

Read-only: never writes to either schema tree; the SDK is only imported.

    python3 harness/consumer_matrix.py [--baseline PATH] [--proposed PATH] [--sdk PATH]
"""

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as H  # noqa: E402  (reuses schema loading + validator helpers)

DEFAULT_BASELINE = pathlib.Path.home() / "workspace/ucp-phase1-repos/ucp"
DEFAULT_PROPOSED = pathlib.Path("/tmp/por-proposed")  # disposable /tmp copy w/ patch applied
DEFAULT_SDK = pathlib.Path.home() / "workspace/ucp-phase1-repos/python-sdk"


def load_sdk_models(sdk_path):
    src = pathlib.Path(sdk_path) / "src"
    sys.path.insert(0, str(src))
    try:
        from ucp_sdk.models.schemas.shopping.types.variant import Variant
        from ucp_sdk.models.schemas.shopping.types.product import Product
        from pydantic import ValidationError
    except Exception as e:  # pragma: no cover
        print(f"# SDK models unavailable: {e}", file=sys.stderr)
        return None, None
    return Variant, Product, ValidationError


def sdk_check(model, ValidationError, inst):
    try:
        model.model_validate(inst)
        return "accepted", ""
    except ValidationError as e:
        first = e.errors()[0]
        loc = ".".join(map(str, first["loc"]))
        return "rejected", f"{loc}: {first['msg']}"


def lenient_amount(inst):
    """The naive old-consumer read: variant.get("price", {}).get("amount", 0)."""
    price = inst.get("price", {})
    if not isinstance(price, dict):
        return "<non-object price>", "non-object"
    return price.get("amount", 0), "ok"


def hand_rolled(inst):
    """The strict hand-rolled consumer: variant["price"]["amount"]."""
    try:
        return str(inst["price"]["amount"]), "value"
    except KeyError as e:
        return f"KeyError({e})", "crash"
    except (TypeError, IndexError) as e:
        return f"{type(e).__name__}({e})", "crash"


def fmt_money(amount):
    if isinstance(amount, int):
        return f"${amount / 100:.2f}"
    return str(amount)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    ap.add_argument("--proposed", default=str(DEFAULT_PROPOSED))
    ap.add_argument("--sdk", default=str(DEFAULT_SDK))
    ap.add_argument("--quiet", action="store_true",
                    help="suppress per-assertion PASS lines; still prints FAILs and tables")
    args = ap.parse_args()

    import importlib.metadata as md

    print("# Consumer-behavior matrix — price-on-request prototype (Worker C, self-review)")
    print(f"# jsonschema {md.version('jsonschema')}, pydantic {md.version('pydantic')}")
    print(f"# baseline={args.baseline} proposed={args.proposed} sdk={args.sdk}")
    print()

    base_store = H.load_store(args.baseline)
    prop_store = H.load_store(args.proposed)
    bv, bp = H.make_validator(H.VARIANT_URL, base_store), H.make_validator(H.PRODUCT_URL, base_store)
    pv, pp = H.make_validator(H.VARIANT_URL, prop_store), H.make_validator(H.PRODUCT_URL, prop_store)

    sdk = load_sdk_models(args.sdk)
    Variant, Product, ValidationError = (sdk + (None,)) if sdk[0] is None else sdk
    have_sdk = Variant is not None

    vectors = json.loads((HERE / "vectors.json").read_text())["vectors"]
    rows = []
    for v in vectors:
        inst = json.loads((HERE / "fixtures" / v["file"]).read_text())
        is_var = v["kind"] == "variant"
        bval, pval = (bv, pv) if is_var else (bp, pp)
        gb = "valid" if H.is_valid(bval, inst) else "invalid"
        gp = "valid" if H.is_valid(pval, inst) else "invalid"
        berr = "" if gb == "valid" else H.first_error(bval, inst)[:120]
        rows.append({**v, "inst": inst, "is_var": is_var, "gb": gb, "gp": gp, "berr": berr})

    failures = []

    def check(cond, label):
        if args.quiet:
            if not cond:
                print(f"  [FAIL] {label}")
        else:
            print(f"  [{'PASS' if cond else 'FAIL'}] {label}")
        if not cond:
            failures.append(label)

    # ---- (a) old payload acceptance by NEW schemas ----
    print("## (a) old payload acceptance by NEW schemas")
    print()
    print("| fixture | baseline | proposed | class |")
    print("|---|---|---|---|")
    for r in rows:
        if r["baseline"] != "valid":
            continue
        cls = "no change" if r["gp"] == "valid" else "**narrows**"
        print(f"| `{r['file']}` | valid | {r['gp']} | {cls} |")
        check(r["gp"] == r["proposed"],
              f"(a) {r['file']}: proposed={r['gp']} matches vectors.json")
    print()

    # ---- (b) new payload acceptance by OLD consumers ----
    print("## (b) new payload acceptance by OLD consumers")
    print()
    print("Validating consumer = baseline jsonschema. Lenient consumer = "
          "`variant.get(\"price\", {}).get(\"amount\", 0)`; product fixtures show the "
          "first variant's read.")
    print()
    print("| fixture (proposed-valid) | old validating consumer | old lenient read |")
    print("|---|---|---|")
    for r in rows:
        if r["proposed"] != "valid":
            continue
        inst = r["inst"]
        probe = inst if r["is_var"] else (inst.get("variants") or [{}])[0]
        amount, _ = lenient_amount(probe)
        money = fmt_money(amount)
        misread = " **<-- $0.00 MISREAD as FREE**" if amount == 0 and "price" not in probe else ""
        print(f"| `{r['file']}` | {r['gb']}"
              + (f" (`{r['berr']}`)" if r["gb"] == "invalid" else "")
              + f" | {money}{misread} |")
        check(r["gb"] == r["baseline"],
              f"(b) {r['file']}: baseline={r['gb']} matches vectors.json")
    print()

    # ---- (c) generated SDK behavior ----
    print("## (c) generated SDK behavior (pydantic v2)")
    print()
    print("OLD side: pinned `ucp-sdk` 0.4.6 models (generated from the RELEASED "
          "schemas; `price` required, `pricing` unknown so `extra=\"allow\"` keeps "
          "it unvalidated). NEW side: **proposed-schema validation via jsonschema "
          "4.10.3** — regenerating SDK models from the proposed schemas was not "
          "feasible in this env (`datamodel_code_generator`/`uv`/`ruff` "
          "unavailable), so no NEW-side generated models exist to run.")
    print()
    print("| fixture | OLD SDK (pydantic) | NEW side (jsonschema on proposed) | note |")
    print("|---|---|---|---|")
    for r in rows:
        if have_sdk:
            model = Variant if r["is_var"] else Product
            got, detail = sdk_check(model, ValidationError, r["inst"])
            note = detail[:100] if got == "rejected" else ""
        else:
            got, note = "SKIP", "SDK unavailable"
        print(f"| `{r['file']}` | {got} | {r['gp']} | {note} |")
    print()

    # ---- (d) lenient consumer behavior ----
    print("## (d) lenient consumer behavior (variant fixtures)")
    print()
    print("Naive read `variant.get(\"price\", {}).get(\"amount\", 0)` vs strict "
          "hand-rolled `variant[\"price\"][\"amount\"]`.")
    print()
    print("| fixture | naive amount read | interpretation | strict hand-rolled |")
    print("|---|---|---|---|")
    for r in rows:
        if not r["is_var"]:
            continue
        amount, status = lenient_amount(r["inst"])
        money = fmt_money(amount)
        strict, skind = hand_rolled(r["inst"])
        has_price = "price" in r["inst"]
        if not has_price and amount == 0:
            interp = "**$0.00 misread as FREE** (the #877 harm)"
        elif has_price:
            interp = "correct (price present)"
        else:
            interp = status
        check((not has_price and amount == 0) or (has_price and isinstance(amount, int)),
              f"(d) {r['file']}: naive read behaves as classified")
        print(f"| `{r['file']}` | {money} | {interp} | "
              + (f"`{strict}`" if skind == "value" else f"{strict} (fail-loud)") + " |")
    print()

    print(f"## RESULT: {'ALL ASSERTIONS PASS' if not failures else f'{len(failures)} FAILURES'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
