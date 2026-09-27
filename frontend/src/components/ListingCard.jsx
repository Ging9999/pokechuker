import { format, parseISO } from "date-fns";

function formatDate(dateStr) {
  try {
    return format(parseISO(dateStr), "dd MMM yyyy");
  } catch {
    return dateStr || "Unknown";
  }
}

function isRealUrl(url) {
  // Mock data uses hex IDs like /itm/078f488c0b3c — real eBay IDs are numeric
  if (!url) return false;
  const m = url.match(/\/itm\/(\w+)/);
  if (m && !/^\d+$/.test(m[1])) return false; // hex = fake
  return url.startsWith("https://www.ebay.co.uk") || url.startsWith("https://rover.ebay.com");
}

export default function ListingCard({ listing }) {
  const { title, price, date, url, condition, image, sold } = listing;
  const hasLink = isRealUrl(url);

  const inner = (
    <>
      {image && (
        <img
          src={image}
          alt={title}
          className="w-16 h-16 object-contain rounded flex-shrink-0 bg-gray-900"
          onError={(e) => { e.target.style.display = "none"; }}
        />
      )}
      <div className="flex-1 min-w-0">
        <div className="text-sm text-gray-300 truncate group-hover:text-white transition-colors">
          {title}
        </div>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-poke-yellow font-bold text-lg">
            £{price?.toFixed(2)}
          </span>
          {condition && (
            <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">
              {condition}
            </span>
          )}
          {sold && (
            <span className="text-xs bg-green-900/40 text-green-400 px-2 py-0.5 rounded">
              Sold
            </span>
          )}
        </div>
        <div className="text-xs text-poke-muted mt-1">{formatDate(date)}</div>
      </div>
      {hasLink && <div className="text-poke-muted self-center text-lg flex-shrink-0">↗</div>}
    </>
  );

  const cls = "flex gap-3 bg-poke-card border border-poke-border rounded-lg p-3 transition-colors group" +
    (hasLink ? " hover:border-poke-blue cursor-pointer" : "");

  if (hasLink) {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer" className={cls}>
        {inner}
      </a>
    );
  }
  return <div className={cls}>{inner}</div>;
}
