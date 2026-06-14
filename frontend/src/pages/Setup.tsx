import { useEffect, useState } from "react";
import { api, type EventItem } from "../api";

const SPORT_LABELS: Record<string, string> = {
  marathon: "Marathon",
  half_marathon: "Half Marathon",
  "10k": "10K",
  "5k": "5K",
  sportive: "Sportive / Gran Fondo",
  triathlon: "Triathlon",
  other: "Other",
};

function paceDisplay(s: number | null): string {
  if (!s) return "";
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function parsePace(input: string): number | null {
  const m = input.match(/^(\d+):(\d{2})$/);
  if (!m) return null;
  return parseInt(m[1]) * 60 + parseInt(m[2]);
}

export default function Setup() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [msgOk, setMsgOk] = useState(false);

  // Profile form state
  const [ftp, setFtp] = useState("");
  const [pace, setPace] = useState("");
  const [maxHr, setMaxHr] = useState("");
  const [sessions, setSessions] = useState("");
  const [hours, setHours] = useState("");
  const [kmTarget, setKmTarget] = useState("");
  const [scheduleNotes, setScheduleNotes] = useState("");
  const [coachingNotes, setCoachingNotes] = useState("");

  // New event form state
  const [evtName, setEvtName] = useState("");
  const [evtDate, setEvtDate] = useState("");
  const [evtType, setEvtType] = useState("marathon");
  const [evtGoal, setEvtGoal] = useState("");

  async function load() {
    const [p, e] = await Promise.all([api.getProfile(), api.listEvents()]);
    setEvents(e);
    setFtp(p.ftp_watts?.toString() ?? "");
    setPace(paceDisplay(p.threshold_pace_s_per_km));
    setMaxHr(p.max_hr?.toString() ?? "");
    setSessions((p as any).weekly_sessions?.toString() ?? "");
    setHours((p as any).weekly_hours?.toString() ?? "");
    setKmTarget((p as any).weekly_km_target?.toString() ?? "");
    setScheduleNotes((p as any).schedule_notes ?? "");
    setCoachingNotes((p as any).coaching_notes ?? "");
  }

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, []);

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      await api.updateProfile({
        ftp_watts: ftp ? parseInt(ftp) : null,
        threshold_pace_s_per_km: parsePace(pace),
        max_hr: maxHr ? parseInt(maxHr) : null,
        weekly_sessions: sessions ? parseInt(sessions) : null,
        weekly_hours: hours ? parseFloat(hours) : null,
        weekly_km_target: kmTarget ? parseFloat(kmTarget) : null,
        schedule_notes: scheduleNotes || null,
        coaching_notes: coachingNotes || null,
      } as any);
      setMsgOk(true);
      setMsg("Profile saved.");
    } catch (err) {
      setMsgOk(false);
      setMsg(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function addEvent(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      await api.addEvent({ name: evtName, event_date: evtDate, event_type: evtType, goal: evtGoal || null, priority: "A" });
      setEvtName(""); setEvtDate(""); setEvtGoal("");
      setMsgOk(true);
      setMsg("Event added.");
      await load();
    } catch (err) {
      setMsgOk(false);
      setMsg(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function deleteEvent(id: number) {
    await api.deleteEvent(id);
    await load();
  }

  function daysUntil(d: string) {
    return Math.ceil((new Date(d).getTime() - Date.now()) / 86_400_000);
  }

  return (
    <div className="setup">
      {msg && <div className={`banner ${msgOk ? "banner-ok" : ""}`}>{msg}</div>}

      {/* --- Events --- */}
      <section className="card">
        <h3>🎯 Upcoming events</h3>

        {events.length > 0 ? (
          <ul className="event-list">
            {events.map((ev) => (
              <li key={ev.id} className="event-row">
                <div>
                  <strong>{ev.name}</strong>
                  <span className="muted small">
                    {" "}· {ev.event_date} · {daysUntil(ev.event_date)} days away
                    {ev.goal ? ` · Goal: ${ev.goal}` : ""}
                  </span>
                </div>
                <button className="ghost small danger" onClick={() => deleteEvent(ev.id)}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No events yet.</p>
        )}

        <details className="add-form">
          <summary>+ Add event</summary>
          <form onSubmit={addEvent}>
            <div className="form-row">
              <label>Event name</label>
              <input value={evtName} onChange={(e) => setEvtName(e.target.value)} placeholder="Sydney Marathon" required />
            </div>
            <div className="form-row">
              <label>Date</label>
              <input type="date" value={evtDate} onChange={(e) => setEvtDate(e.target.value)} required />
            </div>
            <div className="form-row">
              <label>Type</label>
              <select value={evtType} onChange={(e) => setEvtType(e.target.value)}>
                {Object.entries(SPORT_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <label>Goal <span className="muted">(optional)</span></label>
              <input value={evtGoal} onChange={(e) => setEvtGoal(e.target.value)} placeholder="sub-3:00" />
            </div>
            <button type="submit" disabled={saving}>Add</button>
          </form>
        </details>
      </section>

      {/* --- Training budget --- */}
      <section className="card">
        <h3>📅 Weekly training budget</h3>
        <p className="muted small">
          Tell the coach how much you can train. It'll prescribe exactly this many sessions per week.
        </p>
        <form onSubmit={saveProfile}>
          <div className="form-grid">
            <div className="form-row">
              <label>Sessions per week</label>
              <input
                type="number" min="1" max="14"
                value={sessions}
                onChange={(e) => setSessions(e.target.value)}
                placeholder="5"
              />
            </div>
            <div className="form-row">
              <label>Hours per week</label>
              <input
                type="number" min="1" max="40" step="0.5"
                value={hours}
                onChange={(e) => setHours(e.target.value)}
                placeholder="8"
              />
            </div>
            <div className="form-row">
              <label>Weekly km target <span className="muted">(optional)</span></label>
              <input
                type="number" min="0" max="300" step="1"
                value={kmTarget}
                onChange={(e) => setKmTarget(e.target.value)}
                placeholder="60"
              />
            </div>
          </div>
          <div className="form-row">
            <label>Schedule notes</label>
            <textarea
              value={scheduleNotes}
              onChange={(e) => setScheduleNotes(e.target.value)}
              placeholder="e.g. I can train Mon–Fri mornings for up to 1hr before work. Longer sessions (1.5–2hr) on Saturday or Sunday. Wednesday evenings I have family commitments."
              rows={3}
            />
          </div>
          <div className="form-row">
            <label>Coaching preferences <span className="muted">(standing guidance for every plan)</span></label>
            <textarea
              value={coachingNotes}
              onChange={(e) => setCoachingNotes(e.target.value)}
              placeholder="e.g. Prefer outdoor rides when dry, indoor Zwift if wet or dark. I dislike treadmill runs. Keep one full rest day. Long run on Sunday if possible."
              rows={3}
            />
          </div>

          {/* --- Fitness markers --- */}
          <h3 style={{ marginTop: "20px" }}>⚙️ Fitness markers</h3>
          <p className="muted small">Used to set accurate power and pace targets in your workouts.</p>
          <div className="form-grid">
            <div className="form-row">
              <label>FTP (watts)</label>
              <input type="number" value={ftp} onChange={(e) => setFtp(e.target.value)} placeholder="210" />
            </div>
            <div className="form-row">
              <label>Threshold run pace (mm:ss /km)</label>
              <input value={pace} onChange={(e) => setPace(e.target.value)} placeholder="4:05" />
            </div>
            <div className="form-row">
              <label>Max HR (bpm)</label>
              <input type="number" value={maxHr} onChange={(e) => setMaxHr(e.target.value)} placeholder="190" />
            </div>
          </div>

          <button type="submit" disabled={saving} style={{ marginTop: "8px" }}>
            {saving ? "Saving…" : "Save"}
          </button>
        </form>
      </section>
    </div>
  );
}
