import { useState } from "react";
import type { AdapterStatusReport, JobListing, WorkModality } from "../../types/jobHunting";

interface DiscoverViewProps {
  jobs: JobListing[];
  adapters: AdapterStatusReport[];
  onSelectJob: (jobId: string) => void;
  onNavigateTab: (tab: string) => void;
  onIngestLinkedInUrl: (url: string, title?: string, company?: string, modality?: string) => Promise<void>;
  onIngestLinkedInAlert: (alertText: string) => Promise<void>;
  onIngestGreenhouse: (boardToken: string, filterRole?: string) => Promise<void>;
  onIngestLever: (siteName: string, filterRole?: string) => Promise<void>;
  onIngestDirectUrl: (url: string, title?: string, company?: string, rawText?: string, modality?: string) => Promise<void>;
  onTriggerSearch: (query: string, location: string, modalities: string[]) => Promise<void>;
}

export function DiscoverView({
  jobs,
  adapters,
  onSelectJob,
  onNavigateTab,
  onIngestLinkedInUrl,
  onIngestLinkedInAlert,
  onIngestGreenhouse,
  onIngestLever,
  onIngestDirectUrl,
  onTriggerSearch,
}: DiscoverViewProps) {
  const [activeSourceTab, setActiveSourceTab] = useState<"linkedin_url" | "alert" | "greenhouse" | "lever" | "direct" | "search">("linkedin_url");
  const [busy, setBusy] = useState(false);
  const [filterModality, setFilterModality] = useState<string>("all");
  const [filterSource, setFilterSource] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Form states
  const [liUrl, setLiUrl] = useState("");
  const [liTitle, setLiTitle] = useState("");
  const [liCompany, setLiCompany] = useState("");
  const [liModality, setLiModality] = useState<WorkModality>("remote");

  const [alertText, setAlertText] = useState("");

  const [ghToken, setGhToken] = useState("");
  const [ghFilter, setGhFilter] = useState("software");

  const [leverSite, setLeverSite] = useState("");
  const [leverFilter, setLeverFilter] = useState("developer");

  const [directUrl, setDirectUrl] = useState("");
  const [directTitle, setDirectTitle] = useState("");
  const [directCompany, setDirectCompany] = useState("");
  const [directText, setDirectText] = useState("");

  const [searchRole, setSearchRole] = useState("Full Stack Developer");
  const [searchLoc, setSearchLoc] = useState("Worldwide");
  const [searchModalities, setSearchModalities] = useState<string[]>(["remote", "hybrid"]);

  async function handleLinkedInSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!liUrl) return;
    setBusy(true);
    try {
      await onIngestLinkedInUrl(liUrl, liTitle || undefined, liCompany || undefined, liModality);
      setLiUrl("");
      setLiTitle("");
      setLiCompany("");
    } finally {
      setBusy(false);
    }
  }

  async function handleAlertSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!alertText) return;
    setBusy(true);
    try {
      await onIngestLinkedInAlert(alertText);
      setAlertText("");
    } finally {
      setBusy(false);
    }
  }

  async function handleGreenhouseSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ghToken) return;
    setBusy(true);
    try {
      await onIngestGreenhouse(ghToken, ghFilter || undefined);
      setGhToken("");
    } finally {
      setBusy(false);
    }
  }

  async function handleLeverSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!leverSite) return;
    setBusy(true);
    try {
      await onIngestLever(leverSite, leverFilter || undefined);
      setLeverSite("");
    } finally {
      setBusy(false);
    }
  }

  async function handleDirectSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!directUrl) return;
    setBusy(true);
    try {
      await onIngestDirectUrl(directUrl, directTitle || undefined, directCompany || undefined, directText || undefined);
      setDirectUrl("");
      setDirectTitle("");
      setDirectCompany("");
      setDirectText("");
    } finally {
      setBusy(false);
    }
  }

  async function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await onTriggerSearch(searchRole, searchLoc, searchModalities);
    } finally {
      setBusy(false);
    }
  }

  // Filtered jobs list
  const filteredJobs = jobs.filter((job) => {
    if (filterModality !== "all" && job.modality !== filterModality) return false;
    if (filterSource !== "all" && !job.source.toLowerCase().includes(filterSource.toLowerCase())) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        job.title.toLowerCase().includes(q) ||
        job.company_name.toLowerCase().includes(q) ||
        job.location.toLowerCase().includes(q) ||
        job.required_skills.some((s) => s.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div>
      <div className="jh-header">
        <div className="jh-header-titles">
          <h2><span>🌐</span> MULTI-SOURCE JOB DISCOVERY ENGINE</h2>
          <p>Verified public adapters and user-supplied link ingestion. LinkedIn automation & scraping strictly prohibited.</p>
        </div>
      </div>

      {/* Source Ingestion Tabs */}
      <div className="jh-card">
        <div style={{ display: "flex", gap: "6px", borderBottom: "1px solid var(--hud-border)", paddingBottom: "10px", marginBottom: "14px", flexWrap: "wrap" }}>
          {[
            { id: "linkedin_url", label: "LinkedIn Job Link" },
            { id: "alert", label: "LinkedIn Alert Email" },
            { id: "greenhouse", label: "Greenhouse Board" },
            { id: "lever", label: "Lever Board" },
            { id: "direct", label: "Careers Page URL" },
            { id: "search", label: "Autonomous Search" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`jh-btn ${activeSourceTab === tab.id ? "jh-btn-primary" : "jh-btn-secondary"}`}
              style={{ padding: "4px 10px", fontSize: "11px" }}
              onClick={() => setActiveSourceTab(tab.id as any)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 1. LinkedIn URL Form */}
        {activeSourceTab === "linkedin_url" && (
          <form onSubmit={handleLinkedInSubmit}>
            <div style={{ fontSize: "12px", color: "var(--hud-text-secondary)", marginBottom: "10px" }}>
              Paste a public LinkedIn job URL directly. ALEX extracts the job ID and details without scraping or account automation.
            </div>
            <div className="jh-form-row">
              <div className="jh-input-group">
                <label>Job Posting URL *</label>
                <input
                  type="url"
                  className="jh-input"
                  placeholder="https://www.linkedin.com/jobs/view/1234567890"
                  value={liUrl}
                  onChange={(e) => setLiUrl(e.target.value)}
                  required
                />
              </div>
              <div className="jh-input-group">
                <label>Optional Title</label>
                <input
                  type="text"
                  className="jh-input"
                  placeholder="e.g. Senior React Developer"
                  value={liTitle}
                  onChange={(e) => setLiTitle(e.target.value)}
                />
              </div>
              <div className="jh-input-group">
                <label>Optional Company</label>
                <input
                  type="text"
                  className="jh-input"
                  placeholder="e.g. TechCorp"
                  value={liCompany}
                  onChange={(e) => setLiCompany(e.target.value)}
                />
              </div>
              <div className="jh-input-group" style={{ maxWidth: "140px" }}>
                <label>Modality</label>
                <select
                  className="jh-select"
                  value={liModality}
                  onChange={(e) => setLiModality(e.target.value as WorkModality)}
                >
                  <option value="remote">Remote</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="onsite">On-Site</option>
                </select>
              </div>
            </div>
            <button type="submit" className="jh-btn jh-btn-primary" disabled={busy}>
              {busy ? "Ingesting..." : "Ingest LinkedIn URL"}
            </button>
          </form>
        )}

        {/* 2. Alert Email Form */}
        {activeSourceTab === "alert" && (
          <form onSubmit={handleAlertSubmit}>
            <div style={{ fontSize: "12px", color: "var(--hud-text-secondary)", marginBottom: "10px" }}>
              Paste the text or HTML body of a LinkedIn Job Alert email received in your inbox. ALEX extracts all opportunities into tracked listings.
            </div>
            <div className="jh-input-group" style={{ marginBottom: "12px" }}>
              <label>Alert Email Content *</label>
              <textarea
                className="jh-textarea"
                style={{ height: "120px" }}
                placeholder="Paste alert email body text or job listing snippet here..."
                value={alertText}
                onChange={(e) => setAlertText(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="jh-btn jh-btn-primary" disabled={busy}>
              {busy ? "Parsing Alert..." : "Parse & Ingest Alert"}
            </button>
          </form>
        )}

        {/* 3. Greenhouse Board Form */}
        {activeSourceTab === "greenhouse" && (
          <form onSubmit={handleGreenhouseSubmit}>
            <div style={{ fontSize: "12px", color: "var(--hud-text-secondary)", marginBottom: "10px" }}>
              Fetch live public job listings directly from an authorized Greenhouse company job board token.
            </div>
            <div className="jh-form-row">
              <div className="jh-input-group">
                <label>Company Board Token *</label>
                <input
                  type="text"
                  className="jh-input"
                  placeholder="e.g. airbnb, stripe, datadog"
                  value={ghToken}
                  onChange={(e) => setGhToken(e.target.value)}
                  required
                />
              </div>
              <div className="jh-input-group">
                <label>Filter Keyword / Role</label>
                <input
                  type="text"
                  className="jh-input"
                  placeholder="e.g. software, full stack, frontend"
                  value={ghFilter}
                  onChange={(e) => setGhFilter(e.target.value)}
                />
              </div>
            </div>
            <button type="submit" className="jh-btn jh-btn-primary" disabled={busy}>
              {busy ? "Fetching Board..." : "Ingest Greenhouse Board"}
            </button>
          </form>
        )}

        {/* 4. Lever Board Form */}
        {activeSourceTab === "lever" && (
          <form onSubmit={handleLeverSubmit}>
            <div style={{ fontSize: "12px", color: "var(--hud-text-secondary)", marginBottom: "10px" }}>
              Fetch live public postings directly from a company Lever career board site name.
            </div>
            <div className="jh-form-row">
              <div className="jh-input-group">
                <label>Company Site Name *</label>
                <input
                  type="text"
                  className="jh-input"
                  placeholder="e.g. netflix, figma, spotify"
                  value={leverSite}
                  onChange={(e) => setLeverSite(e.target.value)}
                  required
                />
              </div>
              <div className="jh-input-group">
                <label>Filter Keyword / Role</label>
                <input
                  type="text"
                  className="jh-input"
                  placeholder="e.g. developer, react, node"
                  value={leverFilter}
                  onChange={(e) => setLeverFilter(e.target.value)}
                />
              </div>
            </div>
            <button type="submit" className="jh-btn jh-btn-primary" disabled={busy}>
              {busy ? "Fetching Board..." : "Ingest Lever Board"}
            </button>
          </form>
        )}

        {/* 5. Direct Careers Page Form */}
        {activeSourceTab === "direct" && (
          <form onSubmit={handleDirectSubmit}>
            <div style={{ fontSize: "12px", color: "var(--hud-text-secondary)", marginBottom: "10px" }}>
              Ingest a direct job posting from any public company careers portal or ATS link.
            </div>
            <div className="jh-form-row">
              <div className="jh-input-group">
                <label>Careers URL *</label>
                <input
                  type="url"
                  className="jh-input"
                  placeholder="https://company.com/careers/job-id"
                  value={directUrl}
                  onChange={(e) => setDirectUrl(e.target.value)}
                  required
                />
              </div>
              <div className="jh-input-group">
                <label>Role Title</label>
                <input
                  type="text"
                  className="jh-input"
                  placeholder="e.g. Full Stack Developer"
                  value={directTitle}
                  onChange={(e) => setDirectTitle(e.target.value)}
                />
              </div>
              <div className="jh-input-group">
                <label>Company Name</label>
                <input
                  type="text"
                  className="jh-input"
                  placeholder="e.g. Global Tech"
                  value={directCompany}
                  onChange={(e) => setDirectCompany(e.target.value)}
                />
              </div>
            </div>
            <div className="jh-input-group" style={{ marginBottom: "12px" }}>
              <label>Optional Description Text / Snippet</label>
              <textarea
                className="jh-textarea"
                placeholder="Paste job description text if behind portal restrictions..."
                value={directText}
                onChange={(e) => setDirectText(e.target.value)}
              />
            </div>
            <button type="submit" className="jh-btn jh-btn-primary" disabled={busy}>
              {busy ? "Ingesting..." : "Ingest Careers Listing"}
            </button>
          </form>
        )}

        {/* 6. Autonomous Search Form */}
        {activeSourceTab === "search" && (
          <form onSubmit={handleSearchSubmit}>
            <div style={{ fontSize: "12px", color: "var(--hud-text-secondary)", marginBottom: "10px" }}>
              Execute an authorized search across company career portals, RemoteOK, and public web listings.
            </div>
            <div className="jh-form-row">
              <div className="jh-input-group">
                <label>Target Role</label>
                <input
                  type="text"
                  className="jh-input"
                  value={searchRole}
                  onChange={(e) => setSearchRole(e.target.value)}
                  required
                />
              </div>
              <div className="jh-input-group">
                <label>Location</label>
                <input
                  type="text"
                  className="jh-input"
                  value={searchLoc}
                  onChange={(e) => setSearchLoc(e.target.value)}
                  required
                />
              </div>
              <div className="jh-input-group">
                <label>Modalities</label>
                <div style={{ display: "flex", gap: "8px", marginTop: "6px" }}>
                  {["remote", "hybrid", "onsite"].map((m) => (
                    <label key={m} style={{ fontSize: "11px", display: "flex", alignItems: "center", gap: "4px" }}>
                      <input
                        type="checkbox"
                        checked={searchModalities.includes(m)}
                        onChange={(e) => {
                          if (e.target.checked) setSearchModalities([...searchModalities, m]);
                          else setSearchModalities(searchModalities.filter((x) => x !== m));
                        }}
                      />
                      {m.toUpperCase()}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <button type="submit" className="jh-btn jh-btn-primary" disabled={busy}>
              {busy ? "Searching Web..." : "Run Autonomous Discovery"}
            </button>
          </form>
        )}
      </div>

      {/* Discovered Listings Table / Filter Bar */}
      <div className="jh-card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px", marginBottom: "12px" }}>
          <div style={{ fontFamily: "var(--hud-font-mono)", fontSize: "13px", fontWeight: 700 }}>
            DISCOVERED JOBS ({filteredJobs.length} of {jobs.length})
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <input
              type="text"
              className="jh-input search-input-field"
              style={{ padding: "4px 8px", fontSize: "11px", width: "180px" }}
              placeholder="Search title, company, skill..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <select
              className="jh-select"
              style={{ padding: "4px 8px", fontSize: "11px" }}
              value={filterModality}
              onChange={(e) => setFilterModality(e.target.value)}
            >
              <option value="all">All Modalities</option>
              <option value="remote">Remote Only</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">On-Site</option>
            </select>
            <select
              className="jh-select"
              style={{ padding: "4px 8px", fontSize: "11px" }}
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
            >
              <option value="all">All Sources</option>
              <option value="linkedin">LinkedIn</option>
              <option value="indeed">Indeed</option>
              <option value="greenhouse">Greenhouse</option>
              <option value="lever">Lever</option>
              <option value="public_api">RemoteOK</option>
              <option value="company_careers">Company Careers</option>
            </select>
          </div>
        </div>

        {filteredJobs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "30px 10px", color: "var(--hud-text-muted)" }}>
            No jobs match the current filters.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {filteredJobs.map((job) => (
              <div
                key={job.id}
                className="jh-card"
                style={{ margin: 0, padding: "12px", background: "var(--hud-bg-secondary)" }}
              >
                <div className="jh-card-header">
                  <div>
                    <h3
                      className="jh-card-title"
                      style={{ cursor: "pointer", color: "var(--hud-accent)" }}
                      onClick={() => { onSelectJob(job.id); onNavigateTab("details"); }}
                    >
                      {job.title}
                    </h3>
                    <div className="jh-card-company">{job.company_name}</div>
                  </div>
                  <div style={{ display: "flex", gap: "6px" }}>
                    <span className="jh-badge">{job.modality}</span>
                    <span className="jh-badge" style={{ color: "var(--hud-accent-secondary)" }}>
                      {job.source.replace("_", " ")}
                    </span>
                  </div>
                </div>

                <div className="jh-card-meta">
                  <span>📍 {job.location}</span>
                  <span>⏳ Experience: {job.experience_required_min}-{job.experience_required_max} yrs</span>
                  {job.is_expired && <span className="jh-badge jh-badge-match-low">EXPIRED</span>}
                </div>

                {job.required_skills.length > 0 && (
                  <div className="jh-tag-list">
                    {job.required_skills.slice(0, 6).map((skill) => (
                      <span key={skill} className="jh-tag">{skill}</span>
                    ))}
                  </div>
                )}

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "10px" }}>
                  <button
                    type="button"
                    className="jh-btn jh-btn-secondary"
                    style={{ padding: "4px 10px", fontSize: "11px" }}
                    onClick={() => { onSelectJob(job.id); onNavigateTab("details"); }}
                  >
                    View Details
                  </button>
                  <button
                    type="button"
                    className="jh-btn jh-btn-primary"
                    style={{ padding: "4px 10px", fontSize: "11px" }}
                    onClick={() => { onSelectJob(job.id); onNavigateTab("analysis"); }}
                  >
                    Analyze Match
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* External Adapter Telemetry */}
      <div className="jh-card" style={{ marginTop: "16px" }}>
        <div style={{ fontFamily: "var(--hud-font-mono)", fontSize: "12px", color: "var(--hud-accent)", marginBottom: "8px" }}>
          ▸ EXTERNAL ADAPTER CONNECTIVITY STATUS
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "10px" }}>
          {(Array.isArray(adapters) ? adapters : []).map((a) => (
            <div key={a.adapter_name} style={{ padding: "8px 10px", background: "rgba(0,0,0,0.3)", borderRadius: "4px", fontSize: "11px", fontFamily: "var(--hud-font-mono)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>{a.adapter_name}</strong>
                <span style={{ color: a.is_available ? "var(--hud-success)" : "var(--hud-warning)" }}>
                  {a.is_available ? "● READY" : "○ CONFIG REQ"}
                </span>
              </div>
              <div style={{ fontSize: "10px", color: "var(--hud-text-muted)", marginTop: "4px" }}>
                {a.configuration_hint}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

