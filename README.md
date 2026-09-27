# PokeChuker

A price tracker for Pokémon trading cards. Search any card, pick a condition (raw or a
specific PSA, BGS or CGC grade), and see what it has actually sold for on eBay UK, with
price statistics and a history chart. Cards you own can be kept in a portfolio.

## Features

- **Sold-price search:** scrapes recent eBay UK sold listings with Playwright and parses
  them with BeautifulSoup. Results are filtered by grade: raw, PSA 10/9, BGS 9.5, CGC 10.
- **Price statistics:** min, max, mean, median and listing count for each search.
- **Price history:** results are stored per card, so the detail page charts prices over
  time (Recharts).
- **Card autocomplete:** backed by a local SQLite cache that is filled on demand from the
  [Pokémon TCG API](https://pokemontcg.io/).
- **Portfolio:** add, edit and remove cards you own through a small REST API.
- **BGS population scraper** (`bgs_scraper/`): a separate async CLI that walks Beckett's
  card-lookup pages with parallel Playwright workers, filters for Pokémon cards, stores
  them in SQLite, supports resume and retries, and exports to CSV.

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn, httpx, Playwright, BeautifulSoup, SQLite |
| Frontend | React 18, React Router, Vite, Tailwind CSS, Recharts, date-fns |
| Storage | JSON files for price history and portfolio; SQLite for the card cache |

## Project structure

```
backend/        FastAPI app: search, autocomplete, card history and portfolio endpoints
frontend/       React + Vite UI: search, card detail with price chart, portfolio
bgs_scraper/    Standalone async CLI for Beckett population data
setup.bat       One-time install of Python, Playwright and Node dependencies
start.bat       Starts the backend (port 8001) and frontend (port 5173)
```

## Getting started (Windows)

Requires Python 3.11+ and Node.js 18+.

```bat
setup.bat
start.bat
```

Then open http://localhost:5173.

On other platforms, run the steps from the batch files by hand:

```bash
cd backend && pip install -r requirements.txt && python -m playwright install chromium
python -m uvicorn main:app --reload --port 8001
# in a second terminal
cd frontend && npm install && npm run dev
```

If eBay blocks scraping during development, set `USE_MOCK = True` in `backend/main.py`, or
pass `mock=true` to `/api/search`, to use generated listings instead.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/search?q=&condition=&sold=` | Scrape and store listings, return stats |
| GET | `/api/autocomplete?q=` | Card name suggestions |
| GET | `/api/cards` / `/api/cards/{slug}` | Stored cards and their price history |
| GET, POST | `/api/portfolio` | List or add portfolio cards |
| PUT, DELETE | `/api/portfolio/{id}` | Update or remove a portfolio card |

Interactive docs are served at http://localhost:8001/docs while the backend is running.

## BGS scraper

```bash
cd bgs_scraper
pip install -r requirements.txt
python main.py --workers 5 --limit 1000
python main.py --export-only      # dump the database to CSV
```

Logging in is optional. To use an account, set the `BGS_USERNAME` and `BGS_PASSWORD`
environment variables; credentials are never stored in the code. Run `python main.py --help`
for all options.

## Notes

This is a personal learning project. Both scrapers wait a randomised 1–3 seconds between
requests. Check a site's terms of service before running a scraper against it.
