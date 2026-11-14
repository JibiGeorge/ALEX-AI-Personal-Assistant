import { useMemo, useState } from "react";
import type { CompatibilityScore, JobListing } from "../../types/jobHunting";

interface JobLocationMapViewProps {
  jobs: JobListing[];
  scores: Record<string, CompatibilityScore>;
  onSelectJob: (jobId: string) => void;
  onNavigateTab: (tab: string) => void;
  onTailorResume?: (jobId: string) => Promise<void>;
}

type ViewMode = "split" | "map" | "list";

interface CityCluster {
  cityName: string;
  country: string;
  state?: string | null;
  lat: number;
  lng: number;
  jobs: JobListing[];
  hasHybrid: boolean;
  hasOnsite: boolean;
  hasRemote: boolean;
}

export function JobLocationMapView({
  jobs,
  scores,
  onSelectJob,
  onNavigateTab,
  onTailorResume,
}: JobLocationMapViewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("split");
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Filters
  const [selectedCountry, setSelectedCountry] = useState<string>("all");
  const [selectedModality, setSelectedModality] = useState<string>("all");
  const [minMatchThreshold, setMinMatchThreshold] = useState<number>(0);
  const [searchFilter, setSearchFilter] = useState<string>("");

  // Selected City & Selected Job for quick inspection
  const [activeCityName, setActiveCityName] = useState<string | null>(null);

  // Filter jobs based on user criteria
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      if (selectedModality !== "all" && job.modality !== selectedModality) return false;
      if (selectedCountry !== "all" && (job.country || "").toLowerCase() !== selectedCountry.toLowerCase()) return false;
      const score = scores[job.id]?.match_percentage || 0;
      if (minMatchThreshold > 0 && score < minMatchThreshold) return false;
      if (searchFilter.trim()) {
        const q = searchFilter.toLowerCase();
        const matchesTitle = job.title.toLowerCase().includes(q);
        const matchesCompany = job.company_name.toLowerCase().includes(q);
        const matchesLoc = job.location.toLowerCase().includes(q);
        const matchesSkills = job.required_skills.some((s) => s.toLowerCase().includes(q));
        if (!matchesTitle && !matchesCompany && !matchesLoc && !matchesSkills) return false;
      }
      return true;
    });
  }, [jobs, selectedModality, selectedCountry, minMatchThreshold, searchFilter, scores]);

  // Separate jobs with verifiable coordinates from pure remote jobs
  const { cityClusters, remoteJobs, countriesList } = useMemo(() => {
    const clusters: Record<string, CityCluster> = {};
    const remoteOnly: JobListing[] = [];
    const countries = new Set<string>();

    for (const job of filteredJobs) {
      if (job.country) {
        countries.add(job.country);
      }
      if (job.latitude !== null && job.latitude !== undefined && job.longitude !== null && job.longitude !== undefined) {
        const key = `${job.city || "Hub"}_${job.country || ""}`;
        if (!clusters[key]) {
          clusters[key] = {
            cityName: job.city || job.location,
            country: job.country || "Global",
            state: job.state,
            lat: job.latitude,
            lng: job.longitude,
            jobs: [],
            hasHybrid: false,
            hasOnsite: false,
            hasRemote: false,
          };
        }
        clusters[key].jobs.push(job);
        if (job.modality === "hybrid") clusters[key].hasHybrid = true;
        if (job.modality === "onsite") clusters[key].hasOnsite = true;
        if (job.modality === "remote") clusters[key].hasRemote = true;
      } else {
        remoteOnly.push(job);
      }
    }

    return {
      cityClusters: Object.values(clusters),
      remoteJobs: remoteOnly,
      countriesList: Array.from(countries).sort(),
    };
  }, [filteredJobs]);

  const activeCluster = useMemo(() => {
    if (!activeCityName) return cityClusters[0] || null;
    return cityClusters.find((c) => c.cityName === activeCityName) || null;
  }, [cityClusters, activeCityName]);

  // SVG Map dimensions
  const mapWidth = 900;
  const mapHeight = 460;

  // Equirectangular Projection
  function projectCoordinates(lat: number, lng: number) {
    const x = ((lng + 180) * (mapWidth / 360));
    const y = (((90 - lat) * (mapHeight / 180)));
    return { x, y };
  }

  function handleMouseDown(e: React.MouseEvent) {
    setIsPanning(true);
    setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
  }

  function handleMouseMove(e: React.MouseEvent) {
    if (!isPanning) return;
    setPanOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  }

  function handleMouseUp() {
    setIsPanning(false);
  }

  function handleZoomIn() {
    setZoomLevel((z) => Math.min(3.5, z + 0.35));
  }

  function handleZoomOut() {
    setZoomLevel((z) => Math.max(0.85, z - 0.35));
  }

  function handleResetMap() {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
    setActiveCityName(null);
  }

  return (
    <div className="jh-map-container" data-testid="job-location-map-view">
      {/* Header & View Switcher */}
      <div className="jh-header" style={{ marginBottom: "0.85rem" }}>
        <div className="jh-header-titles">
          <h2><span>🌐</span> INTERACTIVE JOB LOCATION MAP & GEO RADAR</h2>
          <p>
            Verifiable geographic clusters for matching opportunities. Pure remote positions segregated into verified remote radar.
          </p>
        </div>

        {/* View Mode Switcher */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <div className="jh-view-mode-pill-group" role="group" aria-label="Map Display Modes">
            <button
              type="button"
              className={`jh-btn ${viewMode === "split" ? "jh-btn-primary" : "jh-btn-secondary"}`}
              style={{ fontSize: "0.75rem", padding: "0.35rem 0.75rem" }}
              onClick={() => setViewMode("split")}
            >
              ◫ Split View
            </button>
            <button
              type="button"
              className={`jh-btn ${viewMode === "map" ? "jh-btn-primary" : "jh-btn-secondary"}`}
              style={{ fontSize: "0.75rem", padding: "0.35rem 0.75rem" }}
              onClick={() => setViewMode("map")}
            >
              🗺️ Map View
            </button>
            <button
              type="button"
              className={`jh-btn ${viewMode === "list" ? "jh-btn-primary" : "jh-btn-secondary"}`}
              style={{ fontSize: "0.75rem", padding: "0.35rem 0.75rem" }}
              onClick={() => setViewMode("list")}
            >
              📋 List View
            </button>
          </div>
        </div>
      </div>

      {/* Advanced Filter Ribbon */}
      <div className="jh-filter-bar" style={{ display: "flex", flexWrap: "wrap", gap: "0.6rem", alignItems: "center", marginBottom: "1rem" }}>
        <input
          type="text"
          placeholder="Filter by title, company, skills..."
          className="jh-input"
          style={{ width: "220px", fontSize: "0.8rem", padding: "0.4rem 0.75rem" }}
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
        />

        <select
          className="jh-input"
          style={{ width: "auto", fontSize: "0.8rem", padding: "0.4rem 0.75rem" }}
          value={selectedCountry}
          onChange={(e) => setSelectedCountry(e.target.value)}
        >
          <option value="all">🌍 All Countries</option>
          {countriesList.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        <select
          className="jh-input"
          style={{ width: "auto", fontSize: "0.8rem", padding: "0.4rem 0.75rem" }}
          value={selectedModality}
          onChange={(e) => setSelectedModality(e.target.value)}
        >
          <option value="all">🏢 All Modalities</option>
          <option value="remote">💻 Remote Only</option>
          <option value="hybrid">🟣 Hybrid Only</option>
          <option value="onsite">🏢 On-site Only</option>
        </select>

        <select
          className="jh-input"
          style={{ width: "auto", fontSize: "0.8rem", padding: "0.4rem 0.75rem" }}
          value={minMatchThreshold}
          onChange={(e) => setMinMatchThreshold(Number(e.target.value))}
        >
          <option value={0}>🎯 Any Match Score</option>
          <option value={85}>⭐ Excellent (≥85%)</option>
          <option value={70}>✨ Good Match (≥70%)</option>
          <option value={50}>⚡ Potential (≥50%)</option>
        </select>

        {(searchFilter || selectedCountry !== "all" || selectedModality !== "all" || minMatchThreshold > 0) && (
          <button
            type="button"
            className="jh-btn jh-btn-secondary"
            style={{ fontSize: "0.75rem", padding: "0.35rem 0.6rem" }}
            onClick={() => {
              setSearchFilter("");
              setSelectedCountry("all");
              setSelectedModality("all");
              setMinMatchThreshold(0);
            }}
          >
            Clear Filters
          </button>
        )}

        <div style={{ marginLeft: "auto", fontSize: "0.75rem", color: "var(--hud-cyan-bright)" }}>
          Showing <strong>{filteredJobs.length}</strong> matching roles ({cityClusters.length} geographical hubs, {remoteJobs.length} remote)
        </div>
      </div>

      {/* Main Layout Stage */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: viewMode === "split" ? "1.3fr 1fr" : "1fr",
          gap: "1.2rem",
          alignItems: "start",
        }}
      >
        {/* MAP SECTION */}
        {(viewMode === "map" || viewMode === "split") && (
          <div
            className="jh-map-viewport"
            style={{
              position: "relative",
              border: "1px solid rgba(0, 229, 255, 0.4)",
              borderRadius: "10px",
              background: "radial-gradient(ellipse at center, rgba(3, 24, 38, 0.95) 0%, rgba(1, 9, 15, 0.98) 100%)",
              boxShadow: "inset 0 0 40px rgba(0, 229, 255, 0.08), 0 0 25px rgba(0, 0, 0, 0.7)",
              overflow: "hidden",
              height: viewMode === "split" ? "480px" : "560px",
              cursor: isPanning ? "grabbing" : "grab",
              userSelect: "none",
            }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            {/* Map Controls Overlay */}
            <div
              style={{
                position: "absolute",
                top: "12px",
                right: "12px",
                zIndex: 10,
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <button
                type="button"
                className="jh-btn jh-btn-secondary"
                style={{ width: "32px", height: "32px", padding: 0, fontSize: "1.1rem" }}
                onClick={handleZoomIn}
                title="Zoom In"
              >
                +
              </button>
              <button
                type="button"
                className="jh-btn jh-btn-secondary"
                style={{ width: "32px", height: "32px", padding: 0, fontSize: "1.1rem" }}
                onClick={handleZoomOut}
                title="Zoom Out"
              >
                -
              </button>
              <button
                type="button"
                className="jh-btn jh-btn-secondary"
                style={{ width: "32px", height: "32px", padding: 0, fontSize: "0.7rem" }}
                onClick={handleResetMap}
                title="Reset View"
              >
                ↺
              </button>
            </div>

            {/* Map Legend */}
            <div
              style={{
                position: "absolute",
                bottom: "10px",
                left: "12px",
                zIndex: 10,
                background: "rgba(2, 11, 18, 0.85)",
                padding: "6px 12px",
                borderRadius: "6px",
                border: "1px solid rgba(0, 229, 255, 0.25)",
                fontSize: "0.7rem",
                display: "flex",
                gap: "12px",
                alignItems: "center",
              }}
            >
              <span style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#00E5FF", boxShadow: "0 0 6px #00E5FF" }} />
                Verified Hub
              </span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#c084fc", boxShadow: "0 0 6px #c084fc" }} />
                Hybrid Hub
              </span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#fbbf24", boxShadow: "0 0 6px #fbbf24" }} />
                On-site Hub
              </span>
            </div>

            {/* SVG Interactive Canvas */}
            <svg
              width="100%"
              height="100%"
              viewBox={`0 0 ${mapWidth} ${mapHeight}`}
              style={{
                transform: `scale(${zoomLevel}) translate(${panOffset.x / zoomLevel}px, ${panOffset.y / zoomLevel}px)`,
                transformOrigin: "center center",
                transition: isPanning ? "none" : "transform 0.15s ease-out",
              }}
            >
              <defs>
                {/* Holographic Radar Pulse Animation */}
                <radialGradient id="hubGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#00E5FF" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#00E5FF" stopOpacity="0" />
                </radialGradient>
                <pattern id="radarGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(0, 229, 255, 0.08)" strokeWidth="0.8" />
                </pattern>
              </defs>

              {/* Grid Background */}
              <rect width={mapWidth} height={mapHeight} fill="url(#radarGrid)" />

              {/* Stylized Continents Outlines */}
              {/* North America */}
              <path
                d="M 120 70 Q 180 50 250 80 Q 280 120 260 170 Q 220 220 180 230 Q 150 180 130 140 Z"
                fill="rgba(0, 229, 255, 0.05)"
                stroke="rgba(0, 229, 255, 0.22)"
                strokeWidth="1.2"
              />
              {/* South America */}
              <path
                d="M 230 240 Q 280 250 290 310 Q 270 380 240 420 Q 210 350 220 280 Z"
                fill="rgba(0, 229, 255, 0.05)"
                stroke="rgba(0, 229, 255, 0.22)"
                strokeWidth="1.2"
              />
              {/* Europe */}
              <path
                d="M 430 70 Q 480 60 520 90 Q 510 140 460 150 Q 420 130 430 70 Z"
                fill="rgba(0, 229, 255, 0.05)"
                stroke="rgba(0, 229, 255, 0.22)"
                strokeWidth="1.2"
              />
              {/* Africa */}
              <path
                d="M 440 160 Q 510 170 520 240 Q 490 330 460 340 Q 420 260 440 160 Z"
                fill="rgba(0, 229, 255, 0.05)"
                stroke="rgba(0, 229, 255, 0.22)"
                strokeWidth="1.2"
              />
              {/* Asia */}
              <path
                d="M 530 60 Q 680 50 780 100 Q 810 180 730 240 Q 640 220 570 170 Q 530 110 530 60 Z"
                fill="rgba(0, 229, 255, 0.05)"
                stroke="rgba(0, 229, 255, 0.22)"
                strokeWidth="1.2"
              />
              {/* Australia */}
              <path
                d="M 720 290 Q 800 280 820 340 Q 770 380 710 350 Z"
                fill="rgba(0, 229, 255, 0.05)"
                stroke="rgba(0, 229, 255, 0.22)"
                strokeWidth="1.2"
              />

              {/* Equator and Meridian Guide Lines */}
              <line x1="0" y1={mapHeight / 2} x2={mapWidth} y2={mapHeight / 2} stroke="rgba(0, 229, 255, 0.15)" strokeDasharray="4 4" />
              <line x1={mapWidth / 2} y1="0" x2={mapWidth / 2} y2={mapHeight} stroke="rgba(0, 229, 255, 0.15)" strokeDasharray="4 4" />

              {/* CITY MARKERS */}
              {cityClusters.map((cluster) => {
                const { x, y } = projectCoordinates(cluster.lat, cluster.lng);
                const isSelected = activeCityName === cluster.cityName;
                const markerColor = cluster.hasHybrid ? "#c084fc" : cluster.hasOnsite ? "#fbbf24" : "#00E5FF";

                return (
                  <g
                    key={cluster.cityName}
                    transform={`translate(${x}, ${y})`}
                    style={{ cursor: "pointer" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveCityName(cluster.cityName);
                      if (cluster.jobs[0]) {
                        onSelectJob(cluster.jobs[0].id);
                      }
                    }}
                  >
                    {/* Pulsing radar ring */}
                    <circle
                      r={isSelected ? 18 : 12}
                      fill="none"
                      stroke={markerColor}
                      strokeWidth={isSelected ? 2 : 1.2}
                      opacity={isSelected ? 0.9 : 0.6}
                    />

                    {/* Central pin circle */}
                    <circle
                      r={isSelected ? 9 : 7}
                      fill={markerColor}
                      opacity={0.95}
                    />

                    {/* Job Count inside marker */}
                    <text
                      textAnchor="middle"
                      dy="3.5"
                      fill="#020B10"
                      fontSize="9"
                      fontWeight="bold"
                    >
                      {cluster.jobs.length}
                    </text>

                    {/* City Name label */}
                    <text
                      y={-14}
                      textAnchor="middle"
                      fill={isSelected ? "#ffffff" : "rgba(224, 247, 250, 0.85)"}
                      fontSize={isSelected ? "11" : "9.5"}
                      fontWeight={isSelected ? "bold" : "normal"}
                      style={{
                        paintOrder: "stroke",
                        stroke: "rgba(2, 11, 18, 0.95)",
                        strokeWidth: "2.5px",
                        strokeLinejoin: "round",
                      }}
                    >
                      {cluster.cityName}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        )}

        {/* LIST & DETAILS DRAWER SECTION */}
        {(viewMode === "list" || viewMode === "split") && (
          <div className="jh-map-list-pane" style={{ maxHeight: "560px", overflowY: "auto" }}>
            {/* Active City Hub Highlight */}
            {activeCluster && (
              <div
                className="jh-card"
                style={{
                  marginBottom: "1rem",
                  borderColor: "rgba(0, 229, 255, 0.6)",
                  background: "linear-gradient(135deg, rgba(0, 229, 255, 0.08) 0%, rgba(2, 11, 18, 0.9) 100%)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: "1.05rem", color: "var(--hud-cyan-bright)" }}>
                      📍 {activeCluster.cityName}, {activeCluster.country}
                    </h3>
                    <p style={{ margin: "4px 0 0 0", fontSize: "0.75rem", color: "var(--hud-text-secondary)" }}>
                      {activeCluster.jobs.length} verifiable opportunity{activeCluster.jobs.length > 1 ? "ies" : ""} in this regional hub
                    </p>
                  </div>
                  <span className="jh-badge jh-badge-source">VERIFIED HUB</span>
                </div>

                <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                  {activeCluster.jobs.map((job) => {
                    const score = scores[job.id]?.match_percentage;
                    return (
                      <div
                        key={job.id}
                        className="jh-card"
                        style={{
                          padding: "0.6rem 0.8rem",
                          background: "rgba(2, 15, 24, 0.7)",
                          border: "1px solid rgba(0, 229, 255, 0.2)",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <div>
                            <strong style={{ fontSize: "0.85rem", color: "#e0f7fa" }}>{job.title}</strong>
                            <div style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)" }}>
                              {job.company_name} · <span style={{ textTransform: "uppercase" }}>{job.modality}</span>
                            </div>
                          </div>
                          {score !== undefined && (
                            <span className={`jh-badge ${score >= 80 ? "jh-badge-high" : score >= 60 ? "jh-badge-med" : "jh-badge-low"}`}>
                              {score}% MATCH
                            </span>
                          )}
                        </div>

                        {job.required_skills && job.required_skills.length > 0 && (
                          <div style={{ marginTop: "0.4rem", display: "flex", flexWrap: "wrap", gap: "4px" }}>
                            {job.required_skills.slice(0, 4).map((s) => (
                              <span key={s} className="jh-tag" style={{ fontSize: "0.65rem", padding: "1px 6px" }}>
                                {s}
                              </span>
                            ))}
                          </div>
                        )}

                        <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
                          <button
                            type="button"
                            className="jh-btn jh-btn-secondary"
                            style={{ fontSize: "0.7rem", padding: "0.25rem 0.55rem" }}
                            onClick={() => {
                              onSelectJob(job.id);
                              onNavigateTab("details");
                            }}
                          >
                            Inspect Specs 📋
                          </button>
                          {job.source_url && (
                            <a
                              href={job.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="jh-btn jh-btn-primary"
                              style={{ fontSize: "0.7rem", padding: "0.25rem 0.55rem", textDecoration: "none" }}
                            >
                              Apply Now ↗
                            </a>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* General Opportunity List */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--hud-text-secondary)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                All Filtered Opportunities ({filteredJobs.length})
              </div>

              {filteredJobs.length === 0 ? (
                <div className="jh-empty-state">
                  <h3>No opportunities matching geographical filters</h3>
                  <p>Try resetting the country or modality filters above.</p>
                </div>
              ) : (
                filteredJobs.map((job) => {
                  const score = scores[job.id]?.match_percentage;
                  return (
                    <div
                      key={job.id}
                      className="jh-job-card"
                      onClick={() => onSelectJob(job.id)}
                      style={{ cursor: "pointer" }}
                    >
                      <div className="jh-job-header">
                        <div>
                          <div className="jh-job-title">{job.title}</div>
                          <div className="jh-job-company">
                            {job.company_name} · 📍 {job.location} ({job.modality})
                          </div>
                        </div>
                        {score !== undefined && (
                          <span className={`jh-badge ${score >= 80 ? "jh-badge-high" : score >= 60 ? "jh-badge-med" : "jh-badge-low"}`}>
                            {score}%
                          </span>
                        )}
                      </div>

                      <div className="jh-job-tags">
                        <span className="jh-tag" style={{ textTransform: "capitalize" }}>{job.modality}</span>
                        {job.source && <span className="jh-tag">{job.source.replace("_", " ")}</span>}
                        {job.required_skills.slice(0, 3).map((s) => (
                          <span key={s} className="jh-tag">{s}</span>
                        ))}
                      </div>

                      <div className="jh-job-actions">
                        <button
                          type="button"
                          className="jh-btn jh-btn-secondary"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectJob(job.id);
                            onNavigateTab("analysis");
                          }}
                        >
                          Compatibility
                        </button>
                        {onTailorResume && (
                          <button
                            type="button"
                            className="jh-btn jh-btn-secondary"
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectJob(job.id);
                              void onTailorResume(job.id);
                              onNavigateTab("resume-studio");
                            }}
                          >
                            Tailor 📄
                          </button>
                        )}
                        {job.source_url && (
                          <a
                            href={job.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="jh-btn jh-btn-primary"
                            onClick={(e) => e.stopPropagation()}
                            style={{ textDecoration: "none" }}
                          >
                            Apply ↗
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* VERIFIABLE REMOTE OPPORTUNITIES DOCK */}
      {remoteJobs.length > 0 && (
        <div
          className="jh-remote-dock"
          style={{
            marginTop: "1.5rem",
            padding: "1rem",
            borderRadius: "10px",
            border: "1px solid rgba(0, 229, 255, 0.35)",
            background: "rgba(2, 11, 18, 0.9)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span style={{ fontSize: "1.1rem" }}>💻</span>
              <strong style={{ fontSize: "0.9rem", color: "var(--hud-cyan-bright)" }}>
                VERIFIED REMOTE OPPORTUNITIES (NO PHYSICAL COORDINATES)
              </strong>
              <span className="jh-badge jh-badge-source">{remoteJobs.length} ACTIVE</span>
            </div>
            <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--hud-text-secondary)" }}>
              Locations without verifiable physical hubs are kept off the physical map projection.
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: "0.75rem",
            }}
          >
            {remoteJobs.slice(0, 6).map((job) => {
              const score = scores[job.id]?.match_percentage;
              return (
                <div
                  key={job.id}
                  className="jh-card"
                  style={{
                    padding: "0.6rem 0.8rem",
                    background: "rgba(3, 20, 32, 0.7)",
                    border: "1px solid rgba(0, 229, 255, 0.2)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <div>
                      <strong style={{ fontSize: "0.85rem", color: "#e0f7fa" }}>{job.title}</strong>
                      <div style={{ fontSize: "0.75rem", color: "var(--hud-text-secondary)" }}>
                        {job.company_name} · 🌐 Worldwide / Remote
                      </div>
                    </div>
                    {score !== undefined && (
                      <span className={`jh-badge ${score >= 80 ? "jh-badge-high" : "jh-badge-med"}`}>
                        {score}%
                      </span>
                    )}
                  </div>
                  <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.4rem" }}>
                    <button
                      type="button"
                      className="jh-btn jh-btn-secondary"
                      style={{ fontSize: "0.7rem", padding: "0.2rem 0.5rem" }}
                      onClick={() => {
                        onSelectJob(job.id);
                        onNavigateTab("details");
                      }}
                    >
                      Specs 📋
                    </button>
                    {job.source_url && (
                      <a
                        href={job.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="jh-btn jh-btn-primary"
                        style={{ fontSize: "0.7rem", padding: "0.2rem 0.5rem", textDecoration: "none" }}
                      >
                        Apply ↗
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
