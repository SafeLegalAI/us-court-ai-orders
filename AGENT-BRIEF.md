# Agent brief — collecting US court AI orders (read fully before starting)

You are building one slice of **SafeLegalAI's `us-court-ai-orders` dataset**: every official instrument of a United States court that addresses the use of artificial intelligence in proceedings — judge-specific standing orders, court-wide general/administrative orders, local rules, practice directions, judiciary policies and notices. **Not** sanctions opinions or judgments (those belong to a different dataset); an opinion that *also* announces a rule for the court is included only if the court adopted it as a standing instrument.

## The rule that governs everything
**We record what the court wrote; we do not infer.** Every field is coded from the primary text. If the text does not address a point, the value is `not-addressed`. If you could not retrieve the text, say so in `verification` and leave the obligations at `not-addressed` with `warning_only: false` and a `notes` explanation — never guess from a secondary description.

## Legal rules for sources (non-negotiable)
- **Use only primary sources**: the court's own website (`*.uscourts.gov`, state judiciary sites such as `nycourts.gov`, `txcourts.gov`, `courts.ca.gov`, `flcourts.gov`), `govinfo.gov`, or a PDF issued by the court. US court orders and rules are public domain (17 U.S.C. §105; *Georgia v. Public.Resource.Org*), so you may download and quote them.
- **Never** fetch, cite as source, or rely on: `advance.lexis.com`, `westlaw.com`, `ropesgray.com`, Justia, law-firm client alerts, blogs, or any tracker. You may *read* a tracker or a news report to learn that an order exists (record it in `lead_source` / `secondary_urls`), then go to the court's site and find the actual document. If you cannot find the primary document, include the row with `verification: "link-only"`, `source_url` set to the most official page you found, and explain in `notes` — or omit it if nothing official exists.
- **Politeness**: identify yourself with `-A "SafeLegalAI-Bot/1.0 (+https://safelegalai.com/datasets; hello@safelegalai.com)"`, at most one request per second per host, no logins, no form submissions, respect robots.txt, and download each document once. Use `curl -sL --max-time 60`. Extract PDF text with `pdftotext -layout file.pdf -` (installed). Do not download PDFs larger than 25 MB.
- Optionally request an archive snapshot: `curl -sI "https://web.archive.org/save/<url>"` and record the resulting `https://web.archive.org/web/<timestamp>/<url>` in `archive_url`; if the Wayback Machine is slow or refuses, leave `archive_url` null — do not retry more than once.

## Where to look (discovery — this is the valuable part)
1. **Each federal district court website** in your list: look for "Judges" → each judge's page → "Standing Orders", "Requirements", "Procedures", "Judge-Specific Requirements", "Civil Procedures", "Courtroom Procedures", "Notices", and court-wide "General Orders" / "Administrative Orders" / "Local Rules" / "Notices". Search each site (its own search box via URL, e.g. `?s=artificial+intelligence`, or `site:<host> "artificial intelligence"` via web_search) for: `"artificial intelligence"`, `"generative AI"`, `"generative artificial intelligence"`, `ChatGPT`, `"large language model"`. Many orders are titled "Standing Order Regarding Use of Artificial Intelligence" or are a paragraph inside a longer "Judge's Requirements" document — include those too (`document_type: judge-requirements-page`).
2. **State courts** in your list: the state supreme court / administrative office of the courts (AI policies, administrative orders, interim rules, task-force orders), intermediate appellate courts, and trial courts that publish standing orders (Texas district courts on `topics.txcourts.gov`, Illinois circuit courts, New York judges' part rules on `nycourts.gov`).
3. **Lead lists** (leads only — verify at the primary source): the rows I have placed for your jurisdictions in `work/leads/<your-group>.json` (from public trackers; their `link`/`original_link` may be paywalled — find the court copy); EDRM's judicial-orders table (https://edrm.net/judicial-orders-2/) and Duke RAILS (https://rails.legal/resources/resource-ai-orders/) for your jurisdictions.
4. web_search patterns that work: `site:uscourts.gov "artificial intelligence" standing order <district>`; `"<Judge name>" "artificial intelligence" standing order`; `<state> supreme court administrative order artificial intelligence`.

## What to write, and where
Append one JSON object per line to **`work/agents/<your-group>.jsonl`** (path given in your task) conforming exactly to `schema/order.schema.json` (read it first: `cat schema/order.schema.json`). Rules of thumb:
- `order_id`: `<court_code>-<judge-last-name or court>-<yyyy>-<two-or-three-word-title>`, all lower-case, e.g. `txnd-starr-2023-mandatory-certification`, `il-supreme-court-2024-ai-policy`.
- `summary`: 40–60 words, descriptive, present tense, names the court, who it binds, what it requires and the date. No adjectives of judgement.
- `key_provisions`: 3–7 statements, each traceable to a sentence in the text.
- `sanctions_language` and `text_excerpt`: verbatim quotes only, in quotation marks, ≤ 25 words for sanctions_language.
- `obligations`: code from the text. Typical mappings — "must disclose whether generative AI was used" → `disclose_use: required`; "must certify that every citation was checked by a human" → `certify_accuracy: required-each-filing` and `verify_citations: required`; "attorneys are reminded of Rule 11" with no new duty → all `not-addressed` and `warning_only: true`; "prohibited from using generative AI to draft" → `ai_drafting: prohibited`.
- `lead_source` is an array (e.g. `["court-site-crawl"]`, `["legalrealist","court-site-crawl"]`).
- Dates ISO; `issued_date` null if the document is undated (say so in `notes`).
- Do **not** write rows for Canadian/UK/other non-US courts.
- Do **not** duplicate: if the same instrument appears as an amended version, write ONE row with `amended_date` and mention prior versions in `notes`.

Validate as you go: `python3 -c "import json,sys;[json.loads(l) for l in open('work/agents/<group>.jsonl')]"`.

## When you are done
Reply with a short report only (the data is in the file): rows written; counts by `verification`; courts crawled with zero findings (so we know they were checked); anything that needs a human (ambiguous status, conflicting versions). Do not paste the rows into the reply.
