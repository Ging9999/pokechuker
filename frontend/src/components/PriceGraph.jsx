import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { format, parseISO, subDays } from "date-fns";
import { useMemo, useState } from "react";

const RANGES = [
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
  { label: "180d", days: 180 },
  { label: "All", days: null },
];

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-poke-card border border-poke-border rounded-lg p-3 text-sm shadow-xl">
      <div className="text-poke-muted mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="font-bold" style={{ color: p.color }}>
          {p.name}: £{Number(p.value).toFixed(2)}
        </div>
      ))}
    </div>
  );
}

export default function PriceGraph({ listings, purchasePrice = null, title = "Price History" }) {
  const [range, setRange] = useState("90d");

  const data = useMemo(() => {
    const rangeObj = RANGES.find((r) => r.label === range);
    const cutoff = rangeObj?.days ? subDays(new Date(), rangeObj.days) : null;

    const filtered = listings
      .filter((l) => l.sold && l.price != null && l.date)
      .filter((l) => {
        if (!cutoff) return true;
        try {
          return parseISO(l.date) >= cutoff;
        } catch {
          return false;
        }
      })
      .sort((a, b) => a.date.localeCompare(b.date));

    return filtered.map((l) => ({
      date: (() => {
        try { return format(parseISO(l.date), "dd MMM"); } catch { return l.date; }
      })(),
      price: l.price,
    }));
  }, [listings, range]);

  if (data.length === 0) {
    return (
      <div className="bg-poke-card border border-poke-border rounded-lg p-6 text-center text-poke-muted text-sm">
        No price history yet — run a search to populate data.
      </div>
    );
  }

  return (
    <div className="bg-poke-card border border-poke-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-200">{title}</h3>
        <div className="flex gap-1">
          {RANGES.map(({ label }) => (
            <button
              key={label}
              onClick={() => setRange(label)}
              className={`px-2.5 py-1 text-xs rounded transition-colors ${
                range === label
                  ? "bg-poke-blue text-white"
                  : "text-poke-muted hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            tickLine={false}
            axisLine={{ stroke: "#2a2d3a" }}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#6b7280" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `£${v}`}
            width={50}
          />
          <Tooltip content={<CustomTooltip />} />
          {purchasePrice && (
            <ReferenceLine
              y={purchasePrice}
              stroke="#ef4444"
              strokeDasharray="4 2"
              label={{ value: "Cost", fill: "#ef4444", fontSize: 11 }}
            />
          )}
          <Line
            type="monotone"
            dataKey="price"
            name="Sold Price"
            stroke="#FFCB05"
            strokeWidth={2}
            dot={data.length < 40 ? { r: 3, fill: "#FFCB05" } : false}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
