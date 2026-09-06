"""Convert dataset rows into SafeLegalAI regulation-tracker records (one YAML per instrument),
so every court order becomes a page at /regulation/us-<state|federal>/<slug> with version history.

Rules:
- only `fetched-and-read` rows are converted (the site publishes what was actually read)
- every record is written with `verified: false` — the editor flips it after re-opening the source
  (unverified records are noindex and excluded from feeds, widgets and syndication)
- an instrument already present in the tracker (same source URL in any `versions[].url`) is skipped
- nothing is invented: `status: unknown` becomes `in-force` only because the instrument is currently
  posted on the court's site, and the summary says so; undated instruments get the fetch date as the
  version date with version label "As posted (undated)"

    .venv/bin/python pipeline/to_site.py --site /path/to/safelegalai-site [--limit N]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString as DQ

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

TYPE_MAP = {
    "standing-order": "standing-order",
    "administrative-order": "standing-order",
    "general-order": "standing-order",
    "judge-requirements-page": "standing-order",
    "local-rule": "court-rule",
    "proposed-rule": "court-rule",
    "practice-direction": "practice-direction",
    "policy": "policy",
    "notice": "guidance",
}
STATUS_MAP = {"in-force": "in-force", "superseded": "superseded", "rescinded": "withdrawn", "proposed": "proposed", "unknown": "in-force"}
APPLIES_MAP = {"attorneys": "lawyers", "pro-se-litigants": "litigants", "all-filers": "all", "parties": "parties", "court-staff": "court-staff", "judges": "judges", "jurors": "parties", "witnesses": "parties"}


def requirements(o: dict) -> list[str]:
    req = []
    if o["disclose_use"] in ("required", "required-on-request") or o["disclose_tool"] == "required" or o["disclose_how_used"] == "required" or o["mark_ai_sections"] == "required" or o["ai_generated_evidence_disclosure"] == "required":
        req.append("disclosure")
    if o["certify_accuracy"].startswith("required") or o["certify_human_review"] == "required":
        req.append("certification")
    if o["verify_citations"] == "required":
        req.append("verification")
    if o["ai_drafting"] == "prohibited" or o["ai_recording_in_courtroom"] == "prohibited":
        req.append("prohibition")
    if o["certify_confidentiality"] == "required":
        req.append("confidentiality")
    if o["retain_prompts"] == "required":
        req.append("record-keeping")
    if o["ai_drafting"] in ("permitted", "permitted-with-conditions") and not req:
        req.append("permissive")
    if o["warning_only"] and not req:
        req.append("competence")
    return req or ["competence"]


def categories(r: dict) -> list[str]:
    o, cats = r["obligations"], []
    if o["disclose_use"] != "not-addressed" or o["certify_accuracy"] != "not-addressed" or o["mark_ai_sections"] == "required":
        cats.append("disclosure-filings")
    if o["verify_citations"] == "required" or o["certify_accuracy"].startswith("required"):
        cats.append("verification-duty")
    if o["certify_confidentiality"] == "required":
        cats.append("confidentiality-client-data")
    if "pro-se-litigants" in r["applies_to"]:
        cats.append("litigant-in-person")
    if "judges" in r["applies_to"] or "court-staff" in r["applies_to"]:
        cats.append("court-own-use")
    if o["ai_generated_evidence_disclosure"] != "not-addressed" or o["ai_recording_in_courtroom"] != "not-addressed":
        cats.append("evidence-admissibility")
    if o["ai_drafting"] == "prohibited":
        cats.append("ai-decision-prohibition")
    return cats or ["disclosure-filings"]


def short_court(court: str) -> str:
    return re.sub(r"^(United States|U\.S\.) (District|Bankruptcy) Court for the ", "", court).replace("United States Court of Appeals for the ", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", type=Path, required=True)
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    regs_dir = a.site / "src" / "content" / "regulations"
    yaml = YAML()
    yaml.width = 4096
    existing_urls = set()
    for f in regs_dir.glob("*.yaml"):
        doc = yaml.load(f.read_text(encoding="utf-8")) or {}
        for v in doc.get("versions", []) or []:
            if v.get("url"):
                existing_urls.add(v["url"].rstrip("/").lower())
        for s in doc.get("sources", []) or []:
            if s.get("url"):
                existing_urls.add(s["url"].rstrip("/").lower())
    rows = [json.loads(l) for l in (DATA / "orders.jsonl").open(encoding="utf-8") if l.strip()]
    written = skipped = 0
    for r in rows:
        if r["verification"] != "fetched-and-read":
            continue
        if r["source_url"].rstrip("/").lower() in existing_urls:
            skipped += 1
            continue
        if a.limit and written >= a.limit:
            break
        fed = r["court_level"].startswith("federal")
        undated = not r.get("issued_date")
        vdate = (r.get("amended_date") or r.get("issued_date") or r["fetched_at"])
        vdate = vdate if len(vdate) == 10 else f"{vdate}-01"
        summary = r["summary"].strip()
        if r["status"] == "unknown":
            summary = f"{summary} The instrument was posted on the court's website when SafeLegalAI read it on {r['fetched_at']}; the court does not state whether it has been amended or withdrawn."
        rec = {
            "title": DQ(r["title"]),
            "body": DQ(r["court"] if not r.get("judge") else f"{r['court']} — Judge {r['judge']}"),
            "bodyShort": DQ(short_court(r["court"]) if not r.get("judge") else f"{short_court(r['court'])} (Judge {r['judge'].split()[-1]})"),
            "jurisdiction": "us-federal" if fed else "us-state",
            **({"region": DQ(r["state"])} if r.get("state") else {}),
            "country": DQ("US"),
            "type": TYPE_MAP[r["document_type"]],
            "status": STATUS_MAP[r["status"]],
            "appliesTo": sorted({APPLIES_MAP[x] for x in r["applies_to"]}),
            "requirements": requirements(r["obligations"]),
            **({"effectiveDate": r["effective_date"] if len(r["effective_date"]) == 10 else f"{r['effective_date']}-01"} if r.get("effective_date") else {}),
            "versions": [{"version": DQ("As posted (undated)" if undated else ("Amended" if r.get("amended_date") else "Original")), "date": vdate, "url": DQ(r["source_url"]), **({"archiveUrl": DQ(r["archive_url"])} if r.get("archive_url") else {})}],
            "summary": DQ(summary),
            "keyProvisions": [DQ(k) for k in r["key_provisions"]],
            "relatedIncidents": [],
            "sources": [{"label": DQ(f"{short_court(r['court'])} — {r['title']} (primary, {r['source_type']})"), "url": DQ(r["source_url"])}] + ([{"label": DQ("Archived copy (Wayback Machine)"), "url": DQ(r["archive_url"])}] if r.get("archive_url") else []) + [{"label": DQ("SafeLegalAI us-court-ai-orders dataset row (coding, text excerpt, provenance)"), "url": DQ(f"https://github.com/SafeLegalAI/us-court-ai-orders/blob/main/data/orders.jsonl")}],
            "categories": categories(r),
            "lastVerified": r["fetched_at"],
            "verified": False,
        }
        slug = f"us-{r['order_id']}"[:100]
        with (regs_dir / f"{slug}.yaml").open("w", encoding="utf-8") as fh:
            yaml.dump(rec, fh)
        existing_urls.add(r["source_url"].rstrip("/").lower())
        written += 1
    print(json.dumps({"written": written, "skipped_existing": skipped, "eligible": sum(1 for r in rows if r["verification"] == "fetched-and-read")}))


if __name__ == "__main__":
    main()
