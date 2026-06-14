const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "ripe_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    throw new Error("Not authenticated");
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Types ---
export interface Profile {
  id: number;
  ftp_watts: number | null;
  threshold_pace_s_per_km: number | null;
  max_hr: number | null;
  resting_hr: number | null;
  weight_kg: number | null;
  notes: string | null;
}
export interface EventItem {
  id: number;
  name: string;
  event_date: string;
  event_type: string;
  goal: string | null;
  priority: string;
}
export interface WorkoutStep {
  phase: string;
  detail: string;
}
export interface Workout {
  id: number;
  workout_date: string;
  slot_start: string | null;
  sport: string;
  title: string;
  structure: { steps: WorkoutStep[] } | null;
  targets: string | null;
  rationale: string | null;
  status: string;
}
export interface Plan {
  id: number;
  created_at: string;
  week_start: string;
  model: string | null;
  rationale: string | null;
  workouts: Workout[];
}
export interface Activity {
  id: number;
  sport: string;
  start_time: string;
  duration_s: number | null;
  distance_m: number | null;
  avg_hr: number | null;
  avg_power: number | null;
  training_load: number | null;
}
export interface SportVolume {
  km: number;
  hours: number;
  sessions: number;
}
export interface WeekVolume {
  week_start: string;
  is_current: boolean;
  total_km: number;
  total_hours: number;
  sessions: number;
  by_sport: Record<string, SportVolume>;
}
export interface VolumeStats {
  weeks: WeekVolume[];
  targets: {
    weekly_hours: number | null;
    weekly_km: number | null;
    weekly_sessions: number | null;
  };
}
export interface Readiness {
  date: string;
  score: number;
  label: string;
  recommendation: string;
  components: Record<string, number>;
  factors: string[];
  resting_hr_baseline: number | null;
}

// --- Endpoints ---
export const api = {
  health: () => request<{ status: string }>("/health"),
  login: (password: string) =>
    request<{ token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  getProfile: () => request<Profile>("/profile"),
  updateProfile: (body: Partial<Profile>) =>
    request<Profile>("/profile", { method: "PUT", body: JSON.stringify(body) }),
  listEvents: () => request<EventItem[]>("/events"),
  listActivities: () => request<Activity[]>("/activities?limit=10"),
  syncGarmin: () =>
    request<{ message: string }>("/activities/sync", { method: "POST" }),
  volumeStats: () => request<VolumeStats>("/activities/stats?weeks=8"),
  readiness: () => request<Readiness | null>("/activities/readiness"),
  latestPlan: () => request<Plan | null>("/plan/latest"),
  generatePlan: () => request<Plan>("/plan/generate", { method: "POST" }),
  setWorkoutStatus: (id: number, status: string) =>
    request<Workout>(`/plan/workout/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  addEvent: (body: Omit<EventItem, "id">) =>
    request<EventItem>("/events", { method: "POST", body: JSON.stringify(body) }),
  deleteEvent: (id: number) =>
    request<void>(`/events/${id}`, { method: "DELETE" }),
};
