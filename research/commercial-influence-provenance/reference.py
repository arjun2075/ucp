"""Reference invariants for experimental commercial-influence provenance."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


CAPABILITY = "io.github.arjun2075.shopping.commercial_influence"
STAGES = ("catalog", "offer", "cart", "checkout")
STATEMENT_FIELDS = ("id", "actor", "asserter", "kind", "effect", "basis")


class ProvenanceError(ValueError):
    """Base validation error."""


class IntegrityError(ProvenanceError):
    """Content or chain binding does not verify."""


class ProjectionError(ProvenanceError):
    """A state transition violates projection semantics."""


class ReplayConflict(ProvenanceError):
    """A transition identifier was reused with different inputs."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def validate_statement(statement: dict[str, Any]) -> None:
    missing = [field for field in STATEMENT_FIELDS if field not in statement]
    if missing:
        raise ProvenanceError(f"missing statement fields: {', '.join(missing)}")
    if set(statement) - set(STATEMENT_FIELDS) - {"sponsor"}:
        raise ProvenanceError("unknown statement field")
    for field in ("actor", "asserter"):
        party = statement[field]
        if not isinstance(party, dict) or set(party) != {"id"} or not party["id"]:
            raise ProvenanceError(f"{field} must contain exactly one non-empty id")
    if "sponsor" in statement:
        sponsor = statement["sponsor"]
        if not isinstance(sponsor, dict) or set(sponsor) != {"id"} or not sponsor["id"]:
            raise ProvenanceError("sponsor must contain exactly one non-empty id")


def statement_digest(statement: dict[str, Any]) -> str:
    validate_statement(statement)
    return digest(statement)


def make_binding(
    statement: dict[str, Any],
    stage: str,
    subject_ref: str,
    predecessor_binding_digest: str | None,
) -> dict[str, Any]:
    if stage not in STAGES:
        raise ProjectionError(f"unsupported stage: {stage}")
    if not subject_ref:
        raise ProjectionError("subject_ref must be non-empty")
    sd = statement_digest(statement)
    material = {
        "stage": stage,
        "subject_ref": subject_ref,
        "statement_digest": sd,
        "predecessor_binding_digest": predecessor_binding_digest,
    }
    return {**material, "binding_digest": digest(material)}


def verify_trace(trace: dict[str, Any]) -> None:
    if trace.get("capability") != CAPABILITY:
        raise ProvenanceError("unexpected capability identifier")
    statement = trace.get("statement")
    bindings = trace.get("bindings")
    if not isinstance(statement, dict) or not isinstance(bindings, list) or not bindings:
        raise ProvenanceError("trace requires a statement and non-empty bindings")

    expected_statement_digest = statement_digest(statement)
    predecessor = None
    previous_stage_index = -1
    for binding in bindings:
        stage = binding.get("stage")
        if stage not in STAGES:
            raise ProjectionError(f"unsupported stage: {stage}")
        stage_index = STAGES.index(stage)
        if stage_index <= previous_stage_index:
            raise ProjectionError("stages must be strictly increasing")
        if binding.get("statement_digest") != expected_statement_digest:
            raise IntegrityError("statement digest mismatch")
        if binding.get("predecessor_binding_digest") != predecessor:
            raise IntegrityError("stale or missing predecessor binding")
        material = {
            "stage": stage,
            "subject_ref": binding.get("subject_ref"),
            "statement_digest": binding.get("statement_digest"),
            "predecessor_binding_digest": predecessor,
        }
        if binding.get("binding_digest") != digest(material):
            raise IntegrityError("binding digest mismatch")
        predecessor = binding["binding_digest"]
        previous_stage_index = stage_index


def append_projection(
    trace: dict[str, Any], stage: str, subject_ref: str, effect_survives: bool = True
) -> dict[str, Any]:
    verify_trace(trace)
    result = copy.deepcopy(trace)
    if effect_survives and not result["bindings"]:
        raise ProjectionError("surviving effect requires provenance")
    predecessor = result["bindings"][-1]["binding_digest"]
    if STAGES.index(stage) <= STAGES.index(result["bindings"][-1]["stage"]):
        raise ProjectionError("projection cannot move backward or repeat a stage")
    result["bindings"].append(
        make_binding(result["statement"], stage, subject_ref, predecessor)
    )
    return result


def classify_disclosure(payload: dict[str, Any]) -> str:
    """Distinguish explicit none from absent or incomplete disclosure."""
    if not payload.get("negotiated"):
        return "unknown"
    if not payload.get("complete"):
        return "unknown"
    interventions = payload.get("interventions")
    if interventions == []:
        return "none_asserted"
    if isinstance(interventions, list) and interventions:
        return "assertions_present"
    raise ProvenanceError("complete disclosure requires an interventions array")


class StoredProjection:
    def __init__(self, input_digest: str, output: dict[str, Any]) -> None:
        self.input_digest = input_digest
        self.output = output


class ProjectionStore:
    """Tiny deterministic replay store for lost-response and conflict tests."""

    def __init__(self) -> None:
        self._records: dict[str, StoredProjection] = {}

    def project(
        self, transition_id: str, trace: dict[str, Any], stage: str, subject_ref: str
    ) -> dict[str, Any]:
        material = {
            "trace": trace,
            "stage": stage,
            "subject_ref": subject_ref,
        }
        input_digest = digest(material)
        prior = self._records.get(transition_id)
        if prior:
            if prior.input_digest != input_digest:
                raise ReplayConflict("transition id reused with different input")
            return copy.deepcopy(prior.output)
        output = append_projection(trace, stage, subject_ref)
        self._records[transition_id] = StoredProjection(input_digest, copy.deepcopy(output))
        return output

