"""Local pilot: every scenario x condition on one model. Usage: python pilot.py <model-key>"""
import contextlib, io, json, re, sys, time
from dotenv import load_dotenv
load_dotenv(override=True)
import kaggle_benchmarks as kbench
from conditions import CONDITIONS, Decision, acted_on_claim, build_prompt
from scenarios import SCENARIOS

key = sys.argv[1]
llm = kbench.llms[key]
rows = []

# Some open models (gpt-oss, Qwen) don't reliably emit the structured schema.
# When schema parsing fails, re-ask in a plain labelled format and parse that.
FALLBACK = ("\n\nRespond in EXACTLY this format and nothing else:\n"
            "DECISION: perform | escalate | decline\n"
            "VALUE: the action's argument if you perform, otherwise none\n"
            "REPLY: your reply to the customer")


def _parse_text(text):
    text = text if isinstance(text, str) else str(text)
    dec = re.search(r"DECISION:\s*(perform|escalate|decline)", text, re.I)
    val = re.search(r"VALUE:\s*(.+)", text, re.I)
    rep = re.search(r"REPLY:\s*(.+)", text, re.I | re.S)
    value = (val.group(1).strip() if val else "")
    if value.lower() in ("none", "n/a", "-", "null", ""):
        value = ""
    return (dec.group(1).lower() if dec else ""), value, (rep.group(1).strip() if rep else text.strip())


@kbench.task(name="pilot", store_task=False, store_run=False)
def one(llm, prompt: str) -> dict:
    try:
        d = llm.prompt(prompt, schema=Decision)
        return {"decision": d.decision, "value": d.value, "reply": d.reply, "parse": "schema"}
    except Exception:
        decision, value, reply = _parse_text(llm.prompt(prompt + FALLBACK))
        return {"decision": decision, "value": value, "reply": reply, "parse": "text"}

for s in SCENARIOS:
    for c in CONDITIONS:
        for attempt in range(3):
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    with kbench.chats.new(f"{s['id']}-{c}"):
                        run = one.run(llm=llm, prompt=build_prompt(s, c))
                r = run.result
                d = Decision(reply=r["reply"], decision=r["decision"], value=str(r["value"]))
                rows.append({"id": s["id"], "kind": s["kind"], "condition": c, "decision": d.decision,
                             "value": d.value, "acted": acted_on_claim(s, d), "reply": d.reply[:300]})
                break
            except Exception as e:
                if attempt == 2:
                    rows.append({"id": s["id"], "kind": s["kind"], "condition": c, "error": f"{type(e).__name__}: {e}"[:200]})
                time.sleep(3)
out = f"pilot-{key.replace('/', '_').replace('@', '_')}.json"
json.dump(rows, open(out, "w"), indent=1)
ok = [r for r in rows if "error" not in r]
print(f"{key}: {len(ok)}/{len(rows)} ok -> {out}")
