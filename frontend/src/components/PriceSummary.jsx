export default function PriceSummary({ stats }) {
  if (!stats || stats.count === 0) return null;

  const items = [
    { label: "Lowest", value: stats.min, color: "text-green-400" },
    { label: "Median", value: stats.median, color: "text-poke-yellow" },
    { label: "Average", value: stats.avg, color: "text-blue-400" },
    { label: "Highest", value: stats.max, color: "text-red-400" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      {items.map(({ label, value, color }) => (
        <div key={label} className="bg-poke-card border border-poke-border rounded-lg p-4">
          <div className="text-xs text-poke-muted mb-1">{label}</div>
          <div className={`text-2xl font-bold ${color}`}>
            £{value?.toFixed(2) ?? "—"}
          </div>
        </div>
      ))}
      <div className="col-span-2 sm:col-span-4 text-xs text-poke-muted text-right">
        Based on {stats.count} listing{stats.count !== 1 ? "s" : ""}
      </div>
    </div>
  );
}
