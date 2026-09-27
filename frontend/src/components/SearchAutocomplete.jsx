import { useState, useEffect, useRef, useCallback } from "react";

const POKETCG_URL = "https://api.pokemontcg.io/v2/cards";

// Simple in-memory cache so we don't re-hit the API for the same query
const cache = new Map();

function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

async function fetchCards(q) {
  if (cache.has(q)) return cache.get(q);
  const url = `${POKETCG_URL}?q=name:"${encodeURIComponent(q)}*"&pageSize=20&orderBy=name`;
  const resp = await fetch(url);
  if (!resp.ok) return [];
  const { data } = await resp.json();
  const results = (data || []).map((c) => ({
    id: c.id,
    name: c.name,
    set_name: c.set?.name ?? "",
    number: c.number ?? "",
    rarity: c.rarity ?? "",
    supertype: c.supertype ?? "",
    hp: c.hp ?? "",
    image_small: c.images?.small ?? "",
    image_large: c.images?.large ?? "",
  }));
  cache.set(q, results);
  return results;
}

export default function SearchAutocomplete({ value, onChange, onSelect }) {
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [fetching, setFetching] = useState(false);
  const listRef = useRef(null);
  const debouncedValue = useDebounce(value, 180);

  useEffect(() => {
    if (debouncedValue.trim().length < 2) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    let cancelled = false;
    setFetching(true);
    fetchCards(debouncedValue.trim())
      .then((data) => {
        if (!cancelled) {
          setSuggestions(data);
          setOpen(data.length > 0);
          setActiveIdx(-1);
        }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setFetching(false); });
    return () => { cancelled = true; };
  }, [debouncedValue]);

  const handleSelect = useCallback((card) => {
    const label = [card.name, card.set_name, card.number]
      .filter(Boolean).join(" ").trim();
    onChange(label);
    onSelect?.(card);
    setOpen(false);
    setSuggestions([]);
  }, [onChange, onSelect]);

  function handleKeyDown(e) {
    if (!open) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActiveIdx((i) => Math.max(i - 1, -1)); }
    else if (e.key === "Enter" && activeIdx >= 0) { e.preventDefault(); handleSelect(suggestions[activeIdx]); }
    else if (e.key === "Escape") { setOpen(false); }
  }

  useEffect(() => {
    if (activeIdx >= 0 && listRef.current) {
      listRef.current.children[activeIdx]?.scrollIntoView({ block: "nearest" });
    }
  }, [activeIdx]);

  return (
    <div className="relative flex-1">
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          onBlur={() => setOpen(false)}
          placeholder="e.g. Charizard, Pikachu V, Umbreon VMAX…"
          autoComplete="off"
          spellCheck="false"
          className="w-full bg-poke-card border border-poke-border rounded-xl px-4 py-3 pr-10 text-gray-200 placeholder-poke-muted focus:outline-none focus:border-poke-blue transition-all duration-150"
        />
        {fetching ? (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-poke-blue border-t-transparent rounded-full animate-spin" />
          </div>
        ) : value ? (
          <button
            type="button"
            onMouseDown={(e) => { e.preventDefault(); onChange(""); setSuggestions([]); setOpen(false); }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-poke-muted hover:text-white text-xl leading-none"
          >
            ×
          </button>
        ) : null}
      </div>

      {open && suggestions.length > 0 && (
        <ul
          ref={listRef}
          onMouseDown={(e) => e.preventDefault()}
          className="absolute z-50 mt-1 w-full bg-poke-card border border-poke-border rounded-xl shadow-2xl overflow-auto max-h-80"
        >
          {suggestions.map((card, i) => (
            <li
              key={card.id}
              onClick={() => handleSelect(card)}
              className={`flex items-center gap-3 px-3 py-2.5 cursor-pointer transition-colors ${
                i === activeIdx ? "bg-poke-blue/20" : "hover:bg-white/5"
              }`}
            >
              {card.image_small ? (
                <img
                  src={card.image_small}
                  alt={card.name}
                  className="w-9 h-12 object-contain rounded flex-shrink-0"
                  loading="lazy"
                />
              ) : (
                <div className="w-9 h-12 bg-gray-800 rounded flex-shrink-0" />
              )}
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium text-gray-200 truncate">{card.name}</div>
                <div className="text-xs text-poke-muted truncate">
                  {[card.set_name, card.number && `#${card.number}`, card.rarity].filter(Boolean).join(" · ")}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
