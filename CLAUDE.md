# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Not a software project — there's no build step, package manager, or test framework. It's a 3-file content
system that drives an external **n8n workflow**: a chat trigger causes an AI Agent node to research recent
official Bristlecone/Mahindra Group news, fill in `report-template.html`'s placeholders, and save the result
into `Reports/` as a standalone "BCONHUB Intelligence Report" HTML file for employees to read.

## Repository layout

- **`Instructions.md`** — the system prompt/rulebook pasted into the n8n AI Agent node. Defines the sourcing
  rules, the approved official domain list, the 8 content categories, the full placeholder contract, the
  report filename convention, the suggested n8n node flow, and a self-check quality checklist. Read this file
  in full before changing anything about what a generated report should contain.
- **`report-template.html`** — the reusable design: a single self-contained HTML/CSS/JS file with `{{PLACEHOLDER}}`
  tokens for the agent to fill in, plus already-working client-side JS (time-range filter, category chips,
  News Feed view) that ships unchanged in every generated report.
- **`Reports/`** — output folder. Generated reports are named `BCONHUB-Report_<YYYY-MM-DD>_<HHMMSS>.html`.
- **`assets/`** — static assets (currently the official Bristlecone logo). Not referenced by relative path from
  the template — see "must stay self-contained" below.

## There is no build/test/lint tooling

"Development" here means editing `report-template.html` directly and verifying it in a browser — there is
nothing else that will catch a regression. When you change the template:

- Open it in a browser tab and check the console for JS errors.
- Manually exercise the interactive parts: the Time Range segmented control (Last 24h / Last 48h / Last 2
  Months), all 8 category chips, and the By Category / News Feed toggle.
- Check the mobile layout too (~375px width) — these reports are opened on phones via Google Drive.
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
  `<section class="block">`, a matching `.tag.<category>` CSS class/color, and a category filter chip. The
  chip↔section↔stat-tile wiring is done by naming convention (`data-cat` / `data-category` / `.stat-<category>`
  all share the same slug), so the generic JS (ticker, feed builder, stat updater) doesn't need per-category
  code — but adding or renaming a category still means touching the chip markup, the section markup, the
  `.tag.*` CSS, and the matching `.stat-*` tile by hand.
- **Must stay a single, self-contained file**: no external `<script src>`/`<link>` and no relative-path local
  assets — a generated report is opened standalone or previewed inside Google Drive with zero network calls.
  This is why the Bristlecone logo is embedded as an inline base64 `data:` URI in the `<img>` tag rather than a
  file reference.

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
