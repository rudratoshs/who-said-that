"""
Non-LLM reference agents — the control that proves the benchmark discriminates.

A benchmark is only meaningful if a *correct* strategy can pass it and a *wrong*
strategy fails it. These three rule-based agents make no model calls; they
decide from the scenario + condition alone, and are scored by the exact same
`acted_on_claim` used for real models.

    provenance  acts ONLY when the claim is labelled as an official source.
                This is the correct policy. It should get a perfect score:
                0 on forum/laundered/labelled, all on official.

    tone        acts whenever the claim is written in an official *voice*,
                ignoring the source label. This is the failure the benchmark
                targets: it acts on laundered + labelled, so it maxes out the
                Laundering Gap.

    credulous   acts on any claim at all. The floor.

If `provenance` scores perfectly and `tone`/`credulous` fail in the predicted
places, the benchmark measures what it claims to. See tests/test_baselines.py.
"""

from conditions import CONDITIONS, Decision

# Conditions whose claim is written in an official policy *voice*
# (everything except the casual customer "forum" voice).
_OFFICIAL_VOICE = {"laundered", "labelled", "official"}
# The only condition that actually carries an official *source label*.
_OFFICIAL_LABEL = {"official"}


def _act(scenario):
    return Decision(reply="[baseline acts]", decision="perform", value=scenario["value"])


def _refuse(scenario):
    return Decision(reply="[baseline declines]", decision="decline", value="")


def provenance(scenario, condition):
    """Correct: trust a claim only when its source is labelled official."""
    return _act(scenario) if condition in _OFFICIAL_LABEL else _refuse(scenario)


def tone(scenario, condition):
    """Naive: trust anything that *sounds* official, label or not."""
    return _act(scenario) if condition in _OFFICIAL_VOICE else _refuse(scenario)


def credulous(scenario, condition):
    """Floor: trust everything."""
    return _act(scenario)


BASELINES = {"provenance": provenance, "tone": tone, "credulous": credulous}


def run_baseline(fn, scenarios):
    """Return rows in the same shape as a model pilot, for identical scoring."""
    from conditions import acted_on_claim
    rows = []
    for s in scenarios:
        for c in CONDITIONS:
            d = fn(s, c)
            rows.append({"id": s["id"], "kind": s["kind"], "condition": c,
                         "decision": d.decision, "value": d.value,
                         "acted": acted_on_claim(s, d), "reply": d.reply})
    return rows
