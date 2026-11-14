import { useState, useEffect, useRef, type ChangeEvent } from "react";
import type { CandidateProfile, WorkModality } from "../../types/jobHunting";

interface JobOnboardingWizardProps {
  isOpen: boolean;
  onClose: () => void;
  profile: CandidateProfile | null;
  onSaveProfile: (updated: Partial<CandidateProfile>) => Promise<void>;
  onUploadResume: (rawText: string, filename?: string) => Promise<void>;
}

export function JobOnboardingWizard({
  isOpen,
  onClose,
  profile,
  onSaveProfile,
  onUploadResume,
}: JobOnboardingWizardProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Step 1: Resume & Basics
  const [resumeText, setResumeText] = useState(profile?.raw_resume_text || "");
  const [fileName, setFileName] = useState("resume.txt");
  const [fullName, setFullName] = useState(profile?.full_name || "");
  const [email, setEmail] = useState(profile?.email || "");
  const [location, setLocation] = useState(profile?.location || profile?.current_location || "");

  // Step 2: Target Roles & Locations
  const [targetRoles, setTargetRoles] = useState<string[]>(
    profile?.preferences?.target_roles?.length
      ? profile.preferences.target_roles
      : ["Frontend Engineer", "Full Stack Engineer"],
  );
  const [roleInput, setRoleInput] = useState("");
  const [seniority, setSeniority] = useState(profile?.seniority_level || "Senior");
  const [targetLocations, setTargetLocations] = useState<string[]>(
    profile?.preferences?.target_locations?.length
      ? profile.preferences.target_locations
      : ["Remote", "Worldwide"],
  );
  const [locationInput, setLocationInput] = useState("");
  const [modalities, setModalities] = useState<WorkModality[]>(
    profile?.preferences?.modalities?.length ? profile.preferences.modalities : ["remote"],
  );

  // Step 3: Compensation & Work Authorization
  const [minSalary, setMinSalary] = useState<number>(profile?.preferences?.minimum_salary || 135000);
  const [workAuth, setWorkAuth] = useState<string>(
    (profile as any)?.work_authorization || "US Citizen / Green Card",
  );
  const [noticePeriod, setNoticePeriod] = useState<string>(profile?.notice_period || "2 Weeks");

  const modalRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setErrorMsg(null);
      // Focus modal container
      setTimeout(() => modalRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Handle ESC key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (!isOpen) return;
      if (e.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleFileUpload = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result;
      if (typeof content === "string") {
        setResumeText(content);
        // Heuristic extraction for quick population if empty
        if (!fullName) {
          const firstLine = content.split("\n")[0].trim();
          if (firstLine.length < 40 && !firstLine.includes("@")) {
            setFullName(firstLine);
          }
        }
      }
    };
    reader.readAsText(file);
  };

  const handleAddRole = () => {
    const trimmed = roleInput.trim();
    if (trimmed && !targetRoles.includes(trimmed)) {
      setTargetRoles([...targetRoles, trimmed]);
      setRoleInput("");
    }
  };

  const handleRemoveRole = (role: string) => {
    setTargetRoles(targetRoles.filter((r) => r !== role));
  };

  const handleAddLocation = () => {
    const trimmed = locationInput.trim();
    if (trimmed && !targetLocations.includes(trimmed)) {
      setTargetLocations([...targetLocations, trimmed]);
      setLocationInput("");
    }
  };

  const handleRemoveLocation = (loc: string) => {
    setTargetLocations(targetLocations.filter((l) => l !== loc));
  };

  const toggleModality = (mod: WorkModality) => {
    if (modalities.includes(mod)) {
      if (modalities.length > 1) {
        setModalities(modalities.filter((m) => m !== mod));
      }
    } else {
      setModalities([...modalities, mod]);
    }
  };

  const handleFinish = async () => {
    setSaving(true);
    setErrorMsg(null);
    try {
      if (resumeText.trim()) {
        await onUploadResume(resumeText, fileName);
      }

      await onSaveProfile({
        full_name: fullName.trim() || profile?.full_name || "Candidate",
        email: email.trim() || profile?.email || "candidate@alex.local",
        location: location.trim() || profile?.location || "Remote",
        seniority_level: seniority,
        notice_period: noticePeriod,
        preferences: {
          ...(profile?.preferences || {
            auto_discovery_enabled: true,
            discovery_interval_hours: 12,
            min_years_experience: 3,
            max_years_experience: 10,
          }),
          target_roles: targetRoles,
          target_locations: targetLocations,
          modalities,
          minimum_salary: minSalary,
        },
        ...( { work_authorization: workAuth } as any ),
      });

      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to complete onboarding.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="onboarding-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="wizard-title"
      ref={modalRef}
      tabIndex={-1}
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(3, 7, 18, 0.85)",
        backdropFilter: "blur(8px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "16px",
      }}
    >
      <div
        className="onboarding-card hud-panel"
        style={{
          width: "100%",
          maxWidth: "680px",
          background: "var(--hud-bg-surface, #0f172a)",
          border: "1px solid var(--hud-border-cyan, #0ea5e9)",
          boxShadow: "0 20px 50px rgba(0, 240, 255, 0.15)",
          borderRadius: "12px",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid var(--hud-border-cyan, #1e293b)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div
              style={{
                fontSize: "11px",
                fontFamily: "var(--hud-font-mono, monospace)",
                color: "var(--hud-accent-cyan, #38bdf8)",
                letterSpacing: "1px",
              }}
            >
              INITIAL SETUP PROTOCOL · STEP {step} OF 3
            </div>
            <h2
              id="wizard-title"
              style={{
                margin: "4px 0 0",
                fontSize: "18px",
                fontWeight: 600,
                color: "var(--hud-text-primary, #f8fafc)",
              }}
            >
              {step === 1 && "Master Resume & Candidate Profile"}
              {step === 2 && "Target Roles & Geographic Preferences"}
              {step === 3 && "Compensation & Work Authorization"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close onboarding wizard"
            style={{
              background: "transparent",
              border: "1px solid var(--hud-border-cyan, #334155)",
              color: "var(--hud-text-secondary, #94a3b8)",
              borderRadius: "6px",
              padding: "6px 10px",
              cursor: "pointer",
            }}
          >
            ✕
          </button>
        </div>

        {/* Progress Bar */}
        <div style={{ height: "4px", background: "#1e293b", width: "100%" }}>
          <div
            style={{
              height: "100%",
              width: `${(step / 3) * 100}%`,
              background: "var(--hud-accent-cyan, #0ea5e9)",
              transition: "width 0.3s ease",
            }}
          />
        </div>

        {/* Body Content */}
        <div style={{ padding: "24px", overflowY: "auto", maxHeight: "65vh" }}>
          {errorMsg && (
            <div
              role="alert"
              style={{
                marginBottom: "16px",
                padding: "10px 14px",
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid #ef4444",
                borderRadius: "6px",
                color: "#fca5a5",
                fontSize: "12px",
              }}
            >
              {errorMsg}
            </div>
          )}

          {step === 1 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--hud-text-secondary, #94a3b8)", lineHeight: 1.5 }}>
                Upload your base resume. ALEX extracts verified skills, work history, and achievements strictly without
                fabrication.
              </p>

              <div>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".txt,.pdf,.docx,.doc"
                  style={{ display: "none" }}
                  id="onboarding-resume-upload"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    width: "100%",
                    padding: "20px",
                    border: "2px dashed var(--hud-border-cyan, #38bdf8)",
                    borderRadius: "8px",
                    background: "rgba(14, 165, 233, 0.05)",
                    color: "var(--hud-text-primary, #f8fafc)",
                    cursor: "pointer",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "20px", marginBottom: "6px" }}>📄</div>
                  <div style={{ fontWeight: 600, fontSize: "13px" }}>
                    {resumeText ? `Loaded: ${fileName}` : "Click to select Resume (PDF, DOCX, TXT)"}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--hud-text-secondary, #94a3b8)", marginTop: "4px" }}>
                    Local processing only · Never shared without consent
                  </div>
                </button>
              </div>

              <div>
                <label
                  htmlFor="resume-paste-text"
                  style={{
                    display: "block",
                    fontSize: "12px",
                    fontFamily: "var(--hud-font-mono, monospace)",
                    color: "var(--hud-text-secondary, #94a3b8)",
                    marginBottom: "6px",
                  }}
                >
                  OR PASTE RESUME TEXT:
                </label>
                <textarea
                  id="resume-paste-text"
                  rows={5}
                  value={resumeText}
                  onChange={(e) => setResumeText(e.target.value)}
                  placeholder="Paste your plain text resume here..."
                  style={{
                    width: "100%",
                    background: "#090d16",
                    border: "1px solid #334155",
                    borderRadius: "6px",
                    padding: "10px",
                    color: "#f8fafc",
                    fontSize: "12px",
                    fontFamily: "var(--hud-font-mono, monospace)",
                  }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label
                    htmlFor="candidate-name"
                    style={{
                      display: "block",
                      fontSize: "11px",
                      fontFamily: "var(--hud-font-mono, monospace)",
                      color: "var(--hud-text-secondary, #94a3b8)",
                      marginBottom: "4px",
                    }}
                  >
                    FULL NAME:
                  </label>
                  <input
                    id="candidate-name"
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Alex Johnson"
                    style={{
                      width: "100%",
                      background: "#090d16",
                      border: "1px solid #334155",
                      borderRadius: "6px",
                      padding: "8px 12px",
                      color: "#f8fafc",
                      fontSize: "12px",
                    }}
                  />
                </div>
                <div>
                  <label
                    htmlFor="candidate-email"
                    style={{
                      display: "block",
                      fontSize: "11px",
                      fontFamily: "var(--hud-font-mono, monospace)",
                      color: "var(--hud-text-secondary, #94a3b8)",
                      marginBottom: "4px",
                    }}
                  >
                    EMAIL ADDRESS:
                  </label>
                  <input
                    id="candidate-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="e.g. alex@example.com"
                    style={{
                      width: "100%",
                      background: "#090d16",
                      border: "1px solid #334155",
                      borderRadius: "6px",
                      padding: "8px 12px",
                      color: "#f8fafc",
                      fontSize: "12px",
                    }}
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="candidate-location"
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontFamily: "var(--hud-font-mono, monospace)",
                    color: "var(--hud-text-secondary, #94a3b8)",
                    marginBottom: "4px",
                  }}
                >
                  CURRENT LOCATION:
                </label>
                <input
                  id="candidate-location"
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. San Francisco, CA / Remote"
                  style={{
                    width: "100%",
                    background: "#090d16",
                    border: "1px solid #334155",
                    borderRadius: "6px",
                    padding: "8px 12px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--hud-text-secondary, #94a3b8)", lineHeight: 1.5 }}>
                Define target positions and geography. The discovery scheduler will auto-scan matching Greenhouse,
                Lever, and RemoteOK feeds.
              </p>

              <div>
                <label
                  htmlFor="target-role-input"
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontFamily: "var(--hud-font-mono, monospace)",
                    color: "var(--hud-text-secondary, #94a3b8)",
                    marginBottom: "6px",
                  }}
                >
                  TARGET ROLES (PRESS ENTER TO ADD):
                </label>
                <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
                  <input
                    id="target-role-input"
                    type="text"
                    value={roleInput}
                    onChange={(e) => setRoleInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddRole())}
                    placeholder="e.g. Lead React Architect, Staff Engineer..."
                    style={{
                      flex: 1,
                      background: "#090d16",
                      border: "1px solid #334155",
                      borderRadius: "6px",
                      padding: "8px 12px",
                      color: "#f8fafc",
                      fontSize: "12px",
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleAddRole}
                    style={{
                      background: "rgba(14, 165, 233, 0.2)",
                      border: "1px solid var(--hud-border-cyan, #0ea5e9)",
                      color: "var(--hud-accent-cyan, #38bdf8)",
                      borderRadius: "6px",
                      padding: "0 16px",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    Add
                  </button>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {targetRoles.map((role) => (
                    <span
                      key={role}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        background: "rgba(14, 165, 233, 0.15)",
                        border: "1px solid var(--hud-border-cyan, #0ea5e9)",
                        color: "#f8fafc",
                        borderRadius: "16px",
                        padding: "4px 10px",
                        fontSize: "11px",
                      }}
                    >
                      {role}
                      <button
                        type="button"
                        onClick={() => handleRemoveRole(role)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#94a3b8",
                          cursor: "pointer",
                          padding: 0,
                        }}
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <label
                  htmlFor="seniority-select"
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontFamily: "var(--hud-font-mono, monospace)",
                    color: "var(--hud-text-secondary, #94a3b8)",
                    marginBottom: "4px",
                  }}
                >
                  TARGET SENIORITY LEVEL:
                </label>
                <select
                  id="seniority-select"
                  value={seniority}
                  onChange={(e) => setSeniority(e.target.value)}
                  style={{
                    width: "100%",
                    background: "#090d16",
                    border: "1px solid #334155",
                    borderRadius: "6px",
                    padding: "8px 12px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                >
                  <option value="Junior">Junior (0-2 years)</option>
                  <option value="Mid-Level">Mid-Level (3-5 years)</option>
                  <option value="Senior">Senior (5-8 years)</option>
                  <option value="Staff">Staff / Principal (8+ years)</option>
                  <option value="Lead">Lead / Management</option>
                </select>
              </div>

              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontFamily: "var(--hud-font-mono, monospace)",
                    color: "var(--hud-text-secondary, #94a3b8)",
                    marginBottom: "6px",
                  }}
                >
                  WORK MODALITY:
                </label>
                <div style={{ display: "flex", gap: "10px" }}>
                  {(["remote", "hybrid", "onsite"] as WorkModality[]).map((mod) => (
                    <label
                      key={mod}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "8px 14px",
                        border: "1px solid",
                        borderColor: modalities.includes(mod) ? "var(--hud-accent-cyan, #0ea5e9)" : "#334155",
                        borderRadius: "6px",
                        background: modalities.includes(mod) ? "rgba(14, 165, 233, 0.15)" : "#090d16",
                        color: modalities.includes(mod) ? "#f8fafc" : "#94a3b8",
                        fontSize: "12px",
                        cursor: "pointer",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={modalities.includes(mod)}
                        onChange={() => toggleModality(mod)}
                        style={{ display: "none" }}
                      />
                      <span>{mod.toUpperCase()}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label
                  htmlFor="target-location-input"
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontFamily: "var(--hud-font-mono, monospace)",
                    color: "var(--hud-text-secondary, #94a3b8)",
                    marginBottom: "6px",
                  }}
                >
                  TARGET GEOGRAPHIC HUBS:
                </label>
                <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
                  <input
                    id="target-location-input"
                    type="text"
                    value={locationInput}
                    onChange={(e) => setLocationInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddLocation())}
                    placeholder="e.g. Remote, San Francisco, London..."
                    style={{
                      flex: 1,
                      background: "#090d16",
                      border: "1px solid #334155",
                      borderRadius: "6px",
                      padding: "8px 12px",
                      color: "#f8fafc",
                      fontSize: "12px",
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleAddLocation}
                    style={{
                      background: "rgba(14, 165, 233, 0.2)",
                      border: "1px solid var(--hud-border-cyan, #0ea5e9)",
                      color: "var(--hud-accent-cyan, #38bdf8)",
                      borderRadius: "6px",
                      padding: "0 16px",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    Add
                  </button>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {targetLocations.map((loc) => (
                    <span
                      key={loc}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        background: "rgba(14, 165, 233, 0.15)",
                        border: "1px solid var(--hud-border-cyan, #0ea5e9)",
                        color: "#f8fafc",
                        borderRadius: "16px",
                        padding: "4px 10px",
                        fontSize: "11px",
                      }}
                    >
                      {loc}
                      <button
                        type="button"
                        onClick={() => handleRemoveLocation(loc)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#94a3b8",
                          cursor: "pointer",
                          padding: 0,
                        }}
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--hud-text-secondary, #94a3b8)", lineHeight: 1.5 }}>
                Configure salary filters and work authorization. ALEX scores opportunities against these thresholds to
                filter out non-viable roles.
              </p>

              <div>
                <label
                  htmlFor="min-salary-input"
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontFamily: "var(--hud-font-mono, monospace)",
                    color: "var(--hud-text-secondary, #94a3b8)",
                    marginBottom: "4px",
                  }}
                >
                  MINIMUM ANNUAL SALARY (USD):
                </label>
                <div style={{ position: "relative" }}>
                  <span
                    style={{
                      position: "absolute",
                      left: "12px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      color: "#94a3b8",
                      fontSize: "13px",
                    }}
                  >
                    $
                  </span>
                  <input
                    id="min-salary-input"
                    type="number"
                    step={5000}
                    value={minSalary}
                    onChange={(e) => setMinSalary(Number(e.target.value) || 0)}
                    style={{
                      width: "100%",
                      background: "#090d16",
                      border: "1px solid #334155",
                      borderRadius: "6px",
                      padding: "8px 12px 8px 28px",
                      color: "#f8fafc",
                      fontSize: "13px",
                    }}
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="work-auth-select"
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontFamily: "var(--hud-font-mono, monospace)",
                    color: "var(--hud-text-secondary, #94a3b8)",
                    marginBottom: "4px",
                  }}
                >
                  WORK AUTHORIZATION STATUS:
                </label>
                <select
                  id="work-auth-select"
                  value={workAuth}
                  onChange={(e) => setWorkAuth(e.target.value)}
                  style={{
                    width: "100%",
                    background: "#090d16",
                    border: "1px solid #334155",
                    borderRadius: "6px",
                    padding: "8px 12px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                >
                  <option value="US Citizen / Green Card">US Citizen / Permanent Resident (Green Card)</option>
                  <option value="Requires Visa Sponsorship">Requires Visa Sponsorship (H-1B, TN, etc.)</option>
                  <option value="EU / UK Citizen">EU / UK Work Authorized</option>
                  <option value="Canada Authorized">Canada Work Authorized</option>
                  <option value="Global Contractor">Global Independent Contractor (B2B / EoR)</option>
                  <option value="Other">Other / Open</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="notice-period-select"
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontFamily: "var(--hud-font-mono, monospace)",
                    color: "var(--hud-text-secondary, #94a3b8)",
                    marginBottom: "4px",
                  }}
                >
                  AVAILABILITY / NOTICE PERIOD:
                </label>
                <select
                  id="notice-period-select"
                  value={noticePeriod}
                  onChange={(e) => setNoticePeriod(e.target.value)}
                  style={{
                    width: "100%",
                    background: "#090d16",
                    border: "1px solid #334155",
                    borderRadius: "6px",
                    padding: "8px 12px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                >
                  <option value="Immediate">Immediate / Available Now</option>
                  <option value="2 Weeks">2 Weeks Notice</option>
                  <option value="1 Month">1 Month Notice</option>
                  <option value="2+ Months">2+ Months Notice</option>
                </select>
              </div>

              <div
                style={{
                  padding: "12px",
                  background: "rgba(32, 214, 160, 0.08)",
                  border: "1px solid rgba(32, 214, 160, 0.3)",
                  borderRadius: "6px",
                  fontSize: "12px",
                  color: "var(--hud-success, #20d6a0)",
                  lineHeight: 1.4,
                }}
              >
                ✓ All configuration is stored strictly in your local SQLite database. No credentials or career data are
                shared without explicit action.
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid #1e293b",
            background: "rgba(15, 23, 42, 0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {step > 1 ? (
            <button
              type="button"
              onClick={() => setStep((s) => (s - 1) as any)}
              disabled={saving}
              style={{
                background: "transparent",
                border: "1px solid #334155",
                color: "#94a3b8",
                borderRadius: "6px",
                padding: "8px 16px",
                fontSize: "12px",
                cursor: "pointer",
              }}
            >
              ← Back
            </button>
          ) : (
            <div />
          )}

          {step < 3 ? (
            <button
              type="button"
              onClick={() => setStep((s) => (s + 1) as any)}
              style={{
                background: "var(--hud-accent-cyan, #0ea5e9)",
                border: "none",
                color: "#ffffff",
                borderRadius: "6px",
                padding: "8px 20px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Continue to Step {step + 1} →
            </button>
          ) : (
            <button
              type="button"
              onClick={handleFinish}
              disabled={saving}
              style={{
                background: "var(--hud-success, #20d6a0)",
                border: "none",
                color: "#0f172a",
                borderRadius: "6px",
                padding: "8px 24px",
                fontSize: "12px",
                fontWeight: 700,
                cursor: saving ? "not-allowed" : "pointer",
                opacity: saving ? 0.7 : 1,
              }}
            >
              {saving ? "Saving..." : "Complete Setup & Launch Radar ✓"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
