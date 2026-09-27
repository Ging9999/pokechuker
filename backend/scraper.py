import asyncio
import hashlib
import random
import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

CONDITION_KEYWORDS = {
    "raw": "",
    "psa": "PSA",
    "psa10": "PSA 10",
    "psa9": "PSA 9",
    "bgs": "BGS",
    "bgs95": "BGS 9.5",
    "cgc": "CGC",
    "cgc10": "CGC 10",
}


def build_ebay_url(query: str, condition_key: str, sold: bool = True) -> str:
    condition_suffix = CONDITION_KEYWORDS.get(condition_key, "")
    full_query = f"{query} {condition_suffix}".strip() if condition_suffix else query
    encoded = full_query.replace(" ", "+")
    base = f"https://www.ebay.co.uk/sch/i.html?_nkw={encoded}&_sop=13"
    if sold:
        base += "&LH_Sold=1&LH_Complete=1&LH_PrefLoc=1"
    return base


def listing_id(url: str) -> str:
    m = re.search(r"/itm/(\d+)", url)
    if m:
        return m.group(1)
    return hashlib.md5(url.encode()).hexdigest()[:12]


def parse_price(text: str) -> Optional[float]:
    text = text.replace(",", "")
    m = re.search(r"[\d]+\.?\d*", text)
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


def parse_date(text: str) -> Optional[str]:
    try:
        cleaned = re.sub(r"^(Sold\s+)", "", text.strip(), flags=re.IGNORECASE)
        dt = dateparser.parse(cleaned, dayfirst=True)
        if dt:
            return dt.isoformat()
    except Exception:
        pass
    return None


def parse_listings(html: str, sold: bool = True) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results = []

    # eBay's current markup uses li[id^="item"] with data-listingid attribute
    items = soup.select('li[id^="item"][data-listingid]')
    for item in items:
        ebay_id = item.get("data-listingid", "")

        # Title — first primary text span, skip sponsored/footer items
        title_el = item.select_one("span.su-styled-text.primary.default")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        # Price
        price_el = item.select_one("span.s-card__price")
        price_text = price_el.get_text(strip=True) if price_el else ""
        if "to" in price_text.lower():
            price_text = price_text.split("to")[0]
        price = parse_price(price_text)
        if price is None:
            continue

        # URL — build from item ID to avoid tracking junk
        url = f"https://www.ebay.co.uk/itm/{ebay_id}" if ebay_id else ""
        # Fallback: first link inside the item that points to /itm/
        if not url:
            link_el = item.select_one('a[href*="/itm/"]')
            if link_el:
                url = link_el["href"].split("?")[0]

        # Sold date
        date_str = None
        if sold:
            caption_el = item.select_one("div.s-card__caption span")
            if caption_el:
                date_str = parse_date(caption_el.get_text(strip=True))

        # Condition
        cond_el = item.select_one("div.s-card__subtitle span.su-styled-text")
        condition = cond_el.get_text(strip=True) if cond_el else ""

        # Image — new layout uses direct src (no lazy load)
        img_el = item.select_one("img.s-card__image")
        image = ""
        if img_el:
            raw = img_el.get("src", "")
            if raw and "gif" not in raw and len(raw) > 20:
                image = raw

        results.append({
            "id": ebay_id or listing_id(url),
            "title": title,
            "price": price,
            "date": date_str or datetime.utcnow().isoformat(),
            "url": url,
            "condition": condition,
            "image": image,
            "sold": sold,
        })

    return results


def _fetch_html_sync(url: str) -> str:
    """Sync Playwright in its own thread — avoids event loop conflict with uvicorn."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            locale="en-GB",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(2_000)
        html = page.content()
        browser.close()
        return html


_thread_pool = None

async def _fetch_html_playwright(url: str) -> str:
    """Run sync Playwright in a thread so it gets its own event loop."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(max_workers=2)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_thread_pool, _fetch_html_sync, url)


async def scrape_ebay(query: str, condition_key: str = "raw", sold: bool = True) -> list[dict]:
    url = build_ebay_url(query, condition_key, sold)
    delay = random.uniform(1.0, 2.5)
    await asyncio.sleep(delay)
    html = await _fetch_html_playwright(url)
    return parse_listings(html, sold)


# --- Mock data for development / when eBay blocks ---
def mock_listings(query: str, condition_key: str, sold: bool = True) -> list[dict]:
    from datetime import timedelta

    base_prices = {"raw": 15.0, "psa10": 85.0, "psa9": 45.0, "bgs95": 70.0, "cgc10": 75.0}
    base = base_prices.get(condition_key, 20.0)

    listings = []
    for i in range(20):
        price = round(base * random.uniform(0.8, 1.3), 2)
        days_ago = random.randint(1, 90)
        date = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()
        cond_label = condition_key.upper() if condition_key != "raw" else "Used"
        uid = hashlib.md5(f"{query}{condition_key}{i}".encode()).hexdigest()[:12]
        listings.append({
            "id": uid,
            "title": f"{query} Pokemon Card {cond_label} #{i+1}",
            "price": price,
            "date": date,
            "url": f"https://www.ebay.co.uk/itm/{uid}",
            "condition": cond_label,
            "image": "",
            "sold": sold,
        })
    return sorted(listings, key=lambda x: x["date"], reverse=True)
