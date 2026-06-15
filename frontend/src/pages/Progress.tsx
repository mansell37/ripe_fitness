import { useEffect, useState } from "react";
import {
  api,
  type Activity,
  type Readiness,
  type SyncStatus,
  type VolumeStats,
} from "../api";
import ReadinessCard from "../components/ReadinessCard";
import TrainingVolume from "../components/TrainingVolume";

const SPORT_ICON: Record<string, string> = { run: "🏃", bike: "🚴", gym: "🏋️", rest: "😴" };

function bucket(sport: string): string {
  const s = sport.toLowerCase();
  if (s.includes("run")) return "run";
  if (s.includes("cycl") || s.includes("bik") || s.includes("ride")) return "bike";
  if (s.includes("strength") || s.includes("cardio") || s.includes("gym")) return "gym";
  return "rest";
}

export default function Progress() {
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [volume, setVolume] = useState<VolumeStats | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    const [r, v, a, ss] = await Promise.all([
      api.readiness().catch(() => null),
      api.volumeStats().catch(() => null),
      api.listActivities().catch(() => []),
      api.syncStatus().catch(() => null),
    ]);
    setReadiness(r);
    setVolume(v);
    setActivities(a);
    setSyncStatus(ss);
  }

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, []);

  async function sync() {
    setBusy("sync");
    setMsg(null);
    try {
      await api.syncGarmin();
      await load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page">
      {msg && <div className="banner">{msg}</div>}

      {readiness && <ReadinessCard readiness={readiness} />}
      {volume && <TrainingVolume stats={volume} />}

      {/* Garmin */}
      <section className="card">
        <div className="card-head">
          <h3>⌚ Garmin</h3>
          <button disabled={busy !== null} onClick={sync}>
            {busy === "sync" ? "Syncing…" : "Sync now"}
          </button>
        </div>
        {syncStatus?.enabled && (
          <div className="muted small">
            🔄 Auto-syncs {syncStatus.times.join(", ")} ({syncStatus.timezone})
            {syncStatus.last_run?.at && (
              <div>
                Last: {new Date(syncStatus.last_run.at).toLocaleString()}{" "}
                {syncStatus.last_run.ok ? "✓" : "⚠"}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Recent activities */}
      <section className="card">
        <h3>📋 Recent activities</h3>
        {activities.length > 0 ? (
          <ul className="activity-list">
            {activities.map((a) => (
              <li key={a.id} className="activity-row">
                <span className="sport">{SPORT_ICON[bucket(a.sport)] ?? "•"}</span>
                <div className="activity-info">
                  <div>
                    {a.distance_m ? `${(a.distance_m / 1000).toFixed(1)}km` : ""}
                    {a.duration_s ? ` · ${Math.round(a.duration_s / 60)}min` : ""}
                  </div>
                  <div className="muted small">
                    {new Date(a.start_time).toLocaleDateString()}
                    {a.avg_hr ? ` · ${a.avg_hr}bpm` : ""}
                    {a.avg_power ? ` · ${a.avg_power}W` : ""}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No activities synced yet. Connect Garmin and hit Sync.</p>
        )}
      </section>
    </div>
  );
}
