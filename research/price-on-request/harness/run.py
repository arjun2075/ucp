#!/usr/bin/env python3
"""Price-on-request prototype: validation + compatibility harness.

Runs every leg of the compatibility matrix with real validators:

  Leg A  existing priced payloads vs BASELINE schema   -> must all pass
  Leg B  existing priced payloads vs PROPOSED schema   -> must all pass (no regression)
  Leg C  new on-request payloads vs BASELINE schema    -> must fail (the gap is real)
  Leg D  new on-request payloads vs PROPOSED schema    -> must pass
  Leg E  differential fuzz: N random priced variants/products vs both schemas
         -> verdicts must agree (proposed changes nothing for priced payloads)
  Leg F  old python SDK (ucp-sdk pinned version)      -> priced accepted,
         on-request rejected fail-closed ('price' Field required)

Runnable from any cwd; schema roots and the SDK checkout are configurable:

    python3 harness/run.py [--baseline PATH] [--proposed PATH] [--sdk PATH]
                           [--fuzz N] [--skip-sdk]

Exit code: 0 iff every non-skipped leg passes, else 1.
Requires: jsonschema 4.10.3 (pinned in requirements.txt). The SDK leg
additionally requires pydantic (any 2.x).
"""

import argparse
import json
import pathlib
import random
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_BASELINE = pathlib.Path.home() / "workspace/ucp-phase1-repos/ucp"
DEFAULT_PROPOSED = (
    pathlib.Path.home() / "workspace/ucp-price-on-request-contribution-phase5/scratch-ucp"
)
DEFAULT_SDK = pathlib.Path.home() / "workspace/ucp-phase1-repos/python-sdk"

VARIANT_URL = "https://ucp.dev/schemas/shopping/types/variant.json"
PRODUCT_URL = "https://ucp.dev/schemas/shopping/types/product.json"


# --------------------------------------------------------------------------
# schema loading (jsonschema 4.10.3 RefResolver + $id store)
# --------------------------------------------------------------------------
def load_store(schema_root):
    store = {}
    for p in pathlib.Path(schema_root, "source/schemas").rglob("*.json"):
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(doc, dict) and "$id" in doc:
            store[doc["$id"]] = doc
    if VARIANT_URL not in store or PRODUCT_URL not in store:
        raise SystemExit(f"schema root {schema_root} does not look like the ucp repo")
    return store


def make_validator(url, store):
    from jsonschema import Draft202012Validator, RefResolver

    resolver = RefResolver(base_uri=url, referrer=store[url], store=store)
    return Draft202012Validator({"$ref": url}, resolver=resolver)


def is_valid(validator, instance):
    return not list(validator.iter_errors(instance))


def first_error(validator, instance):
    errs = list(validator.iter_errors(instance))
    return errs[0].message if errs else ""


# --------------------------------------------------------------------------
# legs
# --------------------------------------------------------------------------
def leg_vectors(name, base_store, prop_store):
    """Legs A-D: fixture matrix from vectors.json."""
    from jsonschema import Draft202012Validator  # noqa  (version pin check below)

    vectors = json.loads((HERE / "vectors.json").read_text())["vectors"]
    bv = make_validator(VARIANT_URL, base_store)
    bp = make_validator(PRODUCT_URL, base_store)
    pv = make_validator(VARIANT_URL, prop_store)
    pp = make_validator(PRODUCT_URL, prop_store)
    passed = failed = 0
    for v in vectors:
        inst = json.loads((HERE / "fixtures" / v["file"]).read_text())
        bv_v, pv_v = (bv, pv) if v["kind"] == "variant" else (bp, pp)
        got_b = "valid" if is_valid(bv_v, inst) else "invalid"
        got_p = "valid" if is_valid(pv_v, inst) else "invalid"
        ok = got_b == v["baseline"] and got_p == v["proposed"]
        if ok:
            passed += 1
        else:
            failed += 1
        print(
            f"  [{'PASS' if ok else 'FAIL'}] {v['file']}: "
            f"baseline={got_b} (want {v['baseline']}), "
            f"proposed={got_p} (want {v['proposed']})"
        )
        if not ok:
            if got_b != v["baseline"]:
                print(f"         baseline error: {first_error(bv_v, inst)[:160]}")
            if got_p != v["proposed"]:
                print(f"         proposed error: {first_error(pv_v, inst)[:160]}")
    print(f"{name}: {passed} passed, {failed} failed")
    return failed == 0


def random_priced_variant(rng):
    v = {
        "id": f"var_{rng.randint(1, 10**9)}",
        "title": rng.choice(["Tee", "Mug", "Lamp", "Chair"]),
        "description": {"plain": "fuzz"},
        "price": {
            "amount": rng.choice([0, 1, 99, 2500, 12000, 10**9]),
            "currency": rng.choice(["USD", "EUR", "JPY"]),
        },
    }
    if rng.random() < 0.5:
        v["sku"] = f"SKU-{rng.randint(1, 9999)}"
    if rng.random() < 0.3:
        v["list_price"] = {"amount": v["price"]["amount"] + 100, "currency": v["price"]["currency"]}
    if rng.random() < 0.3:
        v["availability"] = {"available": True}
    return v


def leg_fuzz(n, base_store, prop_store):
    """Leg E: priced payloads must validate identically under both schemas."""
    bv = make_validator(VARIANT_URL, base_store)
    bp = make_validator(PRODUCT_URL, base_store)
    pv = make_validator(VARIANT_URL, prop_store)
    pp = make_validator(PRODUCT_URL, prop_store)
    rng = random.Random(20261001)
    mismatches = 0
    for i in range(n):
        variants = [random_priced_variant(rng) for _ in range(rng.randint(1, 4))]
        amounts = [v["price"]["amount"] for v in variants]
        cur = variants[0]["price"]["currency"]
        product = {
            "id": f"prod_{i}",
            "title": "Fuzz",
            "description": {"plain": "fuzz"},
            "price_range": {
                "min": {"amount": min(amounts), "currency": cur},
                "max": {"amount": max(amounts), "currency": cur},
            },
            "variants": variants,
        }
        for inst, bval, pval, label in (
            (variants[0], bv, pv, f"variant#{i}"),
            (product, bp, pp, f"product#{i}"),
        ):
            gb, gp = is_valid(bval, inst), is_valid(pval, inst)
            if not (gb and gp):
                mismatches += 1
                print(f"  [FAIL] {label}: baseline={gb} proposed={gp}")
                if not gb:
                    print(f"         baseline error: {first_error(bval, inst)[:160]}")
                if not gp:
                    print(f"         proposed error: {first_error(pval, inst)[:160]}")
    print(f"Leg E (differential fuzz, {n} products + {n} variants): {mismatches} mismatches")
    return mismatches == 0


def leg_sdk(sdk_path):
    """Leg F: old python SDK behavior on old vs new payloads."""
    src = pathlib.Path(sdk_path) / "src"
    if not (src / "ucp_sdk").is_dir():
        print("Leg F (SDK): SKIP — no ucp_sdk package at", src)
        return None
    sys.path.insert(0, str(src))
    try:
        from ucp_sdk.models.schemas.shopping.types.variant import Variant
        from pydantic import ValidationError
    except Exception as e:  # pragma: no cover
        print(f"Leg F (SDK): SKIP — import failed: {e}")
        return None

    ok = True

    def check(label, payload, want):
        nonlocal ok
        try:
            Variant.model_validate(payload)
            got = "accepted"
        except ValidationError as e:
            got = "rejected"
            detail = "; ".join(
                f"{'.'.join(map(str, er['loc']))}: {er['msg']}" for er in e.errors()[:2]
            )
        good = got == want
        ok = ok and good
        print(f"  [{'PASS' if good else 'FAIL'}] SDK {label}: {got} (want {want})"
              + ("" if good or got == "accepted" else f" [{detail}]"))
        return got

    priced = json.loads((HERE / "fixtures/priced_variant_basic.json").read_text())
    onreq = json.loads((HERE / "fixtures/onrequest_variant_quote_required.json").read_text())
    priced_marked = dict(priced, pricing={"mode": "public"})
    check("priced payload", priced, "accepted")
    check("on-request payload (new)", onreq, "rejected")
    check("priced payload + pricing marker (new client shape)", priced_marked, "accepted")
    print(f"Leg F (SDK): {'passed' if ok else 'FAILED'}")
    return ok


def versions(baseline, proposed, sdk):
    import importlib.metadata as md

    print("--- versions ---")
    for pkg in ("jsonschema", "pydantic"):
        try:
            print(f"  {pkg}: {md.version(pkg)}")
        except Exception:
            print(f"  {pkg}: not installed")
    for label, path in (("baseline", baseline), ("proposed", proposed), ("sdk", sdk)):
        try:
            sha = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True
            ).stdout.strip()
        except Exception:
            sha = "n/a"
        print(f"  {label} repo: {path} @ {sha}")
    try:
        txt = (pathlib.Path(sdk) / "pyproject.toml").read_text()
        import re

        m = re.search(r'^version\s*=\s*"([^"]+)"', txt, re.M)
        print(f"  ucp-sdk version: {m.group(1) if m else 'unknown'}")
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    ap.add_argument("--proposed", default=str(DEFAULT_PROPOSED))
    ap.add_argument("--sdk", default=str(DEFAULT_SDK))
    ap.add_argument("--fuzz", type=int, default=300)
    ap.add_argument("--skip-sdk", action="store_true")
    args = ap.parse_args()

    print("== price-on-request prototype harness ==")
    versions(args.baseline, args.proposed, args.sdk)

    print("--- Legs A-D: fixture matrix (baseline vs proposed) ---")
    base_store = load_store(args.baseline)
    prop_store = load_store(args.proposed)
    ok_vectors = leg_vectors("Legs A-D", base_store, prop_store)

    print(f"--- Leg E: differential fuzz (n={args.fuzz}) ---")
    ok_fuzz = leg_fuzz(args.fuzz, base_store, prop_store)

    ok_sdk = True
    if not args.skip_sdk:
        print("--- Leg F: old python SDK ---")
        r = leg_sdk(args.sdk)
        ok_sdk = r if r is not None else True
        if r is None:
            print("(SDK leg skipped)")

    all_ok = ok_vectors and ok_fuzz and ok_sdk
    print("== RESULT:", "ALL LEGS PASS" if all_ok else "FAILURES PRESENT", "==")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
