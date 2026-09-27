"""PokeChuker FastAPI backend."""
import statistics
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from card_db import autocomplete as card_autocomplete, init_db as init_card_db
from scraper import scrape_ebay, mock_listings, CONDITION_KEYWORDS
from storage import slugify, upsert_listings, load_card, load_portfolio, save_portfolio, list_cards


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_card_db()
    yield


app = FastAPI(title="PokeChuker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USE_MOCK = False  # Flip to True if eBay blocks scraping during dev


def price_stats(prices: list[float]) -> dict:
    if not prices:
        return {"min": None, "max": None, "avg": None, "median": None, "count": 0}
    return {
        "min": round(min(prices), 2),
        "max": round(max(prices), 2),
        "avg": round(statistics.mean(prices), 2),
        "median": round(statistics.median(prices), 2),
        "count": len(prices),
    }


# ---------- Search / Scrape ----------

@app.get("/api/search")
async def search(
    q: str = Query(..., description="Card name / set / number"),
    condition: str = Query("raw", description="Condition key: raw|psa10|psa9|bgs95|cgc10|psa|bgs|cgc"),
    sold: bool = Query(True),
    mock: bool = Query(False),
):
    if condition not in CONDITION_KEYWORDS:
        raise HTTPException(400, f"Unknown condition '{condition}'. Valid: {list(CONDITION_KEYWORDS.keys())}")

    slug = slugify(f"{q}-{condition}")

    try:
        if mock or USE_MOCK:
            listings = mock_listings(q, condition, sold)
        else:
            listings = await scrape_ebay(q, condition, sold)
    except Exception as e:
        raise HTTPException(502, str(e) or type(e).__name__)

    # Persist
    card = upsert_listings(slug, listings)

    prices = [l["price"] for l in listings if l.get("price") is not None]
    stats = price_stats(prices)

    return {
        "query": q,
        "condition": condition,
        "slug": slug,
        "stats": stats,
        "listings": card["listings"],
        "last_updated": card["last_updated"],
    }


# ---------- Autocomplete ----------

@app.get("/api/autocomplete")
async def autocomplete(q: str = Query(..., min_length=2)):
    results = await card_autocomplete(q)
    return results


# ---------- Card history ----------

@app.get("/api/cards")
def get_cards():
    return {"slugs": list_cards()}


@app.get("/api/cards/{slug}")
def get_card(slug: str):
    card = load_card(slug)
    if not card["listings"]:
        raise HTTPException(404, "No data for this card yet — run a search first.")
    prices = [l["price"] for l in card["listings"] if l.get("price") is not None]
    card["stats"] = price_stats(prices)
    return card


# ---------- Portfolio ----------

class PortfolioCardIn(BaseModel):
    name: str
    set_name: Optional[str] = ""
    number: Optional[str] = ""
    condition: str = "raw"
    purchase_price: float
    purchase_date: str  # ISO date string
    quantity: int = 1
    notes: Optional[str] = ""
    slug: Optional[str] = None  # link to card data file


class PortfolioCardUpdate(BaseModel):
    name: Optional[str] = None
    set_name: Optional[str] = None
    number: Optional[str] = None
    condition: Optional[str] = None
    purchase_price: Optional[float] = None
    purchase_date: Optional[str] = None
    quantity: Optional[int] = None
    notes: Optional[str] = None
    slug: Optional[str] = None


@app.get("/api/portfolio")
def get_portfolio():
    portfolio = load_portfolio()
    cards = portfolio["cards"]

    # Enrich with current price data
    enriched = []
    total_value = 0.0
    total_cost = 0.0

    for card in cards:
        entry = dict(card)
        slug = card.get("slug") or slugify(f"{card['name']}-{card.get('set_name','')}-{card['condition']}")
        card_data = load_card(slug)
        listings = [l for l in card_data.get("listings", []) if l.get("sold") and l.get("price") is not None]
        if listings:
            prices = [l["price"] for l in listings[:20]]  # recent 20
            current_price = round(statistics.median(prices), 2)
            entry["current_price"] = current_price
            entry["current_value"] = round(current_price * card["quantity"], 2)
            entry["profit_loss"] = round((current_price - card["purchase_price"]) * card["quantity"], 2)
        else:
            entry["current_price"] = None
            entry["current_value"] = None
            entry["profit_loss"] = None

        cost = card["purchase_price"] * card["quantity"]
        total_cost += cost
        if entry["current_value"] is not None:
            total_value += entry["current_value"]

        entry["cost"] = round(cost, 2)
        enriched.append(entry)

    return {
        "cards": enriched,
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_profit_loss": round(total_value - total_cost, 2),
    }


@app.post("/api/portfolio", status_code=201)
def add_portfolio_card(card_in: PortfolioCardIn):
    portfolio = load_portfolio()
    new_card = card_in.model_dump()
    new_card["id"] = str(uuid.uuid4())
    new_card["added_at"] = datetime.utcnow().isoformat()
    if not new_card.get("slug"):
        new_card["slug"] = slugify(
            f"{card_in.name}-{card_in.set_name or ''}-{card_in.condition}"
        )
    portfolio["cards"].append(new_card)
    save_portfolio(portfolio)
    return new_card


@app.put("/api/portfolio/{card_id}")
def update_portfolio_card(card_id: str, update: PortfolioCardUpdate):
    portfolio = load_portfolio()
    for i, card in enumerate(portfolio["cards"]):
        if card["id"] == card_id:
            for field, val in update.model_dump(exclude_none=True).items():
                portfolio["cards"][i][field] = val
            save_portfolio(portfolio)
            return portfolio["cards"][i]
    raise HTTPException(404, "Card not found in portfolio")


@app.delete("/api/portfolio/{card_id}", status_code=204)
def delete_portfolio_card(card_id: str):
    portfolio = load_portfolio()
    before = len(portfolio["cards"])
    portfolio["cards"] = [c for c in portfolio["cards"] if c["id"] != card_id]
    if len(portfolio["cards"]) == before:
        raise HTTPException(404, "Card not found in portfolio")
    save_portfolio(portfolio)
