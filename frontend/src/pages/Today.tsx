import { useEffect, useState } from "react";
import { api, type CoachFeedback, type Plan } from "../api";

const SPORT_ICON: Record<string, string> = { run: "🏃", bike: "🚴", gym: "🏋️", rest: "😴" };

function dayLabel(d: string) {
  return new Date(d).toLocaleDateString(undefined, { weekday: "short" });
}

export default function Today() {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [feedback, setFeedback] = useState<CoachFeedback | null>(null);
  const [adjustText, setAdjustText] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function loadPlan() {
    setPlan(await api.latestPlan().catch(() => null));
  }
  async function loadFeedback() {
    setBusy("feedback");
    try {
      setFeedback(await api.planFeedback());
    } catch {
      /* ignore */
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => {
    loadPlan();
    loadFeedback();
  }, []);

  async function run(action: string, fn: () => Promise<unknown>) {
    setBusy(action);
    setMsg(null);
    try {
      await fn();
      await loadPlan();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(null);
    }
  }

  const nextWorkout =
    plan?.workouts.find((w) => w.status === "planned" && w.sport !== "rest") ?? null;
  const adh = feedback?.stats.adherence;

  return (
    <div className="page">
      {msg && <div className="banner">{msg}</div>}

      {/* Next workout hero */}
      {nextWorkout ? (
        <section className="card hero">
          <div className="muted small">NEXT UP · {dayLabel(nextWorkout.workout_date)}</div>
          <div className="hero-title">
            <span className="hero-icon">{SPORT_ICON[nextWorkout.sport] ?? "•"}</span>
            {nextWorkout.title}
          </div>
          {nextWorkout.targets && <div className="hero-targets">{nextWorkout.targets}</div>}
          {nextWorkout.structure?.steps && (
            <ul className="steps">
              {nextWorkout.structure.steps.map((s, i) => (
                <li key={i}><b>{s.phase}:</b> {s.detail}</li>
              ))}
            </ul>
          )}
          <div className="workout-actions">
            <button
              className="small"
              disabled={busy !== null}
              onClick={() => run(`done-${nextWorkout.id}`, () => api.setWorkoutStatus(nextWorkout.id, "done"))}
            >
              ✓ Mark done
            </button>
            <button
              className="ghost small"
              disabled={busy !== null}
              onClick={() => run(`skip-${nextWorkout.id}`, () => api.setWorkoutStatus(nextWorkout.id, "skipped"))}
            >
              ✕ Skip
            </button>
          </div>
        </section>
      ) : (
        <section className="card hero">
          <div className="hero-title">🎉 No sessions queued</div>
          <div className="muted">
            {plan ? "You're all caught up this week." : "Generate a plan below to get started."}
          </div>
        </section>
      )}

      {/* Coach feedback — tough but fair */}
      <section className="card">
        <div className="card-head">
          <h3>🧠 Coach's take</h3>
          <button className="ghost small" disabled={busy !== null} onClick={loadFeedback}>
            {busy === "feedback" ? "Refreshing…" : "↻ Refresh"}
          </button>
        </div>
        {adh?.has_plan && (
          <div className="feedback-stats">
            <span className="vol-chip">
              On track <b>{adh.on_track_pct ?? 0}%</b>
              <span className="muted"> ({adh.done_so_far ?? 0}/{adh.due_so_far ?? 0} due so far)</span>
            </span>
            <span className="vol-chip">
              {feedback?.stats.this_week_km}km
              {feedback?.stats.trailing_avg_km != null && (
                <span className="muted"> vs {feedback.stats.trailing_avg_km} avg</span>
              )}
            </span>
            {feedback?.stats.readiness && (
              <span className="vol-chip">Readiness <b>{feedback.stats.readiness.score}</b></span>
            )}
          </div>
        )}
        {feedback?.verdict ? (
          <p className="rationale">{feedback.verdict}</p>
        ) : busy === "feedback" ? (
          <p className="muted">Reviewing your training…</p>
        ) : (
          <p className="muted small">{feedback?.error ?? "No feedback yet."}</p>
        )}
      </section>

      {/* This week's plan */}
      <section className="card">
        <div className="card-head">
          <h3>📅 This week</h3>
          <button disabled={busy !== null} onClick={() => run("plan", api.generatePlan)}>
            {busy === "plan" ? "Coaching…" : plan ? "Regenerate" : "Generate"}
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
                        {dayLabel(w.workout_date)}{w.targets ? ` · ${w.targets}` : ""}
                      </div>
                    </div>
                  </div>
                  {w.structure?.steps && (
                    <ul className="steps">
                      {w.structure.steps.map((s, i) => (
                        <li key={i}><b>{s.phase}:</b> {s.detail}</li>
                      ))}
                    </ul>
                  )}
                  {w.rationale && <p className="muted small">{w.rationale}</p>}
                  {w.sport !== "rest" && (
                    <div className="workout-actions">
                      <button className="ghost small" disabled={busy !== null}
                        onClick={() => run(`done-${w.id}`, () => api.setWorkoutStatus(w.id, "done"))}>
                        ✓ Done
                      </button>
                      <button className="ghost small" disabled={busy !== null}
                        onClick={() => run(`skip-${w.id}`, () => api.setWorkoutStatus(w.id, "skipped"))}>
                        ✕ Skip
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="coach-adjust">
              <label className="muted small">
                💬 Tell your coach about changes — weather, travel, how you feel…
              </label>
              <textarea
                value={adjustText}
                onChange={(e) => setAdjustText(e.target.value)}
                placeholder="e.g. Rain forecast Thu, make it indoor Zwift. Traveling Wed. Legs heavy — ease off."
                rows={2}
                disabled={busy !== null}
              />
              <button
                disabled={busy !== null || !adjustText.trim()}
                onClick={() =>
                  run("adjust", async () => {
                    await api.adjustPlan(adjustText.trim());
                    setAdjustText("");
                    await loadFeedback();
                  })
                }
              >
                {busy === "adjust" ? "Adjusting…" : "Adjust plan"}
              </button>
            </div>
          </>
        ) : (
          <p className="muted">No plan yet. Set your event and budget in Goals, then generate one.</p>
        )}
      </section>
    </div>
  );
}
