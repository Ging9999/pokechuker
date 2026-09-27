#!/usr/bin/env python3
"""BGS Card-Lookup Scraper — async CLI entry point.

Iterates https://www.beckett.com/grading/card-lookup?item_id=N across a
configurable range, running N parallel Playwright workers simultaneously.

Usage examples
--------------
  python main.py                             # 1 worker, IDs 1–500000
  python main.py --workers 10               # 10 parallel workers
  python main.py --workers 10 --start-id 1 --end-id 500000
  python main.py --workers 5  --limit 10000 # stop after 10k Pokémon cards saved
  python main.py --resume                    # auto-resume from highest item_id in DB
  python main.py --start-id 50000           # begin at a specific ID
  python main.py --proxy-file proxies.txt   # one proxy per line, round-robined
  python main.py --no-headless              # show browser windows (debug selectors)
  python main.py --retry-errors             # re-attempt IDs in the errors table
  python main.py --no-pokemon-filter        # save all sports, not just Pokémon
  python main.py --export-only              # dump current DB to CSV and exit
"""

import argparse
import asyncio
import re
import time
from pathlib import Path

from tqdm import tqdm

import config
import database as db
import pokemon_filter as pf
import scraper as sc


# ── Bar colours cycled across workers ────────────────────────────────────────
_COLOURS = ["cyan", "green", "yellow", "magenta", "blue", "white", "red"]


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Scrape BGS card-lookup IDs into SQLite + CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--workers",    type=int, default=1,
                   help="Number of parallel Playwright browser workers")
    p.add_argument("--start-id",  type=int, default=None,
                   help="First item_id to fetch (default: config.START_ID)")
    p.add_argument("--end-id",    type=int, default=None,
                   help="Last item_id to fetch  (default: config.END_ID)")
    p.add_argument("--resume",    action="store_true",
                   help="Auto-resume from highest item_id in DB + 1")
    p.add_argument("--limit",     type=int, default=None,
                   help="Stop after N Pokémon cards *saved* across all workers")
    p.add_argument("--proxy-file", type=str, default=None,
                   help="File with proxies, one per line (round-robined across workers)")
    p.add_argument("--no-headless", action="store_true",
                   help="Show browser windows (useful for debugging selectors)")
    p.add_argument("--no-login",    action="store_true",
                   help="Skip Beckett login even if credentials are configured")
    p.add_argument("--retry-errors", action="store_true",
                   help="Re-attempt item_ids found in the errors table")
    p.add_argument("--no-pokemon-filter", action="store_true",
                   help="Disable Pokémon-only filter — save every sport")
    p.add_argument("--export-only", action="store_true",
                   help="Export existing DB to CSV and exit without scraping")
    return p.parse_args()


def load_proxies(proxy_file: str | None) -> list[str]:
    if not proxy_file:
        return []
    path = Path(proxy_file)
    if not path.exists():
        print(f"[warn] Proxy file not found: {proxy_file}")
        return []
    proxies = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    print(f"[proxy] Loaded {len(proxies)} proxies")
    return proxies


# ── Async orchestrator ────────────────────────────────────────────────────────

async def _run(
    id_ranges: list[range],
    proxies:   list[str],
    limit:     int | None,
    do_login:  bool,
) -> list[dict]:
    """Create per-worker progress bars, launch workers, await all."""
    n = len(id_ranges)
    db_lock = asyncio.Lock()

    # Shared mutable state (single asyncio thread — no race conditions)
    shared: dict = {"stop": False, "saved": 0, "limit": limit}

    # One tqdm bar per worker, stacked vertically
    pbars = [
        tqdm(
            total=len(id_ranges[i]),
            desc=f"W{i + 1:02d}",
            position=i,
            leave=True,
            unit="id",
            colour=_COLOURS[i % len(_COLOURS)],
            dynamic_ncols=True,
        )
        for i in range(n)
    ]

    tasks = [
        sc.scrape_worker(
            worker_id=i,
            id_range=id_ranges[i],
            db_lock=db_lock,
            pbar=pbars[i],
            shared=shared,
            proxy=proxies[i % len(proxies)] if proxies else None,
            do_login=do_login,
        )
        for i in range(n)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for pbar in pbars:
        pbar.close()

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    # ── Apply CLI overrides to config ─────────────────────────────────────────
    if args.no_headless:
        config.HEADLESS = False
    if args.no_pokemon_filter:
        config.POKEMON_ONLY = False

    proxies = load_proxies(args.proxy_file)

    # ── Init DB ───────────────────────────────────────────────────────────────
    db.init_db()

    # ── Export-only shortcut ──────────────────────────────────────────────────
    if args.export_only:
        n = db.export_csv()
        print(f"Exported {n} rows → {config.CSV_OUTPUT}")
        return

    # ── Pre-load Pokémon name cache ───────────────────────────────────────────
    if config.POKEMON_ONLY:
        name_count = pf.warm_cache()
        print(f"[filter] Pokémon-only ON — {name_count:,} names loaded")
    else:
        print("[filter] Pokémon-only OFF — all sports will be saved")

    # ── Determine ID list ─────────────────────────────────────────────────────
    if args.retry_errors:
        error_urls = db.get_failed_urls()
        id_list: list[int] = []
        for u in error_urls:
            m = re.search(r"item_id=(\d+)", u)
            if m:
                id_list.append(int(m.group(1)))
        if not id_list:
            print("[retry] No errored item_id URLs in errors table. Nothing to do.")
            return
        print(f"[retry] {len(id_list):,} errored IDs queued")
        # Distribute the error IDs across workers as lists (workers accept any iterable)
        n_workers = min(args.workers, len(id_list))
        chunk = max(1, len(id_list) // n_workers)
        id_ranges: list = [
            id_list[i * chunk : (i + 1) * chunk] if i < n_workers - 1
            else id_list[i * chunk :]
            for i in range(n_workers)
        ]
    else:
        start_id = args.start_id if args.start_id is not None else config.START_ID
        end_id   = args.end_id   if args.end_id   is not None else config.END_ID

        if args.resume:
            last = db.get_last_scraped_id()
            if last >= start_id:
                print(f"[resume] Last saved item_id = {last:,} → resuming from {last + 1:,}")
                start_id = last + 1

        if start_id > end_id:
            print(f"[done] start_id ({start_id:,}) > end_id ({end_id:,}). Nothing to do.")
            return

        n_workers  = min(args.workers, end_id - start_id + 1)
        id_ranges  = sc.split_id_range(start_id, end_id, n_workers)
        total_ids  = end_id - start_id + 1
        est_hrs    = total_ids / (n_workers * (3600 / ((config.DELAY_MIN + config.DELAY_MAX) / 2)))

        print(
            f"[range] item_id {start_id:,} → {end_id:,}  "
            f"({total_ids:,} IDs, {n_workers} workers, "
            f"~{est_hrs:.1f}h estimated)"
        )
        for i, r in enumerate(id_ranges):
            print(f"  W{i + 1:02d}: {r.start:,} → {r.stop - 1:,}  ({len(r):,} IDs)")

    # ── Run ───────────────────────────────────────────────────────────────────
    t_start = time.monotonic()
    print()  # blank line before tqdm bars

    results = asyncio.run(
        _run(
            id_ranges=id_ranges,
            proxies=proxies,
            limit=args.limit,
            do_login=not args.no_login,
        )
    )

    # ── Aggregate stats ───────────────────────────────────────────────────────
    totals: dict[str, int] = {"saved": 0, "skipped": 0, "not_found": 0, "failed": 0}
    for r in results:
        if isinstance(r, dict):
            for k in totals:
                totals[k] += r.get(k, 0)
        elif isinstance(r, Exception):
            print(f"[err] Worker raised exception: {r}")

    exported = db.export_csv()

    elapsed = time.monotonic() - t_start
    mins, secs = divmod(int(elapsed), 60)
    ids_processed = sum(totals.values())
    rate = ids_processed / max(elapsed, 1)

    print(f"\n{'=' * 54}")
    print(f"  Workers                 : {n_workers}")
    print(f"  Pokémon cards saved     : {totals['saved']:,}")
    print(f"  Skipped (non-Pokémon)   : {totals['skipped']:,}")
    print(f"  Not found (404/empty)   : {totals['not_found']:,}")
    print(f"  Errors                  : {totals['failed']:,}")
    print(f"  IDs processed           : {ids_processed:,}")
    print(f"  Rate                    : {rate:.1f} IDs/s  ({rate * 3600:,.0f}/hr)")
    print(f"  Time taken              : {mins}m {secs}s")
    print(f"  CSV exported            : {exported:,} rows → {config.CSV_OUTPUT}")
    print(f"  DB                      : {config.DB_PATH}")
    print("=" * 54)


if __name__ == "__main__":
    main()
