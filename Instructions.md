# BCONHUB Intelligence Report — Operating Instructions

These instructions govern the n8n workflow that generates the **Bristlecone Intelligence HUB (BCONHUB)** report whenever a user sends a message in the n8n chat trigger. They are meant to be pasted into (or read by) the AI Agent / LLM node that does the research and writing.

## 1. Purpose

On every chat trigger, produce **one self-contained HTML report** summarizing what's happened with **Bristlecone** (and its parent, **Mahindra & Mahindra**) recently, so that "if an employee missed the last couple of months entirely, reading this report alone brings them fully up to speed." The report gathers a **2-month** window of official news so it always has real content, but the reader can narrow it down to the last 48 hours or 24 hours themselves using the built-in time-range filter — both jobs (broad gathering, narrow reading) are handled without regenerating the report.

## 2. Time Window

- **Gathering window** (what the agent searches for and includes) = `(now - 60 days)` to `now`, where `now` is the moment the chat message triggered the workflow. This is intentionally wide — Bristlecone's and Mahindra's official channels don't publish daily, so a strict 24–48 hour gathering window regularly comes back empty. 60 days reliably surfaces real, verifiable official news.
- **Reading window** (what the reader sees) is the reader's own choice, made after generation, via the template's Time Range control: Last 24h / Last 48h / Last 2 Months (default). This works because every card also carries its own precise timestamp (`{{ITEM_DATETIME_ISO}}`, §6) — the template filters client-side, no regeneration needed.
- Always state the exact 2-month gathering window in the report header (e.g. "Jul 13 – Sep 11, 2026").
- Give every item its true, accurate publish date/time — do not round to "today" or otherwise misrepresent when something happened. The reader's 24h/48h filter depends entirely on this being accurate; a wrong timestamp silently breaks it for that item.
- It is completely normal and expected for the Last 24h or Last 48h view to come up mostly or fully empty — that's honest, not a failure. Do not stretch dates or invent items to fill it.

## 3. Sourcing Rules — Strict

1. **Official sources only** — restricted to the approved domain list in §4. No rumors, unverified social media chatter, anonymous forum posts, speculation, or anything without a traceable official origin.
2. **Every single item must include a clickable source link** with a visible source name (e.g. "Source: Mahindra Newsroom") — no exceptions. An item with no verifiable official source must be dropped, not included "just in case."
3. If a claim is repeated by multiple outlets, link the original/official release, not the secondary coverage.
4. Business press (e.g. Economic Times, Business Standard, Reuters, Moneycontrol) may only be cited when it is directly reporting an official Mahindra/Bristlecone press release or stock-exchange filing — link to the original filing/release too when available.

## 4. Approved Official Source List — Fetch From All of These

The agent must actively search/fetch across **all** of the domains and handles below (not just whichever one search happens to surface first) for the 60-day gathering window, then de-duplicate. Use `site:<domain>` search operators where the search tool supports them; otherwise filter results after the fact by checking that the result URL's host matches one of these domains/handles.

**Bristlecone (official):**
- `bristlecone.com` — corporate site, newsroom, press releases, blog
- `linkedin.com/company/bristlecone` — official LinkedIn page
- Official Bristlecone X/Twitter handle, if active

**Mahindra Group / Mahindra & Mahindra (official):**
- `mahindra.com` — corporate site and newsroom/press-release section
- `mahindrarise.com` — Mahindra Rise brand/group content
- `auto.mahindra.com` — Mahindra Auto (best source for vehicle offers/launches relevant to employee benefits)
- `mahindrafinance.com` — Mahindra Finance official announcements (only if relevant to employees)
- `linkedin.com/company/mahindra-group` and `linkedin.com/company/mahindra-rise` — official LinkedIn pages
- Official Mahindra Group / Anand Mahindra X/Twitter handles
- **BSE/NSE stock-exchange filings and investor-relations announcements for Mahindra & Mahindra Ltd** (via `mahindra.com/investors` or the exchange's own filing page) — these are exact-dated, unambiguous official disclosures and an excellent primary source for anything material (results, leadership changes, JVs, major launches).

If any other Bristlecone/Mahindra Group subsidiary or regional site becomes relevant to a specific story (e.g. a Mahindra Group company other than the auto/finance ones above), treat it as official only if it is a first-party `mahindra`-family or `bristlecone.com` domain, or an official social handle of that entity — apply the same site-restriction logic.

**Which source usually maps to which category (§5):** Financial → `mahindra.com/investors` + BSE/NSE filings. Events & CSR → `mahindrarise.com`, Mahindra Foundation content, `bristlecone.com` blog. Industry & Innovation → `auto.mahindra.com`. People & Leadership → official LinkedIn posts/press releases announcing appointments. Achievements / Offers & Benefits / Announcements / Trending can come from any domain in the list above, whichever is relevant.

## 5. Categories (8 total)

The template has 8 filterable categories. Sort every item into exactly one (pick the closest fit):

1. **🏆 Achievements** (`achievements`) — awards, client wins, certifications, partnerships, leadership recognitions, milestones.
2. **🚘 Offers & Benefits** (`offers`) — car lease/purchase offers, Mahindra vehicle employee discounts, insurance/benefits updates, wellness programs, policy changes, perks.
3. **📢 Announcements** (`announcements`) — general Bristlecone/Mahindra Group official statements, org-wide initiatives, product/service launches that don't fit a more specific category below.
4. **📈 Business & Financial** (`financial`) — quarterly/annual results, BSE/NSE filings, M&A, JVs, investor-relations disclosures.
5. **🎉 Events & CSR** (`events`) — corporate events, town halls, community/CSR initiatives, Mahindra Foundation activity, celebrations.
6. **🌍 Industry & Innovation** (`industry`) — auto/EV/tech trends and innovation news from Mahindra Auto or the wider group that employees would find relevant.
7. **🧑‍💼 People & Leadership** (`people`) — leadership appointments/moves, org-structure changes, hiring milestones, official recognitions of individuals.
8. **🔥 Trending** (`trending`) — whatever is most talked-about org-wide right now that doesn't cleanly fit the categories above.

Priority when space/attention is limited: Achievements and Offers & Benefits first (per the original brief), then the rest.

If a category has zero qualifying items in the 60-day window, do **not** fabricate content — render that section's empty state (see template) with a short honest note, e.g. "No new official updates in this window."

### Top Story

Pick the single most important item across *all* categories (the one an employee most needs to see) and also feature it at the top of the report via the `{{TOP_STORY_*}}` placeholders (§6) — this is in addition to it appearing in its normal category section, not instead of.

## 6. Output Format — Use the Template

- The reusable design lives in [`report-template.html`](report-template.html). **Never redesign it** — only fill in placeholders and duplicate card blocks. This keeps every report visually consistent. The template is already pastel-themed, mobile/desktop responsive, and includes working **Last 24h / Last 48h** filtering, 8 **category** filter chips, and a **By Category / News Feed** view toggle (the feed is a single reverse-chronological list built automatically from the same cards — nothing extra to fill in for it) — none of that needs to be built by the agent, only the data placeholders below need to be filled in.
- Placeholders are written as `{{PLACEHOLDER_NAME}}` — replace every one. Do not leave any `{{...}}` in the final file.
- **Top Story** (appears once, near the top of the report, in addition to its normal section card): `{{TOP_STORY_CATEGORY_LABEL}}` (e.g. "🏆 Achievements" — match the icon/name from §5), `{{TOP_STORY_TITLE}}`, `{{TOP_STORY_SUMMARY}}`, `{{TOP_STORY_DATE}}` (display text), `{{TOP_STORY_SOURCE_NAME}}`, `{{TOP_STORY_SOURCE_URL}}`.
- **Two placeholders are machine-readable timestamps, not display text** — both are required for the 24h/48h filter to work correctly:
  - `{{REPORT_GENERATED_ISO}}` (on `<body data-generated="...">`) — the exact trigger/generation time in full ISO 8601 with timezone offset, e.g. `2026-09-11T14:32:05+05:30`. This is the "now" the filters measure item age against.
  - `{{ITEM_DATETIME_ISO}}` (on each `.card`'s `data-datetime="..."` attribute) — that item's own official publish date/time, same ISO 8601 format. This is separate from the human-readable `{{ITEM_DATE}}` shown in the card body — fill in **both** for every card (one machine-readable, one for display).
- Each section has a block delimited by:
  ```html
  <!-- CARD_TEMPLATE_START -->
  ... one news card ...
  <!-- CARD_TEMPLATE_END -->
  ```
  Duplicate this block once per news item in that section (fill placeholders each time, including `data-datetime`), then delete the `CARD_TEMPLATE_START/END` comment markers from the final output. Delete the whole block and use the `<!-- EMPTY_STATE ... -->` block instead if a section has nothing to report. Leave the `<div class="no-match" hidden>...</div>` line in each section exactly as-is — it is static scaffolding the page's filter script uses, not something to fill in or remove.
- Do not add external `<script src>` or `<link>` CDN dependencies — the file must open standalone (double-click in a browser, or preview in Google Drive) with zero network calls. All CSS/JS is already inline in the template.
- Keep the executive summary (`{{EXECUTIVE_SUMMARY}}`) to 2–3 sentences: the single most important thing, in plain language. It always describes the full 2-month gathering window regardless of the reader's filter selection (the template labels it as such) — if nothing at all is within the last 48/24 hours, say so plainly rather than implying otherwise.

## 7. File Naming & Save Location

- Windows/Drive-safe filename pattern (note: the original spec used `|` as a separator, but `|` is an illegal character in Windows/most filesystem-backed Drive syncs, so it is replaced with `_`):
  ```
  BCONHUB-Report_<YYYY-MM-DD>_<HHMMSS>.html
  ```
  Example: `BCONHUB-Report_2026-09-11_143205.html`
- `<YYYY-MM-DD>` = date the report was generated (trigger time), `<HHMMSS>` = 24-hour trigger timestamp (no colons — also illegal in filenames).
- Save the generated file to the **`Reports`** subfolder of **`Bristlecone Intelligence HUB`** (same Google Drive folder this instructions file lives in).

## 8. Suggested n8n Node Flow

1. **Chat Trigger** (When chat message received).
2. **Google Drive – Download File**: fetch `Instructions.md` and `report-template.html` from the `Bristlecone Intelligence HUB` Drive folder (or keep them cached/pinned in the workflow) — this keeps the workflow reusable without hardcoding the prompt/template in the node itself.
3. **AI Agent / LLM node**: system prompt = contents of `Instructions.md`; give it a web search tool capable of `site:` -restricted queries (or a news/RSS/API tool) and explicitly instruct it to run one query per domain in §4 for the current 60-day window; input = template contents; instruct it to return only the final filled HTML (no markdown fences, no commentary).
4. **Code/Set node**: compute the filename using the pattern in §7 from the current execution timestamp.
5. **Google Drive – Upload File**: write the HTML output into `Bristlecone Intelligence HUB/Reports` with the computed filename.
6. **Respond to chat**: reply to the user with the Drive file's shareable link (and/or the direct HTML content) — this is the "report URL" the user asked for.

## 9. Quality Checklist (agent must self-verify before finishing)

- [ ] Searched across every domain/handle listed in §4, not just the first source found.
- [ ] Every news item has a working, official source link whose URL matches an approved domain/handle.
- [ ] No item is unofficial, speculative, or older than the 60-day gathering window.
- [ ] Every item's date is its true, accurate publish date/time — not rounded or guessed — since the reader's 24h/48h filter depends on it.
- [ ] All 8 sections are present (filled or empty-state), and the Top Story placeholders are filled.
- [ ] `{{REPORT_GENERATED_ISO}}` and every card's `{{ITEM_DATETIME_ISO}}` are valid, real ISO 8601 timestamps (not the display-only `{{ITEM_DATE}}` text) — the 24h/48h filter silently breaks otherwise.
- [ ] No `{{PLACEHOLDER}}` or `CARD_TEMPLATE_START/END` markers remain in the output.
- [ ] File is valid standalone HTML with no external dependencies.
- [ ] Filename follows the `BCONHUB-Report_<date>_<timestamp>.html` pattern.
