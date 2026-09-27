import { useState } from "react";
import { useNavigate } from "react-router-dom";
import ConditionToggle from "../components/ConditionToggle.jsx";
import PriceSummary from "../components/PriceSummary.jsx";
import ListingCard from "../components/ListingCard.jsx";
import PriceGraph from "../components/PriceGraph.jsx";
import SearchAutocomplete from "../components/SearchAutocomplete.jsx";
import { SkeletonCard, SkeletonStats, SkeletonGraph } from "../components/Skeleton.jsx";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [selectedCard, setSelectedCard] = useState(null); // PokéTCG card object
  const [condition, setCondition] = useState("raw");
  const [useMock, setUseMock] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const navigate = useNavigate();

  async function runSearch(q) {
    if (!q?.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const params = new URLSearchParams({ q: q.trim(), condition, mock: useMock });
      const resp = await fetch(`/api/search?${params}`);
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }
      setResult(await resp.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleCardSelect(card) {
    setSelectedCard(card);
    const label = [card.name, card.set_name, card.number].filter(Boolean).join(" ").trim();
    setQuery(label);
    runSearch(label);
  }

  function handleSearch(e) {
    e?.preventDefault();
    runSearch(query);
  }

  const hasResults = result && !loading;

  return (
    <div>
      {/* Search bar */}
      <form onSubmit={handleSearch} className="mb-5">
        <div className="flex gap-2 mb-3">
          <SearchAutocomplete
            value={query}
            onChange={(v) => { setQuery(v); if (!v) setSelectedCard(null); }}
            onSelect={handleCardSelect}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-poke-red hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all duration-150 whitespace-nowrap"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
                Searching
              </span>
            ) : "Search eBay"}
          </button>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <ConditionToggle value={condition} onChange={setCondition} />
          <label className="flex items-center gap-2 text-xs text-poke-muted cursor-pointer select-none">
            <input
              type="checkbox"
              checked={useMock}
              onChange={(e) => setUseMock(e.target.checked)}
              className="accent-poke-blue"
            />
            Offline / mock data
          </label>
        </div>
      </form>

      {/* Selected card preview banner */}
      {selectedCard && !hasResults && (
        <div className="flex items-center gap-4 bg-poke-card border border-poke-border rounded-xl p-4 mb-5 animate-in">
          {selectedCard.image_large && (
            <img
              src={selectedCard.image_large}
              alt={selectedCard.name}
              className="h-28 w-auto object-contain rounded shadow-lg"
            />
          )}
          <div>
            <div className="text-lg font-bold text-gray-100">{selectedCard.name}</div>
            <div className="text-sm text-poke-muted">
              {selectedCard.set_name}{selectedCard.number ? ` · ${selectedCard.number}` : ""}
              {selectedCard.rarity ? ` · ${selectedCard.rarity}` : ""}
            </div>
            {selectedCard.hp && (
              <div className="text-xs text-poke-muted mt-0.5">HP {selectedCard.hp} · {selectedCard.supertype}</div>
            )}
            <div className="text-xs text-poke-muted mt-2">
              Hit <span className="text-white font-semibold">Search eBay</span> to fetch live UK prices
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-xl p-4 mb-5 text-red-300 text-sm">
          <span className="font-semibold">Error:</span> {error}
          {(error.includes("502") || error.includes("blocked")) && (
            <span className="block mt-1 text-red-400/80">
              eBay may be rate-limiting — try again in a moment, or enable Offline mode.
            </span>
          )}
        </div>
      )}

      {/* Skeleton loading */}
      {loading && (
        <div>
          <SkeletonStats />
          <div className="mb-6"><SkeletonGraph /></div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Array.from({ length: 9 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        </div>
      )}

      {/* Results */}
      {hasResults && (
        <div className="animate-in">
          {/* Header row */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              {selectedCard?.image_small && (
                <img
                  src={selectedCard.image_small}
                  alt={selectedCard.name}
                  className="h-10 w-auto object-contain rounded shadow"
                />
              )}
              <div>
                <h2 className="text-lg font-semibold text-gray-100 leading-tight">{result.query}</h2>
                <div className="text-xs text-poke-muted">{result.condition.toUpperCase()} · {result.stats.count} listings</div>
              </div>
            </div>
            <button
              onClick={() => navigate(`/cards/${result.slug}`)}
              className="text-xs text-poke-blue hover:text-blue-300 transition-colors"
            >
              View full history →
            </button>
          </div>

          <PriceSummary stats={result.stats} />

          <div className="mb-6">
            <PriceGraph listings={result.listings} title="Sold Price History" />
          </div>

          <h3 className="text-xs font-semibold text-poke-muted uppercase tracking-wider mb-3">
            All Listings ({result.listings.length})
          </h3>
          {result.listings.length === 0 ? (
            <div className="text-center py-10 text-poke-muted bg-poke-card border border-poke-border rounded-xl">
              <div className="text-3xl mb-2">🔍</div>
              <div>No sold listings found for this query.</div>
              <div className="text-sm mt-1">Try a broader name or a different condition.</div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {result.listings.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && !error && (
        <div className="text-center py-24 text-poke-muted select-none">
          <div className="text-6xl mb-4 opacity-60">⚡</div>
          <div className="text-lg font-medium text-gray-400 mb-2">Search any Pokémon card</div>
          <div className="text-sm">Live UK sold prices · eBay · Flat JSON storage</div>
        </div>
      )}
    </div>
  );
}
