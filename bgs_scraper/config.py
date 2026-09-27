"""BGS Pop Report Scraper — Configuration.

Edit values here, or override via CLI args / environment variables.
"""
import os

# ── Auth ──────────────────────────────────────────────────────────────────────
BGS_USERNAME: str = os.getenv("BGS_USERNAME", "")  # set in env or here
BGS_PASSWORD: str = os.getenv("BGS_PASSWORD", "")

# ── Target URLs ───────────────────────────────────────────────────────────────
LOGIN_URL       = "https://www.beckett.com/login"
POP_REPORT_URL  = "https://www.beckett.com/grading/pop-report"
CARD_LOOKUP_URL = "https://www.beckett.com/grading/card-lookup"  # append ?item_id=N

# ── ID range ──────────────────────────────────────────────────────────────────
# Beckett item_id appears to be a monotonically incrementing integer.
# Override via --start-id / --end-id CLI args.
START_ID: int = 1
END_ID:   int = 500_000

# ── Timing ────────────────────────────────────────────────────────────────────
DELAY_MIN: float = 2.0   # seconds between requests (one per ID)
DELAY_MAX: float = 3.0

# ── Storage ───────────────────────────────────────────────────────────────────
DB_PATH    = "bgs_cards.db"
IMAGES_DIR = "images"
CSV_OUTPUT = "cards.csv"

# ── Browser ───────────────────────────────────────────────────────────────────
HEADLESS: bool = True
PAGE_TIMEOUT: int = 30_000   # ms

# ── Limits ────────────────────────────────────────────────────────────────────
MAX_CARDS: int | None = None   # None = unlimited

# ── Proxies ───────────────────────────────────────────────────────────────────
# Populated at runtime from --proxy-file; format: http://user:pass@host:port
PROXY_LIST: list[str] = []

# ── Pokémon filter ────────────────────────────────────────────────────────────
# Set False to scrape all sports (useful for testing selectors without filtering)
POKEMON_ONLY: bool = True

# URL query param injected into START_URL to request the Pokémon/TCG category.
# Not used for ID-based scraping; kept for reference if switching to link crawl.
# Common candidates: sport=pokemon, category=pokemon, type=tcg
SPORT_URL_PARAM: dict[str, str] = {"sport": "pokemon"}

# Category / sport field values that confirm a card IS Pokémon.
# Matched case-insensitively against whatever BGS puts in their category field.
POKEMON_CATEGORIES: list[str] = [
    "pokemon", "pokémon",
    "trading card game", "trading card games", "tcg",
    "non-sport", "nintendo",
]

# Fast keyword whitelist — card name must contain one of these (case-insensitive).
# If none match, the full PokéTCG API name list is checked as a fallback.
POKEMON_KEYWORDS: list[str] = [
    "Pokemon", "Pokémon",
    # Gen 1
    "Bulbasaur", "Ivysaur", "Venusaur", "Charmander", "Charmeleon", "Charizard",
    "Squirtle", "Wartortle", "Blastoise", "Caterpie", "Metapod", "Butterfree",
    "Pikachu", "Raichu", "Nidoking", "Nidoqueen", "Clefairy", "Jigglypuff",
    "Mewtwo", "Mew", "Gengar", "Gyarados", "Lapras", "Snorlax", "Eevee",
    "Vaporeon", "Jolteon", "Flareon", "Espeon", "Umbreon", "Leafeon", "Glaceon",
    "Sylveon", "Articuno", "Zapdos", "Moltres", "Dragonite", "Dratini",
    "Aerodactyl", "Alakazam", "Machamp", "Golem", "Arcanine", "Ninetales",
    # Gen 2
    "Typhlosion", "Feraligatr", "Meganium", "Lugia", "Ho-Oh", "Celebi",
    "Tyranitar", "Heracross", "Scizor", "Espeon", "Umbreon", "Suicune",
    "Raikou", "Entei",
    # Gen 3
    "Blaziken", "Swampert", "Sceptile", "Gardevoir", "Metagross", "Salamence",
    "Flygon", "Absol", "Rayquaza", "Kyogre", "Groudon", "Latias", "Latios",
    # Gen 4
    "Lucario", "Garchomp", "Gallade", "Togekiss", "Glaceon", "Leafeon",
    "Dialga", "Palkia", "Giratina", "Darkrai", "Arceus",
    # Gen 5
    "Zoroark", "Zekrom", "Reshiram", "Kyurem", "Hydreigon", "Volcarona",
    # Gen 6+
    "Greninja", "Talonflame", "Hawlucha", "Xerneas", "Yveltal",
    "Incineroar", "Mimikyu", "Lunala", "Solgaleo", "Necrozma",
    "Zacian", "Eternatus", "Calyrex", "Urshifu",
    "Koraidon", "Miraidon",
    # TCG-specific suffixes that appear in BGS card names
    "-GX", "-EX", " VMAX", " VSTAR", " V ", " ex",
]

# Path to cache the full PokéTCG API name list after first fetch.
# Delete this file to force a refresh.
POKETCG_NAMES_CACHE: str = "pokemon_names.json"

# ── CSS / XPath selectors ─────────────────────────────────────────────────────
# These are best-effort based on BGS's Next.js layout.
# Run with HEADLESS=False and inspect DevTools if selectors stop matching.
SELECTORS = {
    # Login form
    "login_email":    "input[type='email'], input[name='email'], #email",
    "login_password": "input[type='password'], input[name='password'], #password",
    "login_submit":   "button[type='submit'], input[type='submit']",

    # Pop report search/filter
    "search_input":   "input[placeholder*='card'], input[placeholder*='search'], input[type='search']",

    # Set/category links in pop report listing
    "set_links":      "a[href*='pop-report'], a[href*='/pop/'], table a",

    # Card table rows (pop report results)
    "card_rows":      "table tbody tr",

    # Within a card detail / submission row
    "category":      ".sport, .category, [data-testid='sport'], [data-testid='category'], "
                     "select[name='sport'] option[selected], .breadcrumb li:nth-child(2)",
    "card_name":     "h1, h2, .card-name, [data-testid='card-name']",
    "set_name":      ".set-name, [data-testid='set'], td:nth-child(2)",
    "year":          ".year, [data-testid='year'], td:nth-child(3)",
    "card_number":   ".card-number, [data-testid='number'], td:nth-child(4)",
    "overall_grade": ".grade, .final-grade, td.grade",
    "grade_label":   ".grade-label, .grade-name",

    # Sub-grades (shown on individual submission detail pages)
    "centering": "[data-label='Centering'], td[data-grade='centering'], .subgrade-centering",
    "corners":   "[data-label='Corners'],   td[data-grade='corners'],   .subgrade-corners",
    "edges":     "[data-label='Edges'],     td[data-grade='edges'],     .subgrade-edges",
    "surface":   "[data-label='Surface'],   td[data-grade='surface'],   .subgrade-surface",

    # Card images on detail page
    "front_image": "img[alt*='front' i], img[alt*='Front'], .card-front img, .card-images img:first-child",
    "back_image":  "img[alt*='back'  i], img[alt*='Back'],  .card-back  img, .card-images img:last-child",

    # Pagination
    "next_page": "a[rel='next'], [aria-label='Next page'], .pagination .next a, li.next > a",
}
