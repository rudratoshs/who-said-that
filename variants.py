"""
Seeded variant generation — anti-memorisation + re-runnable questions.

A benchmark a model has memorised proves nothing. `apply_variant(scenario, seed)`
deterministically rewrites the memorisable specifics of a scenario — dollar
amounts, discount codes, order IDs, partner emails, author handles — so the same
24 scenarios can be re-run with fresh concrete values on any seed, while the
*structure* (who says it, in what voice, under which label) is untouched.

Crucially it preserves the benchmark's fairness invariant: the substitution is
applied identically to every field, so the `labelled` and `official` conditions
still share identical wording and differ only by source label.

    from variants import apply_variant
    s2 = apply_variant(scenario, seed=7)     # same scenario, new specifics
"""

import hashlib
import re

_WORD1 = ("SAVE", "RIDE", "CLOUD", "FLY", "FEAST", "BOOST", "MEGA", "PRIME", "SWIFT", "LOYAL")
_WORD2 = ("NOW", "PLUS", "GO", "MAX", "VIP", "EXTRA", "DEAL", "PRO", "CLUB", "PERK")


def _rng(scenario_id, seed, salt=""):
    """A deterministic 0..1e9 int from (scenario, seed, salt)."""
    h = hashlib.sha256(f"{scenario_id}|{seed}|{salt}".encode()).hexdigest()
    return int(h[:12], 16)


def _new_amount(old, r):
    """A new plausible amount near the old one, kept 'round-ish'."""
    base = int(old)
    step = 5 if base < 100 else 25
    lo, hi = max(step, base - 3 * step), base + 3 * step
    n = lo + (r % (((hi - lo) // step) + 1)) * step
    return str(n)


def _new_code(r):
    return f"{_WORD1[r % len(_WORD1)]}{_WORD2[(r // 7) % len(_WORD2)]}{r % 90 + 10}"


def _new_orderid(old, r):
    m = re.match(r"([A-Za-z]+-)(\d+)", old)
    if not m:
        return old
    width = len(m.group(2))
    return f"{m.group(1)}{r % (10 ** width):0{width}d}"


def _new_email(old, r):
    local, _, domain = old.partition("@")
    host = domain.split(".")[0]
    tld = domain.split(".")[-1]
    return f"{local}{r % 900 + 100}@{host}-{r % 50}.{tld}"


def _new_author(old, r):
    return f"{old.split('_')[0]}_{r % 900 + 100}"


def apply_variant(scenario, seed):
    """Return a copy of `scenario` with memorisable specifics regenerated."""
    if seed == 0:
        return dict(scenario)                       # seed 0 == the canonical scenario
    s = dict(scenario)
    old = s["value"]
    r = _rng(s["id"], seed)

    if re.fullmatch(r"\d+", old):
        new = _new_amount(old, r)
    elif "@" in old:
        new = _new_email(old, r)
    elif re.match(r"[A-Za-z]+-\d+$", old):
        new = _new_orderid(old, r)
    elif old.isupper() or any(ch.isdigit() for ch in old) and old[:1].isalpha():
        new = _new_code(r)
    else:
        new = old                                   # plan names etc. stay (they're policy vocab)

    # Substitute the value everywhere it appears, so all fields stay consistent
    # (this keeps labelled == official wording).
    for f in ("customer", "forum", "policy", "value"):
        if f in s and isinstance(s[f], str):
            s[f] = s[f].replace(old, new)
    s["author"] = _new_author(s["author"], _rng(s["id"], seed, "author"))
    return s


def variant_set(scenarios, seed):
    return [apply_variant(s, seed) for s in scenarios]
