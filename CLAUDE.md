# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Not a software project — there's no build step, package manager, or test framework. It's a 3-file content
system for producing the **"BCONHUB Intelligence Report"**: an AI agent (or automation of your choice) researches
recent official Bristlecone/Mahindra Group news, fills in `report-template.html`'s placeholders, and saves the
result into `Reports/` as a standalone HTML file for employees to read.

## Repository layout

- **`Instructions.md`** — the system prompt/rulebook given to whatever AI agent generates the report. Defines
  the sourcing rules, the approved official domain list, the 8 content categories, the full placeholder
  contract, the report filename convention, and a self-check quality checklist. Read this file in full before
  changing anything about what a generated report should contain.
- **`report-template.html`** — the reusable design: a single self-contained HTML/CSS/JS file with `{{PLACEHOLDER}}`
  tokens for the agent to fill in, plus already-working client-side JS (time-range filter, category chips,
  News Feed view) that ships unchanged in every generated report.
- **`Reports/`** — output folder. Generated reports are named `BCONHUB-Report_<YYYY-MM-DD>_<HHMMSS>.html`.
- **`assets/`** — static assets (currently the official Bristlecone logo). Not referenced by relative path from
  the template — see "must stay self-contained" below.
- **`scripts/generate_report.py`** — the automated (non-AI) report generator used by the GitHub Actions
  workflow. See "Automated generation" below.
- **`.github/workflows/generate-report.yml`** — the CI/CD workflow that runs the script daily and on relevant
  pushes, then commits the result into `Reports/`.

## There is no build/test/lint tooling

"Development" here means editing `report-template.html` directly and verifying it in a browser — there is
nothing else that will catch a regression. When you change the template:

- Open it in a browser tab and check the console for JS errors.
- Manually exercise the interactive parts: the Time Range segmented control (Last 24h / Last 48h / Last 60
  Days), all 8 category chips (they scroll-jump to their section and highlight as you scroll — this is
  navigation, not a visibility filter), and the By Category / News Feed toggle.
- Check the mobile layout too (~375px width) — these reports are opened on phones.
- If you need to script a check, injecting fake `data-datetime` values via the browser console and re-running
  `applyWindowFilter()` is an easy way to verify the filtering logic without waiting for real content to age.

## Template architecture (`report-template.html`)

- **Placeholder-fill contract**: every `{{PLACEHOLDER}}` must be replaced by the agent. Each category section
  contains one card wrapped in `<!-- CARD_TEMPLATE_START -->…<!-- CARD_TEMPLATE_END -->` — this block is
  duplicated once per news item (markers removed in the final output). A commented `<!-- EMPTY_STATE -->` block
  swaps in when a category has zero items. The `<div class="no-match" hidden>` line in every section is static
  runtime scaffolding used by the client-side filter JS — it's never filled in or removed by the agent.
- **Two timestamp placeholders drive 100% client-side time filtering, no regeneration needed**:
  `{{REPORT_GENERATED_ISO}}` (on `<body data-generated="...">`) is the filter's reference "now"; each card's
  `{{ITEM_DATETIME_ISO}}` (its `data-datetime` attribute) is compared against it in hours. The reader's
  24h/48h/2-months choice just toggles a `.filtered-out` class per card, recomputes the stat-tile counts, and
  rebuilds the "News Feed" (reverse-chronological, cross-category) view by cloning the currently-visible cards.
  If a generated report has a missing or wrong ISO timestamp, the filter fails silently (the card is just
  always shown) rather than erroring — this is the most likely thing to go subtly wrong in a generated report.
- **8 categories are structural, not data-driven**: each has a fixed `data-category` value on its
  `<section class="block" id="section-<category>">`, a matching `.tag.<category>` CSS class/color, and a
  category chip (`data-cat`) with its own inline `.chip-count` span. The chip↔section wiring is done by naming
  convention (`data-cat` / `data-category` / `id="section-<category>"` all share the same slug), so the generic
  JS (ticker, feed builder, chip-count updater, scroll-spy) doesn't need per-category code — but adding or
  renaming a category still means touching the chip markup, the section markup, and the `.tag.*` CSS by hand.
  Category chips are **navigation**, not a visibility filter: clicking one smooth-scrolls to that section and a
  scroll-spy keeps the matching chip highlighted as the reader scrolls manually.
- **Must stay a single, self-contained file**: no external `<script src>`/`<link>` and no relative-path local
  assets — a generated report is opened standalone, wherever it's stored, with zero network calls.
  This is why the Bristlecone logo is embedded as an inline base64 `data:` URI in the `<img>` tag rather than a
  file reference.

## Automated generation (`scripts/generate_report.py` + GitHub Actions)

`.github/workflows/generate-report.yml` runs the script daily (cron) and on any push that touches
`report-template.html`, `Instructions.md`, or `scripts/**`. The `push` trigger's `paths:` is an allowlist that
deliberately excludes `Reports/**` (GitHub Actions rejects combining `paths` with `paths-ignore` on one
trigger, so exclusion here just means "don't list it") — that's what stops the workflow's own commit into
`Reports/` from re-triggering itself. Don't add `Reports/**` to that `paths:` list.

This script is a deliberately different, narrower path than the manual/AI-assisted flow described in
`Instructions.md`:

- **No LLM, no API key, $0 cost.** It scrapes `mahindra.com/newsroom/press-release` directly with `requests` +
  `BeautifulSoup`, categorizes items with keyword rules (`KEYWORD_RULES` / `INDUSTRY_HINTS`), and fills
  `report-template.html` the same way a human/AI run would — same placeholder contract, same
  `CARD_TEMPLATE_START/END` duplication logic, reimplemented with regex in `replace_section()`.
- **That source paginates one item per page** (`?page=0`, `?page=1`, …, newest first) — not what it looks like
  when you browse it in a real browser, where a "load more" / infinite-scroll interaction has already pulled in
  extra items client-side. `fetch_mahindra_items()` walks pages until it hits an item older than the 60-day
  window, or a safety cap (`max_pages`). If you ever change `SOURCE_URL`, re-derive the pagination behavior
  first — don't assume a single `requests.get()` returns the full list.
- **Coverage is intentionally narrower than a manual run**: only Mahindra Group's corporate newsroom is
  scraped. Bristlecone-specific achievements/events and employee-specific offers are *not* covered — those
  categories will legitimately show empty states from the automated run even when a manually-triggered,
  AI-assisted report (asking Claude directly, per the normal `Instructions.md` flow) can find something by
  searching more broadly. This is by design, not a bug to "fix" by loosening the sourcing rules.
- If `report-template.html`'s section markup changes (e.g. the `CARD_TEMPLATE_START/END`/`EMPTY_STATE`/
  `no-match` structure), `replace_section()`'s regex will need matching updates — it raises a clear
  `RuntimeError` naming the category it couldn't find, rather than silently producing a broken report.

## Known gotcha: PowerShell text encoding will corrupt this file

`report-template.html` and generated reports are full of emoji and Unicode punctuation (🏆🚘📢🌍, em dashes,
→, ™, ·). Editing them via PowerShell's `Get-Content` / `Set-Content` / plain `[System.IO.File]::WriteAllText`
**without an explicit UTF-8 encoding** silently mangles every multi-byte character (mojibake) — this has
already happened once in this repo's history. Windows PowerShell 5.1's default text encoding is not UTF-8.

Prefer the Edit/Write tools for these files. If a PowerShell script edit is unavoidable, force UTF-8 explicitly
on both sides:

```powershell
$content = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
# ...modify $content...
[System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding($false)))
```

## Sourcing rules to preserve if you edit `Instructions.md`

- Official sources only (§3/§4: `bristlecone.com`, the `mahindra.com` family, official LinkedIn pages, BSE/NSE
  filings) — every item needs a working, matching source link.
- There are **two different time windows**, don't conflate them: the **gathering window** is 60 days (wide, so
  a report always has real content, since Bristlecone/Mahindra don't publish daily), while each item's own
  accurate timestamp is what lets the *reader* narrow to the last 24/48 hours after the fact.
- An empty category renders an honest empty-state — content is never fabricated to fill a gap.

## Publishing changes

This folder is not a local git repository and no `git` executable is available on the machine it was authored
on. The remote is `https://github.com/rakeshbob007/Bristlecone-Intelligence-HUB` — the initial push was done
file-by-file through GitHub's web "Upload files" UI (via an automated browser session), not `git push`. Check
whether git is available before assuming any git command will work.
