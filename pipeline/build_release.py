"""Merge the collection agents' rows, validate against the schema, dedupe, and write the release
bundle (JSONL · CSV · Parquet · README · manifest). Optionally push to Hugging Face.

    .venv/bin/python pipeline/build_release.py [--push] [--version 0.1.0]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work" / "agents"
DATA = ROOT / "data"
SCHEMA = json.loads((ROOT / "schema" / "order.schema.json").read_text())
HF_ORG = os.environ.get("HF_ORG", "safelegalaidata")
HF_REPO = "us-court-ai-orders"
SITE = "https://safelegalai.com"
GH = "https://github.com/SafeLegalAI/us-court-ai-orders"
BANNED_HOSTS = ("advance.lexis.com", "westlaw.com", "ropesgray.com", "justia.com", "legalhack.io", "legalaigovernance.com")


def read_jsonl(p: Path):
    out = []
    for i, l in enumerate(p.open(encoding="utf-8"), 1):
        if l.strip():
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError as e:
                print(f"  ! {p.name}:{i} bad JSON ({e}) — skipped")
    return out


def validate(r: dict) -> list[str]:
    errs = []
    props = SCHEMA["properties"]
    for k in SCHEMA["required"]:
        if k not in r or r[k] in (None, "", []):
            errs.append(f"missing {k}")
    for k, spec in props.items():
        if k not in r or r[k] is None:
            continue
        if "enum" in spec and r[k] not in spec["enum"]:
            errs.append(f"{k}={r[k]!r} not in enum")
        if spec.get("type") == "array" and "enum" in spec.get("items", {}):
            for v in r[k]:
                if v not in spec["items"]["enum"]:
                    errs.append(f"{k} item {v!r} not in enum")
        if "pattern" in spec and isinstance(r[k], str) and not re.fullmatch(spec["pattern"], r[k]):
            errs.append(f"{k} pattern")
        if "maxLength" in spec and isinstance(r[k], str) and len(r[k]) > spec["maxLength"]:
            errs.append(f"{k} too long")
    ob = r.get("obligations") or {}
    for k in SCHEMA["properties"]["obligations"]["required"]:
        if k not in ob:
            errs.append(f"obligations.{k} missing")
        elif "enum" in SCHEMA["properties"]["obligations"]["properties"][k] and ob[k] not in SCHEMA["properties"]["obligations"]["properties"][k]["enum"]:
            errs.append(f"obligations.{k}={ob[k]!r} not in enum")
    if any(h in (r.get("source_url") or "") for h in BANNED_HOSTS):
        errs.append("source_url is a paywalled/secondary host")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--version", default="0.1.0")
    a = ap.parse_args()
    rows, rejected = [], []
    for f in sorted(WORK.glob("g*.jsonl")):
        for r in read_jsonl(f):
            r["_group"] = f.stem
            errs = validate(r)
            (rejected if errs else rows).append((r, errs) if errs else r)
    # dedupe on source_url, then on (court, judge, title)
    seen, out = {}, []
    for r in rows:
        key = r["source_url"].rstrip("/").lower()
        alt = (r["court"].lower(), (r.get("judge") or "").lower(), re.sub(r"\W+", " ", r["title"].lower()).strip())
        if key in seen or alt in seen:
            prev = seen.get(key) or seen.get(alt)
            # keep the better-verified row
            rank = {"fetched-and-read": 3, "fetched-not-parsed": 2, "page-read-no-document": 1, "link-only": 0}
            if rank[r["verification"]] > rank[prev["verification"]]:
                out[out.index(prev)] = r
                seen[key] = seen[alt] = r
            continue
        seen[key] = seen[alt] = r
        out.append(r)
    # unique ids
    ids = Counter(r["order_id"] for r in out)
    for r in out:
        if ids[r["order_id"]] > 1:
            r["order_id"] = f"{r['order_id']}-{hashlib.sha1(r['source_url'].encode()).hexdigest()[:6]}"
    out.sort(key=lambda r: (r["state"] or "", r["court"], r.get("judge") or "", r["order_id"]))
    for r in out:
        r.pop("_group", None)
    DATA.mkdir(exist_ok=True)
    with (DATA / "orders.jsonl").open("w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (WORK.parent / "rejected.jsonl").open("w", encoding="utf-8") as fh:
        for r, errs in rejected:
            fh.write(json.dumps({"errors": errs, "row": r}, ensure_ascii=False) + "\n")
    # flat CSV: obligations.* as columns
    ob_keys = SCHEMA["properties"]["obligations"]["required"]
    cols = [k for k in SCHEMA["properties"] if k != "obligations"] + [f"obligations.{k}" for k in ob_keys]
    with (DATA / "orders.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in out:
            flat = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in r.items() if k != "obligations"}
            flat.update({f"obligations.{k}": r["obligations"].get(k) for k in ob_keys})
            w.writerow(flat)
    try:
        import pyarrow as pa, pyarrow.parquet as pq

        flatrows = []
        for r in out:
            flat = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in r.items() if k != "obligations"}
            flat.update({f"obligations.{k}": r["obligations"].get(k) for k in ob_keys})
            flatrows.append({c: flat.get(c) for c in cols})
        pq.write_table(pa.Table.from_pylist(flatrows), DATA / "orders.parquet", compression="zstd")
    except ImportError:
        pass
    # stats for the card
    st = {
        "rows": len(out),
        "rejected": len(rejected),
        "by_verification": dict(Counter(r["verification"] for r in out)),
        "by_document_type": dict(Counter(r["document_type"] for r in out)),
        "by_court_level": dict(Counter(r["court_level"] for r in out)),
        "states": len({r["state"] for r in out if r["state"]}),
        "courts": len({r["court"] for r in out}),
        "judge_specific": sum(1 for r in out if r.get("judge")),
        "disclose_required": sum(1 for r in out if r["obligations"]["disclose_use"] in ("required", "required-on-request")),
        "certify_required": sum(1 for r in out if r["obligations"]["certify_accuracy"].startswith("required")),
        "prohibit_drafting": sum(1 for r in out if r["obligations"]["ai_drafting"] == "prohibited"),
        "warning_only": sum(1 for r in out if r["obligations"]["warning_only"]),
    }
    manifest = {
        "dataset": "SafeLegalAI — US court AI orders",
        "version": a.version,
        "built": date.today().isoformat(),
        "canonical": f"{SITE}/regulation/us-court-ai-orders",
        "repository": GH,
        "license_data": "CC BY 4.0 (SafeLegalAI, Cognesio LLP); the court instruments themselves are public domain",
        "stats": st,
        "contentSha256": hashlib.sha256((DATA / "orders.jsonl").read_bytes()).hexdigest(),
    }
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "README.md").write_text(card(out, manifest), encoding="utf-8")
    print(json.dumps(st, indent=1))
    if a.push:
        from huggingface_hub import HfApi

        api = HfApi(token=os.environ.get("HF_TOKEN"))
        repo_id = f"{HF_ORG}/{HF_REPO}"
        api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
        api.upload_folder(repo_id=repo_id, repo_type="dataset", folder_path=str(DATA), path_in_repo="data", commit_message=f"v{a.version} — {st['rows']} orders")
        api.upload_file(path_or_fileobj=str(ROOT / "README.md"), path_in_repo="README.md", repo_id=repo_id, repo_type="dataset", commit_message=f"card v{a.version}")
        print(f"pushed https://huggingface.co/datasets/{repo_id}")


def card(rows, manifest) -> str:
    st = manifest["stats"]
    by_state = Counter(r["state"] or "(national)" for r in rows)
    states = "\n".join(f"| {s} | {n} |" for s, n in by_state.most_common())
    today = manifest["built"]
    return f"""---
license: cc-by-4.0
pretty_name: "US court AI orders — every standing order, local rule and court policy on AI in filings (SafeLegalAI)"
language:
  - en
size_categories:
  - n<1K
tags:
  - legal
  - law
  - courts
  - standing-orders
  - generative-ai
  - court-rules
  - ai-governance
  - safelegalai
configs:
  - config_name: orders
    default: true
    data_files:
      - split: train
        path: data/orders.parquet
---

# US court AI orders

**{st['rows']} official instruments of United States courts on the use of artificial intelligence in proceedings — judge-specific standing orders, court-wide general and administrative orders, local rules, practice directions, judiciary policies — across {st['states']} states and territories and {st['courts']} courts, each coded from its primary text.**

Built {today} by [SafeLegalAI]({SITE}) (Cognesio LLP). Canonical pages: [{SITE.removeprefix("https://")}/regulation]({SITE}/regulation) (the versioned regulation tracker) · repository and issues: [{GH}]({GH}).

## What a row is

One instrument, one row: `court`, `court_level`, `state`, `judge` (null when court-wide), `document_type`, `issued_date`, `status`, `ai_scope`, `applies_to[]`, and an `obligations` object coded from the text — `ai_drafting`, `disclose_use`, `disclose_tool`, `disclose_how_used`, `certify_accuracy`, `certify_human_review`, `certify_confidentiality`, `verify_citations`, `mark_ai_sections`, `retain_prompts`, `ai_generated_evidence_disclosure`, `ai_recording_in_courtroom`, `warning_only` — plus `sanctions_language` and `text_excerpt` (verbatim), `key_provisions`, a 40–60-word `summary`, and provenance: `source_url` (always the court's own site, uscourts.gov, govinfo.gov or a court PDF — never a paywalled or secondary host), `archive_url`, `fetched_at`, `text_sha256`, `verification` and `lead_source`. Full schema: `schema/order.schema.json`.

| | count |
|---|---|
| rows | {st['rows']} |
| judge-specific | {st['judge_specific']} |
| require disclosure of AI use | {st['disclose_required']} |
| require a certification of accuracy / human review | {st['certify_required']} |
| prohibit AI drafting | {st['prohibit_drafting']} |
| caution only, no new duty | {st['warning_only']} |
| primary text fetched and read | {st['by_verification'].get('fetched-and-read', 0)} |

### Rows by state

| state | rows |
|---|---|
{states}

## Method

Discovery: every federal district, bankruptcy and appellate court website was crawled for judge pages, general/administrative orders, local rules and notices mentioning artificial intelligence; state supreme, appellate and trial-court sites likewise; public trackers (Duke RAILS, EDRM, legalrealist) and news reports were used only as *leads* — every instrument was then located on the issuing court's own site and coded from that text. Rows whose primary document could not be retrieved say so (`verification`). Rules: identified bot, ≤ 1 request/s per host, no logins, documents fetched once.

Coding is conservative: a value is `not-addressed` unless the text addresses it; `warning_only` marks instruments that remind counsel of existing duties without creating new ones. SafeLegalAI records what courts wrote; it does not infer, rank or advise. Corrections: [{SITE.removeprefix("https://")}/report]({SITE}/report).

## Licence

Court orders, rules and opinions of United States courts are public domain (17 U.S.C. § 105; *Georgia v. Public.Resource.Org, Inc.* (2020)). The compilation and coding are **CC BY 4.0** — attribute *SafeLegalAI ({SITE.removeprefix("https://")}), published by Cognesio LLP*. No warranty; the linked court documents are the record.

## Cite

> SafeLegalAI (Cognesio LLP), "US court AI orders", v{manifest['version']}, {today}. https://huggingface.co/datasets/{HF_ORG}/{HF_REPO} — CC BY 4.0.

## Disclaimer and notices

Provided "as is", without warranty of any kind (CC BY 4.0 §5; Apache-2.0 §7). Not legal advice; Cognesio LLP is not a law firm. Courts amend, supersede and withdraw standing orders without notice and judge-specific requirements change when a judge's docket does — **verify every instrument on the issuing court's website before relying on it**; `fetched_at` is the date we read it and `status` is what the document or page said then. The `obligations` coding is SafeLegalAI's good-faith reading of the text for comparison and is not a statement of what a court will require in any case. Judges and courts are named as issuers of public instruments; names identify the instrument only. Anyone concerned about a row may write to https://safelegalai.com/report. Full terms and governing law (England and Wales): https://safelegalai.com/disclaimer · repository DISCLAIMER.md.

## Manifest

```json
{json.dumps(manifest, indent=2)}
```
"""


if __name__ == "__main__":
    main()
