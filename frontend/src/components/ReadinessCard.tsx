import { type Readiness } from "../api";

function colorFor(score: number): string {
  if (score >= 70) return "var(--accent)";
  if (score >= 50) return "#e3b341";
  return "var(--error)";
}

export default function ReadinessCard({ readiness }: { readiness: Readiness }) {
  const color = colorFor(readiness.score);
  // SVG ring geometry
  const r = 34;
  const circ = 2 * Math.PI * r;
  const dash = (readiness.score / 100) * circ;

  return (
    <section className="card readiness">
      <h3>🔋 Recovery readiness</h3>
      <div className="readiness-body">
        <div className="readiness-ring">
          <svg viewBox="0 0 80 80" width="80" height="80">
            <circle cx="40" cy="40" r={r} fill="none" stroke="var(--card-2)" strokeWidth="8" />
            <circle
              cx="40" cy="40" r={r} fill="none" stroke={color} strokeWidth="8"
              strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
              transform="rotate(-90 40 40)"
            />
            <text x="40" y="45" textAnchor="middle" fontSize="20" fontWeight="700" fill="var(--text)">
              {readiness.score}
            </text>
          </svg>
        </div>
        <div className="readiness-info">
          <div className="readiness-label" style={{ color }}>{readiness.label}</div>
          <div className="muted small">{readiness.recommendation}</div>
          <ul className="readiness-factors">
            {readiness.factors.map((f, i) => (
              <li key={i} className="muted small">{f}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
