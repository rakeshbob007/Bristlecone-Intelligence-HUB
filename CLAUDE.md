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
- **`bot/telegram-worker.js`** — a Cloudflare Worker that lets anyone request the latest report on demand via
  a Telegram bot, independent of the daily schedule. See "On-demand delivery" below. This file is the source
  of truth for what's deployed, but deploying a change means manually pasting it into the Cloudflare dashboard
  (Workers & Pages → bconhub-bot → Edit code) — there is no CI/CD link between this repo and the Worker.

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

- **No LLM, no API key, $0 cost.** It scrapes four sources directly with `requests` + `BeautifulSoup`,
  categorizes every item with keyword rules (`KEYWORD_RULES` / `INDUSTRY_HINTS`), and fills
  `report-template.html` the same way a human/AI run would — same placeholder contract, same
  `CARD_TEMPLATE_START/END` duplication logic, reimplemented with regex in `replace_section()`.
- **Four scraped sources, one fetcher function each** (see the `fetchers` list in `main()`), each confirmed
  server-rendered (no headless browser needed) and genuinely editorial (not placeholder/test content):
  - `fetch_mahindra_items()` — `mahindra.com/news-room/press-release`. Paginates **one item per page**
    (`?page=0`, `?page=1`, …, newest first) — not what it looks like in a real browser, where a "load more"
    interaction has already pulled in extra items client-side. Walks pages until an item falls outside the
    60-day window, or a safety cap (`max_pages`).
  - `fetch_mahindra_finance_items()` — `mahindrafinance.com/media/press-release`. Server-rendered `.pressInfo`
    blocks (`span` date in "28th January 2026" ordinal-suffix format, `h3` title, a `.pdf` link used directly
    as the source URL — there is no separate article page). No pagination is scraped; only what's on the base
    URL. Note `/media` alone (no further path) 403s — the exact `/media/press-release` path is required.
  - `fetch_bristlecone_category()` — reused for both `bristlecone.com/category/in-the-news/` and
    `/category/press-releases/`. Standard WordPress archive: `article` elements, title+link in
    `.post-header h3.title a`, the date as **plain text** (no machine-readable attribute) in the first
    `<span>` of `.post-header` ("Month D, YYYY"), real `/page/N/` pagination.
  - If you ever change any of these source URLs, re-derive the pagination/rendering behavior first — don't
    assume a single `requests.get()` returns the full list, or that a real browser's DOM matches the raw
    server response.
- **Two known Mahindra Group domains are deliberately NOT scraped**, both confirmed by hand before deciding
  against them — don't re-add them without re-checking whether the underlying problem was fixed:
  - `auto.mahindra.com/news` — reachable and even server-rendered, but its News Room widget currently serves
    placeholder content ("News Room Blog 9", a generic "AUTOCAR INDIA" byline, stale 2023-24 dates) regardless
    of the `pageNo`/`serviceName` query params. Scraping it would mean publishing fake news under a real
    Mahindra Auto byline — a direct violation of the "no fabricated content" sourcing rule.
  - `mahindrarise.com` — returns a "Non-compliant action" bot-block page to a plain HTTP client; there's no
    free way to get past it without a paid/headless-browser proxy service.
- **Every item now carries its own `source_name`** (`"Mahindra Group Newsroom"` / `"Mahindra Finance"` /
  `"Bristlecone"`) instead of one global constant — `build_card()`, the Top Story fields, and
  `EXECUTIVE_SUMMARY` all read it per-item, so the "Source: X ↗" footer on each card is always accurate even
  though items now come from four different domains.
- Coverage is still narrower than a manual run in one respect: Bristlecone's own site has no scrapable listing
  for employee-specific offers/benefits (that content doesn't live in a dated news feed), so the **Offers**
  category will still legitimately show an empty state from the automated run more often than a
  manually-triggered, AI-assisted report that can search more broadly. This is by design, not a bug to "fix"
  by loosening the sourcing rules.
- If `report-template.html`'s section markup changes (e.g. the `CARD_TEMPLATE_START/END`/`EMPTY_STATE`/
  `no-match` structure), `replace_section()`'s regex will need matching updates — it raises a clear
  `RuntimeError` naming the category it couldn't find, rather than silently producing a broken report.

## On-demand delivery (`bot/telegram-worker.js` + Cloudflare Worker)

A Telegram bot (`@BCONREPORTBOT`) lets anyone request the latest report instantly, independent of the daily
schedule — send it `/latest` or `/report` and it replies with the newest file from `Reports/`. Runs entirely
on Cloudflare Workers' free tier: event-driven (a webhook, not polling), so there's no cron-reliability
concern like the GitHub Actions schedule has.

- **Three secrets configured directly in the Cloudflare dashboard** (Workers & Pages → bconhub-bot → Settings
  → Variables and Secrets) — none of these live in this repo:
  - `TELEGRAM_BOT_TOKEN` — from @BotFather.
  - `WEBHOOK_SECRET` — an arbitrary random string; Telegram echoes it back in a header
    (`X-Telegram-Bot-Api-Secret-Token`) on every webhook call, which is how the Worker verifies a request
    genuinely came from Telegram and not some random POST to its public URL.
  - `GITHUB_TOKEN` — a fine-grained, read-only, public-repo-scoped GitHub personal access token (no
    expiration). Needed because unauthenticated GitHub API calls are capped at 60/hour, and Cloudflare
    Workers share egress IPs across many customers worldwide — that shared-IP limit gets exhausted in
    practice, not just in theory. With this token the effective limit is 5,000/hour. The header is added
    conditionally (`if (env.GITHUB_TOKEN)`), so the code doesn't hard-fail if it's ever removed.
- **Two built-in diagnostic routes**, both plain `GET` (safe to open in any browser, no payload needed):
  - `/whoami` — calls Telegram's `getMe` with the stored token and returns the raw response. First thing to
    check if the bot goes silent — confirms the token itself is valid without ever exposing it.
  - `/setup` — (re-)registers this Worker's own URL as the bot's webhook. Safe to call repeatedly; Telegram
    just reports `"Webhook is already set"` if nothing changed. Necessary once after every fresh deploy of a
    brand-new Worker, and again if the Worker is ever redeployed to a different URL.
- **The file is uploaded to Telegram directly — never passed as a URL.** An earlier version passed
  `document: <raw.githubusercontent.com URL>` in the `sendDocument` call and let Telegram fetch it
  server-side; that failed intermittently with `"Bad Request: failed to get HTTP URL content"` — GitHub's raw
  CDN doesn't reliably serve Telegram's own fetcher. The fix: the Worker downloads the file itself
  (`fetch(rawUrl)` → `arrayBuffer()`), then re-uploads those bytes to Telegram as `multipart/form-data`
  (`FormData` + `Blob`). Slightly more Worker CPU time, but categorically more reliable — don't revert to the
  URL-based approach.
- **Every Telegram API call checks `data.ok` and returns/logs the real error** (`sendMessage`, `sendDocument`)
  instead of firing-and-forgetting — if a user reports "nothing happened" again, the bot should now be
  telling them why in-chat; check Cloudflare's Observability → Invocations tab for `console.error` output if
  not.
- **Deploying a change is manual and easy to forget**: edit `bot/telegram-worker.js` in this repo, but the
  live behavior doesn't change until you also paste the updated code into the Cloudflare dashboard's editor
  and click **Save and deploy**. Keep both in sync by hand.
- **Known friction points worth knowing before touching this again**:
  - Cloudflare's code editor is a Monaco instance inside a same-origin `<iframe>` — clicking it doesn't always
    focus it first try. Verify via `document.activeElement.tagName === "IFRAME"` before doing anything
    keyboard-driven (`Ctrl+A` etc.), or `Ctrl+A` can select the whole outer page instead of just the code.
  - `api.telegram.org` may be blocked outright on a restrictive corporate network (categorized as
    "Chat, IM & other communication" by some IT security policies) — this is why `/setup` calls Telegram
    *from the Worker's own network* rather than requiring a direct browser call to Telegram's API.

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
