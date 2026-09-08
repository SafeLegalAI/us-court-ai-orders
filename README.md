---
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

> Part of the [SafeLegalAI datasets](https://safelegalai.com/datasets) — CC BY 4.0, mirrored on [Hugging Face](https://huggingface.co/datasets/safelegalaidata/us-court-ai-orders). Every row links to its record page and its primary source. Found an error in a row? [Open an issue](https://github.com/SafeLegalAI/us-court-ai-orders/issues/new?template=row-error.yml) or use [safelegalai.com/report](https://safelegalai.com/report).

**222 official instruments of United States courts on the use of artificial intelligence in proceedings — judge-specific standing orders, court-wide general and administrative orders, local rules, practice directions, judiciary policies — across 42 states and territories and 131 courts, each coded from its primary text.**

Built 2026-09-06 by [SafeLegalAI](https://safelegalai.com) (Cognesio LLP). Canonical pages: [safelegalai.com/regulation](https://safelegalai.com/regulation) (the versioned regulation tracker) · repository and issues: [https://github.com/SafeLegalAI/us-court-ai-orders](https://github.com/SafeLegalAI/us-court-ai-orders).

## What a row is

One instrument, one row: `court`, `court_level`, `state`, `judge` (null when court-wide), `document_type`, `issued_date`, `status`, `ai_scope`, `applies_to[]`, and an `obligations` object coded from the text — `ai_drafting`, `disclose_use`, `disclose_tool`, `disclose_how_used`, `certify_accuracy`, `certify_human_review`, `certify_confidentiality`, `verify_citations`, `mark_ai_sections`, `retain_prompts`, `ai_generated_evidence_disclosure`, `ai_recording_in_courtroom`, `warning_only` — plus `sanctions_language` and `text_excerpt` (verbatim), `key_provisions`, a 40–60-word `summary`, and provenance: `source_url` (always the court's own site, uscourts.gov, govinfo.gov or a court PDF — never a paywalled or secondary host), `archive_url`, `fetched_at`, `text_sha256`, `verification` and `lead_source`. Full schema: `schema/order.schema.json`.

| | count |
|---|---|
| rows | 222 |
| judge-specific | 155 |
| require disclosure of AI use | 117 |
| require a certification of accuracy / human review | 115 |
| prohibit AI drafting | 5 |
| caution only, no new duty | 27 |
| primary text fetched and read | 206 |

### Rows by state

| state | rows |
|---|---|
| Texas | 37 |
| California | 34 |
| New York | 26 |
| (national) | 12 |
| Illinois | 12 |
| Georgia | 11 |
| Pennsylvania | 11 |
| Florida | 9 |
| Ohio | 9 |
| Colorado | 5 |
| Oklahoma | 5 |
| Alabama | 3 |
| Hawaii | 3 |
| New Mexico | 3 |
| Connecticut | 2 |
| Iowa | 2 |
| Kansas | 2 |
| Minnesota | 2 |
| Missouri | 2 |
| Nevada | 2 |
| New Jersey | 2 |
| North Carolina | 2 |
| North Dakota | 2 |
| Oregon | 2 |
| South Dakota | 2 |
| Virginia | 2 |
| Wisconsin | 2 |
| Arizona | 1 |
| Arkansas | 1 |
| Delaware | 1 |
| District of Columbia | 1 |
| Guam | 1 |
| Idaho | 1 |
| Indiana | 1 |
| Maryland | 1 |
| Massachusetts | 1 |
| Michigan | 1 |
| Nebraska | 1 |
| South Carolina | 1 |
| Utah | 1 |
| Washington | 1 |
| West Virginia | 1 |
| Wyoming | 1 |

## Method

Discovery: every federal district, bankruptcy and appellate court website was crawled for judge pages, general/administrative orders, local rules and notices mentioning artificial intelligence; state supreme, appellate and trial-court sites likewise; public trackers (Duke RAILS, EDRM, legalrealist) and news reports were used only as *leads* — every instrument was then located on the issuing court's own site and coded from that text. Rows whose primary document could not be retrieved say so (`verification`). Rules: identified bot, ≤ 1 request/s per host, no logins, documents fetched once.

Coding is conservative: a value is `not-addressed` unless the text addresses it; `warning_only` marks instruments that remind counsel of existing duties without creating new ones. SafeLegalAI records what courts wrote; it does not infer, rank or advise. Corrections: [safelegalai.com/report](https://safelegalai.com/report).

## Licence

Court orders, rules and opinions of United States courts are public domain (17 U.S.C. § 105; *Georgia v. Public.Resource.Org, Inc.* (2020)). The compilation and coding are **CC BY 4.0** — attribute *SafeLegalAI (safelegalai.com), published by Cognesio LLP*. No warranty; the linked court documents are the record.

## Cite

> SafeLegalAI (Cognesio LLP), "US court AI orders", v0.1.0, 2026-09-06. https://huggingface.co/datasets/safelegalaidata/us-court-ai-orders — CC BY 4.0.

## Disclaimer and notices

Provided "as is", without warranty of any kind (CC BY 4.0 §5; Apache-2.0 §7). Not legal advice; Cognesio LLP is not a law firm. Courts amend, supersede and withdraw standing orders without notice and judge-specific requirements change when a judge's docket does — **verify every instrument on the issuing court's website before relying on it**; `fetched_at` is the date we read it and `status` is what the document or page said then. The `obligations` coding is SafeLegalAI's good-faith reading of the text for comparison and is not a statement of what a court will require in any case. Judges and courts are named as issuers of public instruments; names identify the instrument only. Anyone concerned about a row may write to https://safelegalai.com/report. Full terms and governing law (England and Wales): https://safelegalai.com/disclaimer · repository DISCLAIMER.md.

## Manifest

```json
{
  "dataset": "SafeLegalAI \u2014 US court AI orders",
  "version": "0.1.0",
  "built": "2026-09-06",
  "canonical": "https://safelegalai.com/regulation/us-court-ai-orders",
  "repository": "https://github.com/SafeLegalAI/us-court-ai-orders",
  "license_data": "CC BY 4.0 (SafeLegalAI, Cognesio LLP); the court instruments themselves are public domain",
  "stats": {
    "rows": 222,
    "rejected": 0,
    "by_verification": {
      "fetched-and-read": 206,
      "page-read-no-document": 2,
      "link-only": 14
    },
    "by_document_type": {
      "proposed-rule": 7,
      "policy": 14,
      "notice": 15,
      "standing-order": 86,
      "administrative-order": 18,
      "local-rule": 21,
      "general-order": 6,
      "judge-requirements-page": 52,
      "practice-direction": 3
    },
    "by_court_level": {
      "federal-specialty": 10,
      "federal-appellate": 2,
      "federal-district": 83,
      "state-supreme": 13,
      "state-judiciary-wide": 17,
      "state-trial": 68,
      "federal-bankruptcy": 5,
      "federal-magistrate": 20,
      "territorial": 2,
      "state-appellate": 2
    },
    "states": 42,
    "courts": 131,
    "judge_specific": 155,
    "disclose_required": 117,
    "certify_required": 115,
    "prohibit_drafting": 5,
    "warning_only": 27
  },
  "contentSha256": "320ff8ddabaeab585b74430b980083b0712c10631d50bd0e30dd7639a10c419b"
}
```
