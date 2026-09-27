import { useState, useEffect } from "react";
import { format, parseISO } from "date-fns";
import PriceGraph from "../components/PriceGraph.jsx";

const CONDITIONS = ["raw", "psa10", "psa9", "bgs95", "cgc10", "psa8", "psa7", "cgc9"];

function formatDate(s) {
  try { return format(parseISO(s), "dd MMM yyyy"); } catch { return s; }
}

function PLBadge({ value }) {
  if (value === null || value === undefined) return <span className="text-poke-muted">—</span>;
  const pos = value >= 0;
  return (
    <span className={`font-semibold ${pos ? "text-green-400" : "text-red-400"}`}>
      {pos ? "+" : ""}£{value.toFixed(2)}
    </span>
  );
}

function AddCardForm({ onAdd }) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    name: "", set_name: "", number: "", condition: "raw",
    purchase_price: "", purchase_date: today, quantity: 1, notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function update(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.name || !form.purchase_price) return;
    setLoading(true);
    setError(null);
    try {
      const body = { ...form, purchase_price: parseFloat(form.purchase_price), quantity: parseInt(form.quantity) };
      const resp = await fetch("/api/portfolio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) throw new Error((await resp.json()).detail);
      onAdd();
      setForm({ name: "", set_name: "", number: "", condition: "raw", purchase_price: "", purchase_date: today, quantity: 1, notes: "" });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const inputCls = "bg-poke-dark border border-poke-border rounded-md px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-poke-blue w-full";

  return (
    <form onSubmit={handleSubmit} className="bg-poke-card border border-poke-border rounded-lg p-5 mb-6">
      <h3 className="font-semibold text-gray-200 mb-4">Add Card to Portfolio</h3>
      {error && <div className="text-red-400 text-sm mb-3">{error}</div>}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="col-span-2">
          <label className="text-xs text-poke-muted block mb-1">Card Name *</label>
          <input className={inputCls} required placeholder="Charizard Base Set" value={form.name} onChange={(e) => update("name", e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-poke-muted block mb-1">Set</label>
          <input className={inputCls} placeholder="Base Set" value={form.set_name} onChange={(e) => update("set_name", e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-poke-muted block mb-1">Number</label>
          <input className={inputCls} placeholder="4/102" value={form.number} onChange={(e) => update("number", e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-poke-muted block mb-1">Condition *</label>
          <select className={inputCls} value={form.condition} onChange={(e) => update("condition", e.target.value)}>
            {CONDITIONS.map((c) => <option key={c} value={c}>{c.toUpperCase()}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-poke-muted block mb-1">Purchase Price (£) *</label>
          <input className={inputCls} required type="number" step="0.01" min="0" placeholder="0.00" value={form.purchase_price} onChange={(e) => update("purchase_price", e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-poke-muted block mb-1">Purchase Date *</label>
          <input className={inputCls} type="date" value={form.purchase_date} onChange={(e) => update("purchase_date", e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-poke-muted block mb-1">Quantity</label>
          <input className={inputCls} type="number" min="1" value={form.quantity} onChange={(e) => update("quantity", e.target.value)} />
        </div>
        <div className="col-span-2 md:col-span-4">
          <label className="text-xs text-poke-muted block mb-1">Notes</label>
          <input className={inputCls} placeholder="Optional notes…" value={form.notes} onChange={(e) => update("notes", e.target.value)} />
        </div>
      </div>
      <button type="submit" disabled={loading} className="mt-4 px-5 py-2 bg-poke-blue hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-md transition-colors">
        {loading ? "Adding…" : "Add Card"}
      </button>
    </form>
  );
}

function PortfolioRow({ card, onDelete, onExpand, expanded }) {
  return (
    <>
      <tr className="border-t border-poke-border hover:bg-poke-dark/50 transition-colors">
        <td className="py-3 px-4">
          <div className="font-medium text-gray-200">{card.name}</div>
          <div className="text-xs text-poke-muted">{card.set_name} {card.number}</div>
        </td>
        <td className="py-3 px-4 text-sm">
          <span className="bg-gray-800 px-2 py-0.5 rounded text-gray-300">{card.condition.toUpperCase()}</span>
        </td>
        <td className="py-3 px-4 text-sm text-gray-300">{card.quantity}</td>
        <td className="py-3 px-4 text-sm text-poke-muted">{formatDate(card.purchase_date)}</td>
        <td className="py-3 px-4 text-sm font-medium text-gray-300">£{card.purchase_price.toFixed(2)}</td>
        <td className="py-3 px-4 text-sm text-poke-yellow font-semibold">
          {card.current_price != null ? `£${card.current_price.toFixed(2)}` : "—"}
        </td>
        <td className="py-3 px-4 text-sm">
          <PLBadge value={card.profit_loss} />
        </td>
        <td className="py-3 px-4">
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => onExpand(card.id)}
              className="text-xs text-poke-blue hover:underline"
            >
              {expanded ? "Hide" : "Graph"}
            </button>
            <button
              onClick={() => onDelete(card.id)}
              className="text-xs text-red-500 hover:text-red-400"
            >
              Remove
            </button>
          </div>
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-poke-border">
          <td colSpan={8} className="p-4 bg-poke-dark/30">
            <ExpandedGraph slug={card.slug} purchasePrice={card.purchase_price} />
          </td>
        </tr>
      )}
    </>
  );
}

function ExpandedGraph({ slug, purchasePrice }) {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/cards/${slug}`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d) setListings(d.listings || []); })
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <div className="text-poke-muted text-sm text-center py-4">Loading…</div>;
  if (!listings.length) return (
    <p className="text-poke-muted text-sm text-center py-4">
      No price history yet. Search for this card to load data.
    </p>
  );

  return <PriceGraph listings={listings} purchasePrice={purchasePrice} title="Price vs. Your Cost" />;
}

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  async function load() {
    setLoading(true);
    const resp = await fetch("/api/portfolio");
    setPortfolio(await resp.json());
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function handleDelete(id) {
    if (!confirm("Remove this card from your portfolio?")) return;
    await fetch(`/api/portfolio/${id}`, { method: "DELETE" });
    load();
  }

  function toggleExpand(id) {
    setExpanded((prev) => (prev === id ? null : id));
  }

  if (loading) return <div className="text-poke-muted text-center py-20">Loading portfolio…</div>;

  const { cards, total_cost, total_value, total_profit_loss } = portfolio;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-100 mb-6">Portfolio</h1>

      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: "Total Cost", value: `£${total_cost.toFixed(2)}`, color: "text-gray-300" },
          { label: "Current Value", value: `£${total_value.toFixed(2)}`, color: "text-poke-yellow" },
          { label: "Total P&L", value: `${total_profit_loss >= 0 ? "+" : ""}£${total_profit_loss.toFixed(2)}`, color: total_profit_loss >= 0 ? "text-green-400" : "text-red-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-poke-card border border-poke-border rounded-lg p-4 text-center">
            <div className="text-xs text-poke-muted mb-1">{label}</div>
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
          </div>
        ))}
      </div>

      <AddCardForm onAdd={load} />

      {/* Table */}
      {cards.length === 0 ? (
        <div className="text-center py-12 text-poke-muted">
          <div className="text-4xl mb-3">📦</div>
          <div>No cards yet — add your first card above.</div>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-poke-border">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-poke-card text-xs text-poke-muted uppercase tracking-wide">
                <th className="py-3 px-4">Card</th>
                <th className="py-3 px-4">Condition</th>
                <th className="py-3 px-4">Qty</th>
                <th className="py-3 px-4">Bought</th>
                <th className="py-3 px-4">Cost</th>
                <th className="py-3 px-4">Current</th>
                <th className="py-3 px-4">P&L</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {cards.map((card) => (
                <PortfolioRow
                  key={card.id}
                  card={card}
                  onDelete={handleDelete}
                  onExpand={toggleExpand}
                  expanded={expanded === card.id}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
