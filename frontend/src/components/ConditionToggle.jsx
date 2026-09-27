const CONDITIONS = [
  { key: "raw", label: "Raw" },
  { key: "psa10", label: "PSA 10" },
  { key: "psa9", label: "PSA 9" },
  { key: "bgs95", label: "BGS 9.5" },
  { key: "cgc10", label: "CGC 10" },
];

export default function ConditionToggle({ value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2">
      {CONDITIONS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={`px-3 py-1.5 rounded-md text-sm font-medium border transition-all ${
            value === key
              ? "bg-poke-blue border-poke-blue text-white"
              : "bg-transparent border-poke-border text-gray-400 hover:border-gray-500 hover:text-white"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
