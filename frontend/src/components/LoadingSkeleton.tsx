export function LoadingSkeleton() {
  return (
    <div className="skeleton-wrapper" aria-busy="true" aria-label="Loading stock data">
      <div className="skeleton-chart">
        <div className="skeleton-line skeleton-title" />
        <div className="skeleton-bars">
          {[65, 40, 80, 55, 30, 70, 50].map((h, i) => (
            <div key={i} className="skeleton-bar" style={{ height: `${h}%` }} />
          ))}
        </div>
      </div>

      {[0, 1, 2].map((i) => (
        <div key={i} className="skeleton-card">
          <div className="skeleton-line skeleton-date" />
          <div className="skeleton-line skeleton-ticker" />
        </div>
      ))}
    </div>
  );
}
