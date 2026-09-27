"""BGS card-lookup scraper — async Playwright, multiple concurrent workers.

Each worker owns its own browser context and scrapes a sub-range of item_ids.
All workers share one SQLite database protected by an asyncio.Lock.

Flow per worker
---------------
1. Launch Chromium context → (optionally) log in.
2. For each item_id in its sub-range:
   a. GET https://www.beckett.com/grading/card-lookup?item_id=N
   b. If 404 / "no results" → skip, continue.
   c. Extract card fields from rendered DOM (or intercepted JSON API response).
   d. Run Pokémon filter — skip non-Pokémon.
   e. Download front/back images to disk.
   f. INSERT into SQLite (under lock).
   g. Sleep DELAY_MIN–DELAY_MAX seconds.
"""

import asyncio
import random
import re
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page

import config
import database as db
import downloader
import pokemon_filter as pf


# ── Pure helpers (no async I/O) ───────────────────────────────────────────────

def _parse_grade(text: str) -> Optional[float]:
    m = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
    return float(m.group(1)) if m else None


def _absolute_url(base: str, href: str) -> str:
    if href.startswith("http"):
        return href
    return urljoin(base, href)


def _card_id_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] or re.sub(r"[^\w]", "_", url)[-40:]
    return slug


def lookup_url(item_id: int) -> str:
    return f"{config.CARD_LOOKUP_URL}?item_id={item_id}"


def split_id_range(start: int, end: int, n: int) -> list[range]:
    """Divide [start, end] into *n* roughly equal contiguous sub-ranges."""
    total = end - start + 1
    chunk = max(1, total // n)
    ranges = []
    for i in range(n):
        s = start + i * chunk
        e = (s + chunk - 1) if i < n - 1 else end
        if s > end:
            break
        ranges.append(range(s, min(e, end) + 1))
    return ranges


def _grade_label(grade: Optional[float]) -> str:
    if grade is None:
        return ""
    return {
        10.0: "Pristine",      9.5: "Gem Mint",
        9.0:  "Mint",          8.5: "Near Mint-Mint+",
        8.0:  "Near Mint-Mint",7.5: "Near Mint+",
        7.0:  "Near Mint",     6.5: "Excellent-Near Mint+",
        6.0:  "Excellent-Near Mint", 5.5: "Excellent+",
        5.0:  "Excellent",     4.5: "Very Good-Excellent+",
        4.0:  "Very Good-Excellent", 3.5: "Very Good+",
        3.0:  "Very Good",     2.5: "Good+",
        2.0:  "Good",          1.5: "Fair",
        1.0:  "Poor",
    }.get(grade, str(grade))


def _extract_from_api(data: dict, url: str, item_id: Optional[int]) -> dict:
    """Map a captured BGS JSON API payload to our schema."""
    resolved_id = item_id or data.get("submissionId") or data.get("id")
    card_id = str(resolved_id) if resolved_id else _card_id_from_url(url)
    grades  = data.get("grades", data.get("subGrades", {}))
    try:
        overall = float(data.get("grade") or data.get("overallGrade") or 0)
    except (TypeError, ValueError):
        overall = None
    return {
        "item_id":         item_id,
        "card_id":         card_id,
        "name":            data.get("name") or data.get("cardName") or "Unknown",
        "set_name":        data.get("set")  or data.get("setName")  or "",
        "year":            str(data.get("year") or ""),
        "card_number":     str(data.get("cardNumber") or data.get("number") or ""),
        "category":        data.get("sport") or data.get("category") or "",
        "front_image_url": data.get("frontImage") or data.get("imageUrl") or "",
        "back_image_url":  data.get("backImage") or "",
        "centering":       _parse_grade(str(grades.get("centering", ""))),
        "corners":         _parse_grade(str(grades.get("corners",   ""))),
        "edges":           _parse_grade(str(grades.get("edges",     ""))),
        "surface":         _parse_grade(str(grades.get("surface",   ""))),
        "overall_grade":   overall,
        "grade_label":     data.get("gradeLabel") or data.get("label") or _grade_label(overall),
        "source_url":      url,
    }


# ── Async Playwright helpers ───────────────────────────────────────────────────

async def _text(page: Page, selector: str, default: str = "") -> str:
    el = await page.query_selector(selector)
    return (await el.inner_text()).strip() if el else default


async def _attr(page: Page, selector: str, attr: str) -> str:
    el = await page.query_selector(selector)
    val = await el.get_attribute(attr) if el else None
    return (val or "").strip()


async def _is_not_found(page: Page, http_status: int) -> bool:
    if http_status in (404, 410):
        return True
    if await page.query_selector(
        ".not-found, .no-results, .error-page, "
        "[data-testid='not-found'], [data-testid='no-results']"
    ):
        return True
    try:
        body = await page.inner_text("body")
        return any(p in body.lower() for p in [
            "no card found", "no results found", "card not found",
            "item not found", "page not found", "does not exist",
        ])
    except Exception:
        return False


async def extract_card(
    page: Page,
    url: str,
    item_id: Optional[int] = None,
    api_data: Optional[dict] = None,
) -> Optional[dict]:
    if api_data:
        return _extract_from_api(api_data, url, item_id)

    sel = config.SELECTORS

    name = await _text(page, sel["card_name"])
    if not name:
        name = (await page.title()).split("|")[0].strip()

    category    = await _text(page, sel["category"])
    overall_raw = await _text(page, sel["overall_grade"])
    overall     = _parse_grade(overall_raw)
    grade_label = await _text(page, sel["grade_label"]) or _grade_label(overall)

    centering = _parse_grade(await _text(page, sel["centering"]))
    corners   = _parse_grade(await _text(page, sel["corners"]))
    edges     = _parse_grade(await _text(page, sel["edges"]))
    surface   = _parse_grade(await _text(page, sel["surface"]))

    front_url = await _attr(page, sel["front_image"], "src") or await _attr(page, sel["front_image"], "data-src")
    back_url  = await _attr(page, sel["back_image"],  "src") or await _attr(page, sel["back_image"],  "data-src")
    front_url = _absolute_url(url, front_url) if front_url else ""
    back_url  = _absolute_url(url, back_url)  if back_url  else ""

    card_id = str(item_id) if item_id else _card_id_from_url(url)

    return {
        "item_id":         item_id,
        "card_id":         card_id,
        "name":            name or "Unknown",
        "set_name":        await _text(page, sel["set_name"]),
        "year":            await _text(page, sel["year"]),
        "card_number":     await _text(page, sel["card_number"]),
        "category":        category,
        "front_image_url": front_url,
        "back_image_url":  back_url,
        "centering":       centering,
        "corners":         corners,
        "edges":           edges,
        "surface":         surface,
        "overall_grade":   overall,
        "grade_label":     grade_label,
        "source_url":      url,
    }


# ── Login ─────────────────────────────────────────────────────────────────────

async def login(page: Page) -> bool:
    if not (config.BGS_USERNAME and config.BGS_PASSWORD):
        return False
    await page.goto(config.LOGIN_URL, wait_until="domcontentloaded", timeout=config.PAGE_TIMEOUT)
    await page.wait_for_timeout(1_500)
    sel = config.SELECTORS
    email_el  = await page.query_selector(sel["login_email"])
    pwd_el    = await page.query_selector(sel["login_password"])
    submit_el = await page.query_selector(sel["login_submit"])
    if not (email_el and pwd_el and submit_el):
        return False
    await email_el.fill(config.BGS_USERNAME)
    await pwd_el.fill(config.BGS_PASSWORD)
    await submit_el.click()
    await page.wait_for_load_state("networkidle", timeout=config.PAGE_TIMEOUT)
    return "login" not in page.url.lower()


# ── Worker ────────────────────────────────────────────────────────────────────

async def scrape_worker(
    worker_id: int,
    id_range: Iterable[int],
    db_lock: asyncio.Lock,
    pbar,                        # tqdm bar for this worker
    shared: dict,                # {"stop": False} — set True by main when limit hit
    proxy: Optional[str] = None,
    do_login: bool = True,
) -> dict:
    """
    Scrape a contiguous sub-range of item_ids.

    Returns a stats dict: {saved, skipped, not_found, failed}.
    """
    stats = {"saved": 0, "skipped": 0, "not_found": 0, "failed": 0}
    api_cache: dict[str, dict] = {}

    async with async_playwright() as pw:
        launch_opts: dict = {"headless": config.HEADLESS}
        if proxy:
            launch_opts["proxy"] = {"server": proxy}

        browser = await pw.chromium.launch(**launch_opts)
        context = await browser.new_context(
            locale="en-GB",
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        async def on_response(response) -> None:
            if "json" not in response.headers.get("content-type", ""):
                return
            if not any(k in response.url for k in ["/api/", "/grading/", "beckett.com"]):
                return
            try:
                data = await response.json()
                if isinstance(data, (dict, list)):
                    api_cache[response.url] = data
            except Exception:
                pass

        context.on("response", on_response)
        page = await context.new_page()

        if do_login and config.BGS_USERNAME:
            await login(page)

        for item_id in id_range:
            if shared.get("stop"):
                break

            # ── Resume: skip already-scraped ──────────────────────────────────
            async with db_lock:
                already = db.item_id_exists(item_id)
            if already:
                pbar.update(1)
                continue

            url = lookup_url(item_id)
            http_status = 200

            # ── Fetch page ────────────────────────────────────────────────────
            try:
                resp = await page.goto(
                    url, wait_until="domcontentloaded", timeout=config.PAGE_TIMEOUT
                )
                if resp:
                    http_status = resp.status
                await page.wait_for_timeout(1_500)
            except Exception as exc:
                async with db_lock:
                    db.log_error(url, str(exc), card_id=str(item_id))
                stats["failed"] += 1
                _update_pbar(pbar, worker_id, stats)
                await asyncio.sleep(random.uniform(config.DELAY_MIN, config.DELAY_MAX))
                continue

            # ── 404 / no result ───────────────────────────────────────────────
            if await _is_not_found(page, http_status):
                stats["not_found"] += 1
                pbar.update(1)
                await asyncio.sleep(random.uniform(config.DELAY_MIN, config.DELAY_MAX))
                continue

            # ── Extract ───────────────────────────────────────────────────────
            data = await extract_card(
                page, url, item_id=item_id, api_data=api_cache.get(url)
            )
            if not data or not data.get("name") or data["name"] == "Unknown":
                async with db_lock:
                    db.log_error(url, "Could not extract card name", card_id=str(item_id))
                stats["failed"] += 1
                _update_pbar(pbar, worker_id, stats)
                await asyncio.sleep(random.uniform(config.DELAY_MIN, config.DELAY_MAX))
                continue

            # ── Pokémon filter ────────────────────────────────────────────────
            if not pf.is_pokemon_card(
                data["name"], data.get("category", ""), data.get("set_name", "")
            ):
                stats["skipped"] += 1
                _update_pbar(pbar, worker_id, stats)
                await asyncio.sleep(random.uniform(config.DELAY_MIN, config.DELAY_MAX))
                continue

            # ── Download images (offloaded to thread — avoids blocking loop) ──
            front_path, back_path = await asyncio.to_thread(
                downloader.download_card_images,
                data["card_id"], data["front_image_url"], data["back_image_url"],
            )
            data["front_image_path"] = front_path
            data["back_image_path"]  = back_path

            # ── Save ──────────────────────────────────────────────────────────
            async with db_lock:
                db.insert_card(data)
                shared["saved"] = shared.get("saved", 0) + 1
                if shared.get("limit") and shared["saved"] >= shared["limit"]:
                    shared["stop"] = True

            stats["saved"] += 1
            _update_pbar(pbar, worker_id, stats, grade=data.get("overall_grade"))

            await asyncio.sleep(random.uniform(config.DELAY_MIN, config.DELAY_MAX))

        await browser.close()

    return stats


def _update_pbar(pbar, worker_id: int, stats: dict, grade=None) -> None:
    pbar.update(1)
    kw: dict = {"W": worker_id + 1, "ok": stats["saved"], "skip": stats["skipped"]}
    if stats["failed"]:
        kw["err"] = stats["failed"]
    if grade is not None:
        kw["grade"] = grade
    pbar.set_postfix(**kw)
