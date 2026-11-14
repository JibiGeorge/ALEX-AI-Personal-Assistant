import { useState } from "react";
import type {
  CandidatePreferences,
  CandidateProfile,
  ScheduleDiscoveryConfig,
  WorkModality,
} from "../../types/jobHunting";

interface SettingsViewProps {
  profile: CandidateProfile | null;
  schedule: ScheduleDiscoveryConfig | null;
  onUpdateProfile: (profile: Partial<CandidateProfile>) => Promise<void>;
  onUpdatePreferences: (prefs: Partial<CandidatePreferences>) => Promise<void>;
  onUploadResume: (rawText: string) => Promise<void>;
  onUpdateSchedule: (enabled: boolean, intervalHours: number) => Promise<void>;
  onError: (msg: string) => void;
  onSuccess: (msg: string) => void;
}

export function SettingsView({
  profile,
  schedule,
  onUpdateProfile,
  onUpdatePreferences,
  onUploadResume,
  onUpdateSchedule,
  onError,
  onSuccess,
}: SettingsViewProps) {
  // Profile form state
  const [fullName, setFullName] = useState(profile?.full_name || "");
  const [email, setEmail] = useState(profile?.email || "");
  const [headline, setHeadline] = useState(profile?.headline || "");
  const [summary, setSummary] = useState(profile?.summary || "");
  const [location, setLocation] = useState(profile?.location || "");
  const [linkedinUrl, setLinkedinUrl] = useState(profile?.linkedin_url || "");
  const [githubUrl, setGithubUrl] = useState(profile?.github_url || "");
  const [totalYears, setTotalYears] = useState(profile?.total_years_experience || 4);
  const [savingProfile, setSavingProfile] = useState(false);

  // Preferences form state
  const prefs = profile?.preferences;
  const [targetRoles, setTargetRoles] = useState(
    prefs?.target_roles?.join(", ") ||
      "Software Developer, Full Stack Developer, React Developer, Next.js Developer, Node.js Developer",
  );
  const [minExp, setMinExp] = useState(prefs?.min_years_experience ?? 2);
  const [maxExp, setMaxExp] = useState(prefs?.max_years_experience ?? 5);
  const [modalities, setModalities] = useState<WorkModality[]>(
    prefs?.modalities || ["remote", "hybrid", "onsite"],
  );
  const [targetLocations, setTargetLocations] = useState(
    prefs?.target_locations?.join(", ") || "Worldwide, Remote",
  );
  const [savingPrefs, setSavingPrefs] = useState(false);

  // Resume upload state
  const [resumeText, setResumeText] = useState("");
  const [parsingResume, setParsingResume] = useState(false);

  // Scheduler state
  const [schedEnabled, setSchedEnabled] = useState(schedule?.enabled ?? true);
  const [schedInterval, setSchedInterval] = useState(schedule?.interval_hours ?? 12);
  const [savingSched, setSavingSched] = useState(false);

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSavingProfile(true);
    try {
      await onUpdateProfile({
        full_name: fullName,
        email,
        headline,
        summary,
        location,
        linkedin_url: linkedinUrl || null,
        github_url: githubUrl || null,
        total_years_experience: Number(totalYears),
      });
      onSuccess("Candidate profile updated successfully.");
    } catch (err: any) {
      onError(`Failed to update profile: ${err.message}`);
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleSavePreferences(e: React.FormEvent) {
    e.preventDefault();
    setSavingPrefs(true);
    try {
      await onUpdatePreferences({
        target_roles: targetRoles.split(",").map((s) => s.trim()).filter(Boolean),
        min_years_experience: Number(minExp),
        max_years_experience: Number(maxExp),
        modalities,
        target_locations: targetLocations.split(",").map((s) => s.trim()).filter(Boolean),
      });
      onSuccess("Job hunting preferences updated successfully.");
    } catch (err: any) {
      onError(`Failed to update preferences: ${err.message}`);
    } finally {
      setSavingPrefs(false);
    }
  }

  function toggleModality(mod: WorkModality) {
    if (modalities.includes(mod)) {
      if (modalities.length > 1) {
        setModalities(modalities.filter((m) => m !== mod));
      }
    } else {
      setModalities([...modalities, mod]);
    }
  }

  async function handleResumeUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!resumeText.trim()) return;
    setParsingResume(true);
    try {
      await onUploadResume(resumeText.trim());
      setResumeText("");
      onSuccess("Master resume parsed and candidate profile verified.");
    } catch (err: any) {
      onError(`Failed to parse resume: ${err.message}`);
    } finally {
      setParsingResume(false);
    }
  }

  async function handleSaveSchedule(e: React.FormEvent) {
    e.preventDefault();
    setSavingSched(true);
    try {
      await onUpdateSchedule(schedEnabled, Number(schedInterval));
      onSuccess("Job discovery scheduler configured.");
    } catch (err: any) {
      onError(`Failed to update schedule: ${err.message}`);
    } finally {
      setSavingSched(false);
    }
  }

  return (
    <div>
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>⚙️</span> JOB HUNTING SETTINGS & CANDIDATE PROFILE</h2>
          <p>
            Configure verified career preferences, master resume ground-truth, and automated discovery cadence.
          </p>
        </div>
        {profile?.is_verified && (
          <div className="jh-badge jh-badge-high" style={{ padding: "0.4rem 0.8rem", fontSize: "0.85rem" }}>
            ✓ VERIFIED PROFILE
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Left Column: Profile & Ground Truth */}
        <div>
          {/* Candidate Profile Form */}
          <div className="jh-card" style={{ marginBottom: "1.5rem" }}>
            <div className="jh-card-header">
              <h4>VERIFIED CANDIDATE IDENTITY</h4>
            </div>
            <form onSubmit={handleSaveProfile}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "0.75rem" }}>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                    Full Name
                  </label>
                  <input
                    type="text"
                    className="jh-input"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                    Email
                  </label>
                  <input
                    type="email"
                    className="jh-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "0.75rem" }}>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                    Location
                  </label>
                  <input
                    type="text"
                    className="jh-input"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                    Years Experience
                  </label>
                  <input
                    type="number"
                    className="jh-input"
                    value={totalYears}
                    onChange={(e) => setTotalYears(Number(e.target.value))}
                  />
                </div>
              </div>

              <div style={{ marginBottom: "0.75rem" }}>
                <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                  Professional Headline
                </label>
                <input
                  type="text"
                  className="jh-input"
                  value={headline}
                  onChange={(e) => setHeadline(e.target.value)}
                />
              </div>

              <div style={{ marginBottom: "0.75rem" }}>
                <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                  Summary
                </label>
                <textarea
                  className="jh-input"
                  rows={3}
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1rem" }}>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                    LinkedIn URL
                  </label>
                  <input
                    type="url"
                    className="jh-input"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                    placeholder="https://linkedin.com/in/..."
                  />
                </div>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                    GitHub URL
                  </label>
                  <input
                    type="url"
                    className="jh-input"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/..."
                  />
                </div>
              </div>

              <div style={{ textAlign: "right" }}>
                <button
                  type="submit"
                  className="jh-btn jh-btn-primary"
                  disabled={savingProfile}
                >
                  {savingProfile ? "Saving Profile..." : "Update Candidate Profile"}
                </button>
              </div>
            </form>
          </div>

          {/* Master Resume Ingestion */}
          <div className="jh-card">
            <div className="jh-card-header">
              <h4>MASTER RESUME GROUND TRUTH</h4>
            </div>
            <p style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", marginBottom: "0.75rem" }}>
              Paste or upload your canonical resume. ALEX parses your genuine career history and uses it as the sole ground truth for matching and resume tailoring.
            </p>
            <form onSubmit={handleResumeUpload}>
              <textarea
                className="jh-input"
                rows={4}
                placeholder="Paste complete plain-text or markdown resume..."
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                style={{ fontFamily: "monospace", fontSize: "0.8rem", marginBottom: "0.75rem" }}
              />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)" }}>
                  {profile?.raw_resume_text ? "Master resume currently loaded" : "No resume uploaded yet"}
                </span>
                <button
                  type="submit"
                  className="jh-btn jh-btn-secondary"
                  disabled={parsingResume || !resumeText.trim()}
                >
                  {parsingResume ? "Parsing & Verifying..." : "Upload & Analyze Resume"}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right Column: Career Preferences & Autonomous Scheduler */}
        <div>
          {/* Career Preferences */}
          <div className="jh-card" style={{ marginBottom: "1.5rem" }}>
            <div className="jh-card-header">
              <h4>CAREER & JOB HUNTING PREFERENCES</h4>
            </div>
            <form onSubmit={handleSavePreferences}>
              <div style={{ marginBottom: "0.75rem" }}>
                <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                  Target Roles (Comma-separated)
                </label>
                <input
                  type="text"
                  className="jh-input"
                  value={targetRoles}
                  onChange={(e) => setTargetRoles(e.target.value)}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "0.75rem" }}>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                    Min Experience (Years)
                  </label>
                  <input
                    type="number"
                    className="jh-input"
                    value={minExp}
                    onChange={(e) => setMinExp(Number(e.target.value))}
                  />
                </div>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                    Max Experience (Years)
                  </label>
                  <input
                    type="number"
                    className="jh-input"
                    value={maxExp}
                    onChange={(e) => setMaxExp(Number(e.target.value))}
                  />
                </div>
              </div>

              <div style={{ marginBottom: "0.75rem" }}>
                <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                  Target Locations
                </label>
                <input
                  type="text"
                  className="jh-input"
                  value={targetLocations}
                  onChange={(e) => setTargetLocations(e.target.value)}
                />
              </div>

              <div style={{ marginBottom: "1rem" }}>
                <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.4rem" }}>
                  Work Arrangements
                </label>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  {(["remote", "hybrid", "onsite"] as WorkModality[]).map((m) => {
                    const active = modalities.includes(m);
                    return (
                      <button
                        key={m}
                        type="button"
                        onClick={() => toggleModality(m)}
                        className={`jh-btn ${active ? "jh-btn-primary" : "jh-btn-secondary"}`}
                        style={{ textTransform: "uppercase", fontSize: "0.75rem", padding: "0.3rem 0.6rem" }}
                      >
                        {active ? `✓ ${m}` : m}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div style={{ textAlign: "right" }}>
                <button
                  type="submit"
                  className="jh-btn jh-btn-primary"
                  disabled={savingPrefs}
                >
                  {savingPrefs ? "Saving..." : "Save Preferences"}
                </button>
              </div>
            </form>
          </div>

          {/* Autonomous Discovery Scheduler */}
          <div className="jh-card">
            <div className="jh-card-header">
              <h4>DISCOVERY ENGINE SCHEDULER</h4>
            </div>
            <p style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", marginBottom: "0.75rem" }}>
              Automatically runs background discovery sweeps across configured public feeds, Greenhouse, Lever, and career portals.
            </p>
            <form onSubmit={handleSaveSchedule}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
                <input
                  type="checkbox"
                  id="schedToggle"
                  checked={schedEnabled}
                  onChange={(e) => setSchedEnabled(e.target.checked)}
                  style={{ width: "18px", height: "18px", accentColor: "var(--hud-accent)" }}
                />
                <label htmlFor="schedToggle" style={{ fontSize: "0.9rem", color: "var(--hud-text)", cursor: "pointer" }}>
                  Enable Scheduled Discovery Sweeps
                </label>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1rem" }}>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)", display: "block", marginBottom: "0.25rem" }}>
                    Interval (Hours)
                  </label>
                  <select
                    className="jh-input"
                    value={schedInterval}
                    onChange={(e) => setSchedInterval(Number(e.target.value))}
                  >
                    <option value={4}>Every 4 hours</option>
                    <option value={6}>Every 6 hours</option>
                    <option value={12}>Every 12 hours (Recommended)</option>
                    <option value={24}>Every 24 hours (Daily)</option>
                  </select>
                </div>

                <div style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", display: "flex", flexDirection: "column", justifyContent: "center" }}>
                  <div>Last Run: {schedule?.last_run_at ? new Date(schedule.last_run_at).toLocaleString() : "Never"}</div>
                  <div>Next Run: {schedule?.next_run_at ? new Date(schedule.next_run_at).toLocaleString() : "Pending"}</div>
                </div>
              </div>

              <div style={{ textAlign: "right" }}>
                <button
                  type="submit"
                  className="jh-btn jh-btn-primary"
                  disabled={savingSched}
                >
                  {savingSched ? "Saving Schedule..." : "Save Discovery Schedule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

