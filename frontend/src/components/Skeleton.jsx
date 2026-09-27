export function SkeletonCard() {
  return (
    <div className="flex gap-3 bg-poke-card border border-poke-border rounded-lg p-3 animate-pulse">
      <div className="w-16 h-16 bg-gray-800 rounded flex-shrink-0" />
      <div className="flex-1 space-y-2 py-1">
        <div className="h-3 bg-gray-800 rounded w-3/4" />
        <div className="h-5 bg-gray-800 rounded w-1/3" />
        <div className="h-3 bg-gray-800 rounded w-1/4" />
      </div>
    </div>
  );
}

export function SkeletonStats() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="bg-poke-card border border-poke-border rounded-lg p-4 animate-pulse">
          <div className="h-3 bg-gray-800 rounded w-1/2 mb-2" />
          <div className="h-7 bg-gray-800 rounded w-2/3" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonGraph() {
  return (
    <div className="bg-poke-card border border-poke-border rounded-lg p-4 h-[268px] animate-pulse">
      <div className="h-4 bg-gray-800 rounded w-1/4 mb-4" />
      <div className="h-full bg-gray-800/40 rounded" />
    </div>
  );
}
