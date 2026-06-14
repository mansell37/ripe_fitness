import { useEffect, useState } from "react";
import {
  api,
  type Activity,
  type EventItem,
  type Plan,
  type Profile,
  type Readiness,
  type SyncStatus,
  type VolumeStats,
} from "../api";
import TrainingVolume from "../components/TrainingVolume";
import ReadinessCard from "../components/ReadinessCard";

const SPORT_ICON: Record<string, string> = {
  run: "🏃",
  bike: "🚴",
  gym: "🏋️",
  rest: "😴",
};

function daysUntil(dateStr: string): number {
  const d = new Date(dateStr).getTime() - Date.now();
  return Math.ceil(d / 86_400_000);
}

export default function Dashboard() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [volume, setVolume] = useState<VolumeStats | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    const [p, e, a, pl, v, r, ss] = await Promise.all([
      api.getProfile(),
      api.listEvents(),
      api.listActivities().catch(() => []),
      api.latestPlan().catch(() => null),
      api.volumeStats().catch(() => null),
      api.readiness().catch(() => null),
      api.syncStatus().catch(() => null),
    ]);
    setProfile(p);
    setEvents(e);
    setActivities(a);
    setPlan(pl);
    setVolume(v);
    setReadiness(r);
    setSyncStatus(ss);
  }

  useEffect(() => {
    load().catch((err) => setMsg(err.message));
  }, []);

  async function run(action: string, fn: () => Promise<unknown>) {
    setBusy(action);
    setMsg(null);
    try {
      await fn();
      await load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(null);
    }
  }

  const nextEvent = events[0];

  return (
    <div className="dashboard">
      {msg && <div className="banner">{msg}</div>}

      <div className="grid">
        {/* Goal / event */}
        <section className="card">
          <h3>🎯 Goal</h3>
          {nextEvent ? (
            <>
              <div className="big">{nextEvent.name}</div>
              <div className="muted">
                {nextEvent.goal} · {daysUntil(nextEvent.event_date)} days away
              </div>
            </>
          ) : (
            <p className="muted">No event set yet.</p>
          )}
        </section>

        {/* Profile */}
        <section className="card">
          <h3>⚙️ Fitness markers</h3>
          {profile && (
            <ul className="stats">
              <li>
                FTP <b>{profile.ftp_watts ?? "—"}</b> W
              </li>
              <li>
                Threshold pace{" "}
                <b>
                  {profile.threshold_pace_s_per_km
                    ? `${Math.floor(profile.threshold_pace_s_per_km / 60)}:${String(
                        profile.threshold_pace_s_per_km % 60
                      ).padStart(2, "0")}`
                    : "—"}
                </b>{" "}
                /km
              </li>
              <li>
                Max HR <b>{profile.max_hr ?? "—"}</b>
              </li>
            </ul>
          )}
        </section>

        {/* Garmin sync */}
        <section className="card">
          <h3>⌚ Garmin</h3>
          <p className="muted">{activities.length} recent activities loaded.</p>
          <button
            disabled={busy !== null}
            onClick={() => run("sync", api.syncGarmin)}
          >
            {busy === "sync" ? "Syncing…" : "Sync now"}
          </button>
          {syncStatus?.enabled && (
            <div className="muted small" style={{ marginTop: 10 }}>
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
      </div>

      {/* Recovery readiness */}
      {readiness && <ReadinessCard readiness={readiness} />}

      {/* Training volume */}
      {volume && <TrainingVolume stats={volume} />}

      {/* Weekly plan */}
      <section className="card">
        <div className="card-head">
          <h3>📅 This week's plan</h3>
          <button
            disabled={busy !== null}
            onClick={() => run("plan", api.generatePlan)}
          >
            {busy === "plan" ? "Coaching…" : plan ? "Regenerate" : "Generate plan"}
          </button>
        </div>

        {plan ? (
          <>
            {plan.rationale && <p className="rationale">{plan.rationale}</p>}
            <div className="workouts">
              {plan.workouts.map((w) => (
                <div key={w.id} className={`workout ${w.status}`}>
                  <div className="workout-head">
                    <span className="sport">{SPORT_ICON[w.sport] ?? "•"}</span>
                    <div>
                      <div className="workout-title">{w.title}</div>
                      <div className="muted small">
                        {new Date(w.workout_date).toLocaleDateString(undefined, {
                          weekday: "short",
                        })}
                        {w.slot_start ? ` · ${w.slot_start}` : ""}
                        {w.targets ? ` · ${w.targets}` : ""}
                      </div>
                    </div>
                  </div>
                  {w.structure?.steps && (
                    <ul className="steps">
                      {w.structure.steps.map((s, i) => (
                        <li key={i}>
                          <b>{s.phase}:</b> {s.detail}
                        </li>
                      ))}
                    </ul>
                  )}
                  {w.rationale && <p className="muted small">{w.rationale}</p>}
                  {w.sport !== "rest" && (
                    <div className="workout-actions">
                      <button
                        className="ghost small"
                        onClick={() => run(`done-${w.id}`, () => api.setWorkoutStatus(w.id, "done"))}
                      >
                        ✓ Done
                      </button>
                      <button
                        className="ghost small"
                        onClick={() => run(`skip-${w.id}`, () => api.setWorkoutStatus(w.id, "skipped"))}
                      >
                        ✕ Skip
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="muted">
            No plan yet. Set your availability and event, then generate one.
          </p>
        )}
      </section>
    </div>
  );
}
