#!/usr/bin/env python3
"""Generate the BCONHUB Intelligence Report by scraping official Bristlecone/Mahindra pages.

No LLM, no API keys, no paid services — pure rule-based scraping + keyword categorization, following
the sourcing rules and placeholder contract in Instructions.md.

Sources scraped (all confirmed server-rendered, real editorial content, no bot-blocking):
  - mahindra.com/news-room/press-release   (Mahindra Group corporate newsroom)
  - mahindrafinance.com/media/press-release (Mahindra Finance press releases & results)
  - bristlecone.com/category/in-the-news    (Bristlecone press mentions / exec commentary)
  - bristlecone.com/category/press-releases (Bristlecone official press releases)

Deliberately NOT scraped:
  - auto.mahindra.com/news — technically reachable, but its News Room widget currently serves
    placeholder content ("News Room Blog 9", generic "AUTOCAR INDIA" byline, stale 2023-24 dates)
    regardless of query params — not genuine news, so including it would violate the "no fabricated
    content" sourcing rule. Revisit if Mahindra Auto ever repopulates that widget with real content.
  - mahindrarise.com — returns a "Non-compliant action" bot-block page to a plain HTTP client; no
    reliable free way to scrape it without a paid/headless-browser service.
"""
import html as html_lib
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "report-template.html"
REPORTS_DIR = REPO_ROOT / "Reports"
IST = timezone(timedelta(hours=5, minutes=30))
WINDOW_DAYS = 60

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BCONHUB-ReportBot/1.0; "
                         "+https://github.com/rakeshbob007/Bristlecone-Intelligence-HUB)"}

CATEGORIES = ["achievements", "offers", "announcements", "financial", "events", "industry", "people", "trending"]

CATEGORY_LABELS = {
    "achievements": "🏆 Achievements",
    "offers": "🚘 Offers & Benefits",
    "announcements": "📢 Announcements",
    "financial": "📈 Financial",
    "events": "🎉 Events & CSR",
    "industry": "🌍 Industry & Innovation",
    "people": "🧑‍💼 People & Leadership",
    "trending": "🔥 Trending",
}

# Checked in order; first match wins. Keep specific categories ahead of the generic industry fallback.
KEYWORD_RULES = [
    ("people", ["appoint", "joins as", "elevat", "promot", "named as group", "steps down", "resigns",
                "chief human resources", "chief executive", "managing director"]),
    ("achievements", ["award", "recogni", "ranked", " wins ", "certified", "named among", "rising star",
                      "leader in", "market guide", "disruptor rating", "gold partner"]),
    ("financial", ["sales", "results", "profit", "credit rating", "dividend", "revenue", "quarter",
                   "vehicle sales", "tractors sold", "tractors in", "growth of", "financial results"]),
    ("offers", ["battery-as-a-service", "discount", "financing", "emi scheme", "offer on"]),
    ("events", ["summit", "csr", "foundation", "town hall", "conclave", "conference", "gig workers",
                "dhan samvaad"]),
]
INDUSTRY_HINTS = ["launch", "unveil", "expand", "introduce", "new range", "architecture", "platform",
                   "partner advantage", "joins google cloud", "sap store"]


def categorize(item):
    text = item["title"].lower()
    for cat, keywords in KEYWORD_RULES:
        if any(k in text for k in keywords):
            return cat
    if any(k in text for k in INDUSTRY_HINTS):
        return "industry"
    return "announcements"


def esc(s):
    return html_lib.escape(s, quote=True)


def fmt_time_12h(dt_ist):
    s = dt_ist.strftime("%I:%M %p IST")
    return s[1:] if s[0] == "0" else s


# ---------------------------------------------------------------------------
# Source 1: Mahindra Group corporate newsroom
# ---------------------------------------------------------------------------

def fetch_mahindra_items(window_start_utc, max_pages=40):
    """mahindra.com/news-room/press-release paginates ONE item per page via ?page=N, newest first.
    Walk pages until an item falls outside the window (or pagination ends / a safety cap is hit)."""
    source_url = "https://www.mahindra.com/news-room/press-release"
    source_name = "Mahindra Group Newsroom"
    items = []
    for page in range(max_pages):
        try:
            resp = requests.get(f"{source_url}?page={page}", headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"WARNING: mahindra.com request failed for page {page}: {exc}", file=sys.stderr)
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        ul = soup.select_one("ul.search-list")
        lis = ul.select(":scope > li") if ul else []
        if not lis:
            break
        hit_boundary = False
        for li in lis:
            a = li.select_one("div.grid-box > a") or li.find("a")
            h2 = li.select_one("h2")
            time_tag = li.select_one("time")
            if not (a and h2 and time_tag and time_tag.get("datetime")):
                continue
            href = (a.get("href") or "").strip()
            title = h2.get_text(strip=True)
            try:
                dt = datetime.strptime(time_tag["datetime"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if dt < window_start_utc:
                hit_boundary = True
                continue
            wrap = li.select_one("div.wrap")
            site_tag = ""
            if wrap:
                classes = [c for c in wrap.get("class", []) if c != "wrap"]
                site_tag = classes[0] if classes else ""
            if not href.startswith("http"):
                href = "https://www.mahindra.com" + href
            items.append({"title": title, "url": href, "dt": dt, "site_tag": site_tag,
                          "source_name": source_name})
        if hit_boundary:
            break
    return items


# ---------------------------------------------------------------------------
# Source 2: Mahindra Finance press releases
# ---------------------------------------------------------------------------

_ORDINAL_RE = re.compile(r"(\d+)(st|nd|rd|th)", re.IGNORECASE)


def _parse_ordinal_date(text):
    """'28th January 2026' -> datetime. Mahindra Finance renders dates with an ordinal suffix."""
    cleaned = _ORDINAL_RE.sub(r"\1", text.strip())
    return datetime.strptime(cleaned, "%d %B %Y").replace(tzinfo=IST).astimezone(timezone.utc)


def fetch_mahindra_finance_items(window_start_utc):
    """mahindrafinance.com/media/press-release is server-rendered (confirmed via direct fetch) but
    shows no further pagination on the base URL — one page's worth is all that's collected here."""
    source_url = "https://www.mahindrafinance.com/media/press-release"
    source_name = "Mahindra Finance"
    items = []
    try:
        resp = requests.get(source_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"WARNING: mahindrafinance.com request failed: {exc}", file=sys.stderr)
        return items
    soup = BeautifulSoup(resp.text, "html.parser")
    for block in soup.select(".pressInfo"):
        span = block.find("span")
        h3 = block.find("h3")
        pdf_a = block.select_one('a[href$=".pdf"]')
        if not (span and h3 and pdf_a):
            continue
        try:
            dt = _parse_ordinal_date(span.get_text(strip=True))
        except ValueError:
            continue
        if dt < window_start_utc:
            continue
        items.append({"title": h3.get_text(strip=True), "url": pdf_a["href"], "dt": dt,
                      "site_tag": "Mahindra Finance", "source_name": source_name})
    return items


# ---------------------------------------------------------------------------
# Source 3 & 4: Bristlecone WordPress "In the News" / "Press Releases" archives
# ---------------------------------------------------------------------------

def fetch_bristlecone_category(slug, site_tag, window_start_utc, max_pages=6):
    """bristlecone.com/category/<slug>/ is a standard WordPress archive: ~10 <article> items per
    page, date as plain text ("Month D, YYYY") inside the first <span> of .post-header, real
    /page/N/ pagination."""
    source_name = "Bristlecone"
    items = []
    for page in range(1, max_pages + 1):
        url = (f"https://www.bristlecone.com/category/{slug}/" if page == 1
               else f"https://www.bristlecone.com/category/{slug}/page/{page}/")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"WARNING: bristlecone.com/{slug} request failed on page {page}: {exc}", file=sys.stderr)
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.select("article")
        if not articles:
            break
        hit_boundary = False
        for art in articles:
            header = art.select_one(".post-header")
            title_a = art.select_one(".post-header h3.title a, .post-header h2.title a")
            date_span = header.find("span") if header else None
            if not (title_a and date_span):
                continue
            try:
                dt = datetime.strptime(date_span.get_text(strip=True), "%B %d, %Y") \
                    .replace(tzinfo=IST).astimezone(timezone.utc)
            except ValueError:
                continue
            if dt < window_start_utc:
                hit_boundary = True
                continue
            items.append({"title": title_a.get_text(strip=True), "url": title_a["href"], "dt": dt,
                          "site_tag": site_tag, "source_name": source_name})
        if hit_boundary:
            break
    return items


def build_card(item, category):
    tag_text = esc(item["site_tag"] or category.title())
    title = esc(item["title"])
    dt_ist = item["dt"].astimezone(IST)
    date_display = dt_ist.strftime("%B %d, %Y")
    iso = item["dt"].isoformat()
    summary = f"Official {esc(item['site_tag'] or 'company')} update from {esc(item['source_name'])}. See the full press release for details."
    return f'''        <div class="card" data-datetime="{iso}" style="animation-delay:0.05s"><div class="card-inner">
          <div class="card-top">
            <div class="card-title">{title}</div>
            <div class="tag {category}">{tag_text}</div>
          </div>
          <p class="desc">{summary}</p>
          <div class="card-foot">
            <div class="date">{date_display}</div>
            <a class="source" href="{item['url']}" target="_blank" rel="noopener">Source: {esc(item['source_name'])} ↗</a>
          </div>
        </div></div>
'''


def replace_section(template, category, items_for_cat):
    """Replace one category section's CARD_TEMPLATE block with real cards, or its EMPTY_STATE text."""
    section_pattern = re.compile(
        r'(<section class="block" id="section-' + re.escape(category) + r'".*?<div class="cards">\s*)'
        r'<!-- CARD_TEMPLATE_START -->.*?<!-- CARD_TEMPLATE_END -->'
        r'(\s*<!-- EMPTY_STATE\s*.*?\s*EMPTY_STATE -->)'
        r'(\s*<div class="no-match" hidden>.*?</div>)',
        re.DOTALL,
    )

    def _sub(m):
        before, empty_block, no_match = m.group(1), m.group(2), m.group(3)
        if items_for_cat:
            cards_html = "\n".join(build_card(it, category) for it in items_for_cat)
            return before + cards_html + no_match
        empty_inner = re.search(r'EMPTY_STATE\s*(.*?)\s*EMPTY_STATE', empty_block, re.DOTALL).group(1).strip()
        return before + empty_inner + "\n" + no_match

    new_template, n = section_pattern.subn(_sub, template, count=1)
    if n == 0:
        raise RuntimeError(f"Could not find CARD_TEMPLATE block for category '{category}' — "
                            "report-template.html structure may have changed; update this script's regex.")
    return new_template


def main():
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc.astimezone(IST)
    window_start_utc = now_utc - timedelta(days=WINDOW_DAYS)

    all_items = []
    fetchers = [
        ("Mahindra Group Newsroom", lambda: fetch_mahindra_items(window_start_utc)),
        ("Mahindra Finance", lambda: fetch_mahindra_finance_items(window_start_utc)),
        ("Bristlecone – In the News", lambda: fetch_bristlecone_category("in-the-news", "In the News", window_start_utc)),
        ("Bristlecone – Press Releases", lambda: fetch_bristlecone_category("press-releases", "Press Release", window_start_utc)),
    ]
    sources_scanned = []
    for label, fetch in fetchers:
        try:
            found = fetch()
            all_items.extend(found)
            sources_scanned.append(f"{label} ({len(found)})")
        except Exception as exc:  # noqa: BLE001 - keep the workflow green even if one source fails
            print(f"WARNING: failed to fetch {label}: {exc}", file=sys.stderr)
            sources_scanned.append(f"{label} (failed)")

    by_category = {c: [] for c in CATEGORIES}
    for it in all_items:
        by_category[categorize(it)].append(it)
    for cat in by_category:
        by_category[cat].sort(key=lambda x: x["dt"], reverse=True)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    for cat in CATEGORIES:
        template = replace_section(template, cat, by_category[cat])

    total = sum(len(v) for v in by_category.values())
    all_items_sorted = sorted(all_items, key=lambda x: x["dt"], reverse=True)

    if all_items_sorted:
        top = all_items_sorted[0]
        top_cat = categorize(top)
        template = template.replace("{{TOP_STORY_CATEGORY_LABEL}}", esc(CATEGORY_LABELS[top_cat]))
        template = template.replace("{{TOP_STORY_TITLE}}", esc(top["title"]))
        template = template.replace(
            "{{TOP_STORY_SUMMARY}}",
            f"The latest official update from {esc(top['source_name'])} — see the full press release for details.",
        )
        template = template.replace("{{TOP_STORY_DATE}}", top["dt"].astimezone(IST).strftime("%B %d, %Y"))
        template = template.replace("{{TOP_STORY_SOURCE_URL}}", top["url"])
        template = template.replace("{{TOP_STORY_SOURCE_NAME}}", esc(top["source_name"]))
    else:
        template = template.replace("{{TOP_STORY_CATEGORY_LABEL}}", esc(CATEGORY_LABELS["announcements"]))
        template = template.replace("{{TOP_STORY_TITLE}}", "No official updates found in this window")
        template = template.replace(
            "{{TOP_STORY_SUMMARY}}",
            "The automated scraper did not find any dated official items in the last 60 days. "
            "Check back after the next scheduled run, or ask for a manually-generated report for a deeper search.",
        )
        template = template.replace("{{TOP_STORY_DATE}}", now_ist.strftime("%B %d, %Y"))
        template = template.replace("{{TOP_STORY_SOURCE_URL}}", "https://www.mahindra.com/news-room/press-release")
        template = template.replace("{{TOP_STORY_SOURCE_NAME}}", "Mahindra Group Newsroom")

    for cat in CATEGORIES:
        template = template.replace("{{" + cat.upper() + "_COUNT}}", str(len(by_category[cat])))

    template = template.replace("{{TOTAL_UPDATES}}", str(total))
    template = template.replace("{{REPORT_GENERATED_ISO}}", now_ist.isoformat())
    template = template.replace("{{REPORT_DATE}}", now_ist.strftime("%b %d, %Y"))
    template = template.replace("{{REPORT_TIME}}", fmt_time_12h(now_ist))
    template = template.replace("{{WINDOW_START}}", window_start_utc.astimezone(IST).strftime("%b %d, %Y"))
    template = template.replace("{{WINDOW_END}}", f"{now_ist.strftime('%b %d, %Y')}, {fmt_time_12h(now_ist)}")
    report_id = f"BCONHUB-{now_ist.strftime('%Y%m%d-%H%M%S')}-AUTO"
    template = template.replace("{{REPORT_ID}}", report_id)

    sources_line = "; ".join(sources_scanned)
    if all_items_sorted:
        top = all_items_sorted[0]
        summary_text = (
            f"This automated run scanned {len(fetchers)} official sources ({sources_line}) for the last "
            f"{WINDOW_DAYS} days and found {total} official update(s). The most recent is “{top['title']}” "
            f"from {top['source_name']} ({top['dt'].astimezone(IST).strftime('%B %d, %Y')})."
        )
    else:
        summary_text = (
            f"This automated run scanned {len(fetchers)} official sources ({sources_line}) for the last "
            f"{WINDOW_DAYS} days and found no dated official items — that's an honest result, not an error."
        )
    template = template.replace("{{EXECUTIVE_SUMMARY}}", esc(summary_text))

    remaining = re.findall(r"\{\{[A-Z_]+\}\}", template)
    if remaining:
        raise RuntimeError(f"Unfilled placeholders remain: {set(remaining)}")

    REPORTS_DIR.mkdir(exist_ok=True)
    filename = f"BCONHUB-Report_{now_ist.strftime('%Y-%m-%d')}_{now_ist.strftime('%H%M%S')}.html"
    out_path = REPORTS_DIR / filename
    out_path.write_text(template, encoding="utf-8")
    print(f"Wrote {out_path} ({total} item(s) found across {len(fetchers)} sources: {sources_line})")


if __name__ == "__main__":
    main()
