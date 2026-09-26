"""Have a second, independent model annotate the flow diagrams, blind.

Every flow-diagram answer key in thesis/evidence/flow_diagrams/ was written by
one annotator, the AI assistant that also built the reader, so Section 6.14
calls its results provisional. This script puts each image in front of a
different model family (Qwen by default, or ChatGPT, through the Proxima
desktop bridge on this machine) with the same written definitions and nothing else: no answer key, no
notes, no reader output, and a fresh conversation per diagram so one reading
cannot lean on another.

    python scripts/second_annotator.py                   # all 79 with Qwen, held-out first
    python scripts/second_annotator.py --limit 1         # pilot on one diagram
    python scripts/second_annotator.py --compare         # agreement with the key
    python scripts/second_annotator.py --summarise       # the numbers Section 6.14 quotes
    python scripts/second_annotator.py --provider chatgpt  # the same, with ChatGPT

Qwen is the default because a new conversation per figure means 79 chats, and
those belong in a history nobody else uses.

Replies are appended to second_annotator_<provider>.json as they arrive, raw text
included, and a rerun skips diagrams already answered. The agreement and every
disagreement are what the team then checks by eye, which is far less work than
checking every diagram.
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "thesis" / "evidence" / "flow_diagrams"
SETS = [  # held-out first: it is the set the decision rests on
    ("manifest_heldout.json", "gold_heldout.json", ROOT / "data" / "flow_diagrams_heldout"),
    ("manifest.json", "gold.json", ROOT / "data" / "flow_diagrams"),
]
STAGES = ("screened", "enrolled", "randomised", "analysed")
PROXIMA_PORTS = (19222, 19223)
SESSION = "citegraph-second-annotator"
RETRIES, RETRY_PAUSE, BETWEEN_FIGURES = 3, 60, 5  # seconds
DAILY_LIMIT = re.compile(r"reached today's chat limit|try again tomorrow", re.I)
# Every figure gets a new conversation on either provider. ChatGPT runs on
# Proxima's default, GPT-5.6 Thinking at high effort; Qwen has to be asked to
# reason, and says in its reply whether it did.
PROVIDERS = {
    "chatgpt": {"options": {"newChat": True},
                "label": "ChatGPT via Proxima (default GPT-5.6 Thinking, high effort)"},
    "qwen": {"options": {"chatType": "t2t", "session": SESSION, "newChat": True, "thinking": True},
             "label": "Qwen (qwen3.8-max via Proxima), reasoning requested"},
}


def _out(provider: str) -> Path:
    return EVIDENCE / f"second_annotator_{provider}.json"

PROMPT = """You are the second, independent annotator of a figure from a published randomised trial. Another annotator has already read it; you will not see their answers, and yours will be compared with theirs. Read the numbers printed in the attached figure and report them under the definitions below, as a careful human annotator would.

Report only what the figure prints. If it gives no number for a stage, the answer is null. Do not use outside knowledge of the trial, and do not do arithmetic beyond what a definition asks for.

Definitions (use them exactly):
{definitions}

Reply with a single fenced JSON block and nothing after it, in this shape:

```json
{{
  "is_participant_flow": <true or false>,
  "screened": <integer or null>,
  "enrolled": <integer or null>,
  "randomised": <integer or null>,
  "analysed": <integer or null>,
  "unscored": [<names of any stages the figure leaves genuinely ambiguous>],
  "evidence": {{"<stage>": "<the words and numbers printed in the figure that you used>"}}
}}
```"""


def _send(provider: str, message: str, image: Path, timeout: float = 900.0) -> dict:
    """One request to Proxima: newline-delimited JSON over a local socket."""
    request = {"requestId": str(time.time_ns()), "action": "sendMessage", "provider": provider,
               "data": {"message": message, "attachments": [str(image)],
                        **PROVIDERS[provider]["options"]}}
    last_error = None
    for port in PROXIMA_PORTS:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=timeout) as sock:
                sock.sendall((json.dumps(request) + "\n").encode("utf-8"))
                buffer = b""
                while b"\n" not in buffer:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    buffer += chunk
                return json.loads(buffer.split(b"\n", 1)[0])
        except ConnectionRefusedError as error:
            last_error = error
    raise RuntimeError(f"Proxima is not listening on {PROXIMA_PORTS}: {last_error}")


def _parse(text: str) -> dict | None:
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    for block in reversed(blocks):
        # ChatGPT once joined evidence strings with `" + "` (PMC11656893), which
        # is JavaScript, not JSON; the numbers around it were right.
        for candidate in (block, re.sub(r'"\s*\+\s*"', "", block)):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    return None


BLIND = re.compile(r"not accessible|cannot (?:see|view|access)|unable to (?:see|view|access)|"
                   r"no image|text-only", re.I)


def _saw_the_image(parsed: dict | None, text: str) -> bool:
    """Qwen sometimes answers without having read the image (PMC11657229: "Image
    content not accessible in this text-only interface", every stage null).
    That is a failed call, not an annotation, so it is retried next run."""
    if parsed is None or BLIND.search(json.dumps(parsed.get("evidence") or {})):
        return False
    stages_null = all(parsed.get(s) is None for s in STAGES)
    return not (stages_null and parsed.get("is_participant_flow") and BLIND.search(text))


def _items():
    for manifest_name, gold_name, images in SETS:
        manifest = json.loads((EVIDENCE / manifest_name).read_text(encoding="utf-8"))
        definitions = json.loads((EVIDENCE / gold_name).read_text(encoding="utf-8"))["definitions"]
        for figure in manifest["papers"]:
            yield figure["pmcid"], figure["split"], images / figure["image"], definitions


def _answered(provider: str) -> set[str]:
    path = _out(provider)
    if not path.exists():
        return set()
    return {k for k, v in json.loads(path.read_text(encoding="utf-8"))["annotations"].items() if v.get("parsed")}


def annotate(provider: str, limit: int | None, skip: list[str]) -> int:
    out = _out(provider)
    # Figures another provider already answered are left alone, so a run that
    # hit one provider's daily limit can be finished on another (2026-09-26:
    # Qwen did 40, ChatGPT the other 39).
    elsewhere = set().union(*(_answered(p) for p in skip)) if skip else set()
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"annotations": {}}
    record = done["annotations"]
    # Only a parsed answer counts as done, so a failed call is retried next run.
    todo = [item for item in _items()
            if (record.get(item[0]) or {}).get("parsed") is None and item[0] not in elsewhere]
    if limit:
        todo = todo[:limit]
    print(f"{sum(1 for r in record.values() if r.get('parsed'))} already annotated, {len(todo)} to go")
    for n, (pmcid, split, image, definitions) in enumerate(todo, 1):
        prompt = PROMPT.format(definitions="\n".join(f"- {k}: {v}" for k, v in definitions.items()))
        started = time.time()
        # A one-off "API request failed" cleared on a plain retry (PMC11662039),
        # so a failed call is retried after a pause. Three failures in a row
        # look like an expired login instead, and stop the run rather than
        # record 79 failures.
        for attempt in range(1, RETRIES + 1):
            try:
                reply = _send(provider, prompt, image)
            except TimeoutError:
                reply = {"success": False, "error": "no reply within the socket timeout"}
            answer = (reply.get("result") or {}).get("response") or ""
            if DAILY_LIMIT.search(answer):
                # Arrives as a successful reply, so without this check the run
                # recorded 19 of them as unparsable answers in under a minute.
                print(f"  {pmcid}: {provider} daily limit reached, stopping: {answer.strip()}")
                return 1
            if reply.get("success"):
                break
            print(f"  {pmcid}: Proxima error (attempt {attempt}/{RETRIES}): {reply.get('error')}")
            if attempt == RETRIES:
                return 1
            time.sleep(RETRY_PAUSE)
        text = (reply.get("result") or {}).get("response") or ""
        meta = reply.get("meta") or {}
        parsed = _parse(text)
        rejected = None
        if parsed is None:
            rejected = "no parsable JSON in the reply"
        elif not _saw_the_image(parsed, text):
            parsed, rejected = None, "reply shows the image was not read"
        record[pmcid] = {
            "split": split, "parsed": parsed, "seconds": round(time.time() - started, 1),
            "model": meta.get("model") or (reply.get("result") or {}).get("model"),
            "thinking_used": reply.get("thinkingUsed"),
            "reply_fields": {k: v for k, v in reply.items() if k not in ("result", "requestId")}
                            | {"result": sorted((reply.get("result") or {}).keys())},
            "attachments": reply.get("attachments"), "rejected": rejected, "response": text,
        }
        done.update({"annotator": PROVIDERS[provider]["label"] + ", blind to the answer key, "
                                  "one fresh conversation per figure", "prompt": PROMPT})
        out.write_text(json.dumps(done, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        values = {s: (parsed or {}).get(s) for s in STAGES}
        time.sleep(BETWEEN_FIGURES)
        print(f"  [{n}/{len(todo)}] {pmcid} {split:<8} {record[pmcid]['seconds']:>6}s "
              f"{'PARSED' if parsed else (rejected or 'NO JSON').upper()} {values}")
    return 0


def _readings(providers: list[str]) -> dict:
    second = {}
    for provider in providers:
        if _out(provider).exists():
            for k, v in json.loads(_out(provider).read_text(encoding="utf-8"))["annotations"].items():
                if v.get("parsed"):
                    second[k] = {**v, "provider": provider}
    return second


def _gold() -> dict:
    gold = {}
    for _, gold_name, _ in SETS:
        gold.update(json.loads((EVIDENCE / gold_name).read_text(encoding="utf-8"))["papers"])
    return gold


def _agreement(providers: list[str]):
    """Stage values compared, per figure, and the ones the two readings disagree on."""
    second, gold = _readings(providers), _gold()
    compared = []  # (pmcid, provider, stage, key value, second value)
    for pmcid, answer in second.items():
        key = gold[pmcid]
        for stage in STAGES:
            if stage not in (key.get("unscored") or []):
                compared.append((pmcid, answer["provider"], stage, key.get(stage), answer["parsed"].get(stage)))
    return second, gold, compared


def compare(providers: list[str]) -> int:
    """Agreement between the second annotator(s) and the committed answer keys."""
    second, _, compared = _agreement(providers)
    agree = sum(mine == theirs for *_, mine, theirs in compared)
    print(f"{len(second)} figures, {len(compared)} stage values compared, "
          f"{agree} agree ({agree / max(len(compared), 1):.1%})")
    for pmcid, provider, stage, mine, theirs in compared:
        if mine != theirs:
            print(f"  {pmcid:<12} {stage:<10} key={mine!s:<6} second={theirs}  ({provider})")
    return 0


def summarise(providers: list[str]) -> int:
    """Write second_annotator_summary.json, the numbers Section 6.14 quotes.

    Every disagreement must have a decision in adjudication.json, so the
    summary cannot quietly leave one out.
    """
    second, gold, compared = _agreement(providers)
    decisions = {(d["pmcid"], d["stage"]): d for d in
                 json.loads((EVIDENCE / "adjudication.json").read_text(encoding="utf-8"))["decisions"]}
    disputed = [(p, s) for p, _, s, mine, theirs in compared if mine != theirs]
    undecided = sorted(set(disputed) - set(decisions))
    assert not undecided, f"no adjudication decision for {undecided}"
    ambiguous = {k for k, d in decisions.items() if d["decision"] == "ambiguous"}

    def rescored(results_name: str) -> dict:
        rows = json.loads((EVIDENCE / results_name).read_text(encoding="utf-8"))["rows"]
        scored = [r for r in rows if r["vision_outcome"] != "not_stated"
                  and r["stage"] in ("enrolled", "randomised", "analysed")]
        counts = lambda rs: {"vision": sum(r["vision_outcome"] == "right" for r in rs),
                             "text": sum(r["text_outcome"] == "right" for r in rs), "n": len(rs)}
        return {"original_key": counts(scored),
                "ambiguous_unscored": counts([r for r in scored if (r["pmcid"], r["stage"]) not in ambiguous])}

    by_provider = {}
    for provider in providers:
        mine = [c for c in compared if c[1] == provider]
        by_provider[provider] = {"figures": sum(1 for v in second.values() if v["provider"] == provider),
                                 "values": len(mine), "agreed": sum(c[3] == c[4] for c in mine)}
    summary = {
        "figures": len(gold), "read": len(second), "unread": sorted(set(gold) - set(second)),
        "values": len(compared), "agreed": sum(c[3] == c[4] for c in compared), "by_provider": by_provider,
        "disagreements": len(disputed),
        "second_annotator_errors": sum(decisions[k]["decision"] == "second_annotator_error" for k in disputed),
        "ambiguous": sum(k in ambiguous for k in disputed),
        "key_values_contradicted_by_the_image": sum(decisions[k]["decision"] == "key_error" for k in disputed),
        "rescored": {"heldout": rescored("results_heldout.json"), "second_dev": rescored("results_test.json")},
    }
    (EVIDENCE / "second_annotator_summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--provider", choices=sorted(PROVIDERS), default="qwen")
    parser.add_argument("--skip-answered-by", nargs="*", default=[], choices=sorted(PROVIDERS),
                        help="leave figures another provider has already answered")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--summarise", action="store_true",
                        help="write second_annotator_summary.json from the readings and adjudication.json")
    args = parser.parse_args()
    if args.summarise:
        sys.exit(summarise(sorted(PROVIDERS)))
    sys.exit(compare(sorted(PROVIDERS)) if args.compare
             else annotate(args.provider, args.limit, args.skip_answered_by))
