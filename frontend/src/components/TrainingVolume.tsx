import { type VolumeStats } from "../api";

const SPORT_ICON: Record<string, string> = {
  run: "🏃",
  bike: "🚴",
  gym: "🏋️",
  other: "•",
};

function ProgressBar({ value, target, unit }: { value: number; target: number | null; unit: string }) {
  const pct = target ? Math.min(100, Math.round((value / target) * 100)) : null;
  return (
    <div className="vol-metric">
      <div className="vol-metric-head">
        <span>
          <b>{value}</b>
          {target ? <span className="muted"> / {target}</span> : ""} {unit}
        </span>
        {pct !== null && <span className="muted small">{pct}%</span>}
      </div>
      {target ? (
        <div className="vol-bar">
          <div
            className="vol-bar-fill"
            style={{ width: `${pct}%`, background: pct! >= 100 ? "var(--accent)" : "var(--accent-2)" }}
          />
        </div>
      ) : (
        <div className="muted small">no target set</div>
      )}
    </div>
  );
}

export default function TrainingVolume({ stats }: { stats: VolumeStats }) {
  const current = stats.weeks[0];
  const trailing = stats.weeks.slice(1).reverse(); // oldest → newest (excl current)
  const maxKm = Math.max(1, ...stats.weeks.map((w) => w.total_km));

  if (!current) return null;

  return (
    <section className="card">
      <h3>📊 Training volume — this week</h3>

      <div className="vol-grid">
        <ProgressBar value={current.total_km} target={stats.targets.weekly_km} unit="km" />
        <ProgressBar value={current.total_hours} target={stats.targets.weekly_hours} unit="hrs" />
        <ProgressBar value={current.sessions} target={stats.targets.weekly_sessions} unit="sessions" />
      </div>

      {/* Per-sport breakdown for current week */}
      {Object.keys(current.by_sport).length > 0 && (
        <div className="vol-sports">
          {Object.entries(current.by_sport).map(([sport, v]) => (
            <span key={sport} className="vol-chip">
              {SPORT_ICON[sport] ?? "•"} {v.km > 0 ? `${v.km}km` : `${v.hours}h`}
              <span className="muted"> ·{v.sessions}</span>
            </span>
          ))}
        </div>
      )}

      {/* Trailing weeks sparkline (km) */}
      {trailing.length > 0 && (
        <div className="vol-trend">
          <div className="muted small" style={{ marginBottom: 6 }}>
            Weekly km — last {stats.weeks.length} weeks
          </div>
          <div className="vol-spark">
            {[...trailing, current].map((w) => (
              <div key={w.week_start} className="vol-spark-col" title={`${w.week_start}: ${w.total_km}km`}>
                <div
                  className="vol-spark-bar"
                  style={{
                    height: `${Math.max(4, (w.total_km / maxKm) * 100)}%`,
                    background: w.is_current ? "var(--accent)" : "var(--accent-2)",
                    opacity: w.is_current ? 1 : 0.55,
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
