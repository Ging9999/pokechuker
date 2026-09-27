import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { format, parseISO } from "date-fns";
import PriceSummary from "../components/PriceSummary.jsx";
import PriceGraph from "../components/PriceGraph.jsx";
import ListingCard from "../components/ListingCard.jsx";
import ConditionToggle from "../components/ConditionToggle.jsx";

function formatDate(s) {
  try { return format(parseISO(s), "dd MMM yyyy HH:mm"); } catch { return s; }
}

const CONDITION_LABELS = {
  raw: "Raw", psa10: "PSA 10", psa9: "PSA 9", bgs95: "BGS 9.5", cgc10: "CGC 10",
};

export default function CardDetailPage() {
  const { slug } = useParams();
  const [card, setCard] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetch(`/api/cards/${slug}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setCard)
      .catch((e) => setError(e.message));
  }, [slug]);

  if (error) return (
    <div className="text-center py-20">
      <div className="text-red-400 mb-4">{error}</div>
      <Link to="/" className="text-poke-blue hover:underline text-sm">← Back to Search</Link>
    </div>
  );

  if (!card) return <div className="text-poke-muted text-center py-20">Loading…</div>;

  const listings = card.listings || [];
  const shown = filter === "all" ? listings : listings.filter((l) => l.sold === (filter === "sold"));

  // Group by condition for stats breakdown
  const condGroups = {};
  listings.forEach((l) => {
    const cond = l.condition || "Unknown";
    if (!condGroups[cond]) condGroups[cond] = [];
    condGroups[cond].push(l.price);
  });

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Link to="/" className="text-poke-muted hover:text-white text-sm">← Back</Link>
        <h1 className="text-xl font-bold text-gray-100">{slug.replace(/-/g, " ")}</h1>
        <span className="text-xs text-poke-muted ml-auto">
          Last updated: {formatDate(card.last_updated)}
        </span>
      </div>

      <PriceSummary stats={card.stats} />

      <div className="mb-6">
        <PriceGraph listings={listings} title="Full Price History" />
      </div>

      {/* Condition breakdown */}
      {Object.keys(condGroups).length > 1 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Condition Breakdown
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(condGroups).map(([cond, prices]) => {
              const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
              return (
                <div key={cond} className="bg-poke-card border border-poke-border rounded-lg p-3">
                  <div className="text-xs text-poke-muted mb-1">{cond}</div>
                  <div className="font-bold text-poke-yellow">£{avg.toFixed(2)}</div>
                  <div className="text-xs text-poke-muted">{prices.length} listings</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Listing filter */}
      <div className="flex gap-2 mb-4">
        {["all", "sold", "active"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-md text-sm capitalize transition-colors ${
              filter === f ? "bg-poke-blue text-white" : "text-poke-muted hover:text-white"
            }`}
          >
            {f}
          </button>
        ))}
        <span className="ml-auto text-sm text-poke-muted self-center">{shown.length} listings</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {shown.map((l) => <ListingCard key={l.id} listing={l} />)}
      </div>

      {shown.length === 0 && (
        <div className="text-center py-8 text-poke-muted text-sm">No listings for this filter.</div>
      )}
    </div>
  );
}
