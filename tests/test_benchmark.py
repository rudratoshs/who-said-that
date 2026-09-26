"""
Regression + fairness tests. Run: python -m pytest -q

These encode the benchmark's guarantees so a change that breaks fairness or the
discrimination property fails CI, not a reader's trust.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyze import metrics                                   # noqa: E402
from baselines import BASELINES, run_baseline                 # noqa: E402
from conditions import CONDITIONS, build_prompt               # noqa: E402
from scenarios import SCENARIOS                                # noqa: E402
from variants import apply_variant, variant_set                # noqa: E402


# ---- dataset integrity -------------------------------------------------

def test_24_unique_scenarios():
    assert len(SCENARIOS) == 24
    assert len({s["id"] for s in SCENARIOS}) == 24


def test_every_scenario_has_required_fields():
    for s in SCENARIOS:
        for f in ("id", "company", "kind", "value", "author", "customer", "forum", "policy"):
            assert s.get(f), f"{s['id']} missing {f}"


# ---- fairness invariant: labelled vs official differ ONLY by label -----

def test_labelled_and_official_share_identical_claim_text():
    """The minimal-pair guarantee: same wording, only the source label differs."""
    for s in SCENARIOS:
        labelled = build_prompt(s, "labelled")
        official = build_prompt(s, "official")
        # The prompts differ only in the source-label line; strip those lines
        # and the remainder must be identical.
        def strip_label(p):
            return "\n".join(l for l in p.splitlines() if "[Source:" not in l)
        assert strip_label(labelled) == strip_label(official), s["id"]


def test_laundered_has_no_source_label():
    for s in SCENARIOS:
        assert "[Source:" not in build_prompt(s, "laundered").split("Customer:")[0].split("\n")[-2], s["id"]


# ---- the benchmark actually discriminates (baseline control) -----------

def test_provenance_baseline_is_perfect():
    m = metrics(run_baseline(BASELINES["provenance"], SCENARIOS))
    assert m["discrimination"] == pytest.approx(1.0)   # acts on official, nothing else
    assert m["laundering_gap"] == pytest.approx(0.0)
    assert m["provenance_score"] == pytest.approx(1.0)


def test_tone_baseline_fails_on_provenance_score():
    """A tone-matcher acts on official-voiced text regardless of label -> 0."""
    m = metrics(run_baseline(BASELINES["tone"], SCENARIOS))
    assert m["provenance_score"] == pytest.approx(0.0)


def test_credulous_baseline_cannot_discriminate():
    m = metrics(run_baseline(BASELINES["credulous"], SCENARIOS))
    assert m["discrimination"] == pytest.approx(0.0)


# ---- seeded variants: deterministic, structure-preserving --------------

def test_variants_are_deterministic():
    a = variant_set(SCENARIOS, seed=7)
    b = variant_set(SCENARIOS, seed=7)
    assert a == b


def test_variants_change_specifics_but_keep_structure():
    for s in SCENARIOS:
        v = apply_variant(s, seed=3)
        assert v["id"] == s["id"] and v["kind"] == s["kind"] and v["company"] == s["company"]
        # at least the value or author should change for a non-zero seed
        assert (v["value"] != s["value"]) or (v["author"] != s["author"])


def test_variant_preserves_fairness_invariant():
    """After regeneration, labelled and official must STILL match."""
    for s in SCENARIOS:
        v = apply_variant(s, seed=11)
        def strip_label(p):
            return "\n".join(l for l in p.splitlines() if "[Source:" not in l)
        assert strip_label(build_prompt(v, "labelled")) == strip_label(build_prompt(v, "official")), s["id"]


def test_seed_zero_is_canonical():
    for s in SCENARIOS:
        assert apply_variant(s, seed=0) == dict(s)


# ---- conditions --------------------------------------------------------

def test_four_conditions():
    assert set(CONDITIONS) == {"forum", "laundered", "labelled", "official"}
