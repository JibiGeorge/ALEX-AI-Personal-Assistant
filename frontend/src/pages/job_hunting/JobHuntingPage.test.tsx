import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { jobHuntingApi } from "../../services/jobHuntingApi";
import type {
  AdapterStatusReport,
  ApplicationApproval,
  CandidateProfile,
  CompatibilityScore,
  JobApplication,
  JobListing,
  ScheduleDiscoveryConfig,
} from "../../types/jobHunting";
import { JobHuntingPage } from "./JobHuntingPage";

vi.mock("../../services/jobHuntingApi", () => ({
  jobHuntingApi: {
    listJobs: vi.fn(),
    getJob: vi.fn(),
    discoverJobs: vi.fn(),
    ingestLinkedInAlert: vi.fn(),
    ingestLinkedInUrl: vi.fn(),
    ingestDirectUrl: vi.fn(),
    ingestGreenhouse: vi.fn(),
    ingestLever: vi.fn(),
    listAdapters: vi.fn(),
    calculateMatch: vi.fn(),
    getScore: vi.fn(),
    tailorResume: vi.fn(),
    listTailoredDocuments: vi.fn(),
    getTailoredDocument: vi.fn(),
    getTailoredDocumentById: vi.fn(),
    updateTailoredDocument: vi.fn(),
    getDownloadUrl: vi.fn(),
    listApplications: vi.fn(),
    getApplication: vi.fn(),
    updateApplicationStatus: vi.fn(),
    recordInterview: vi.fn(),
    listPendingApprovals: vi.fn(),
    decideApproval: vi.fn(),
    getCandidateProfile: vi.fn(),
    updateCandidateProfile: vi.fn(),
    updateCandidatePreferences: vi.fn(),
    uploadMasterResume: vi.fn(),
    getDiscoverySchedule: vi.fn(),
    updateDiscoverySchedule: vi.fn(),
  },
}));

const mockJob: JobListing = {
  id: "job-101",
  source: "greenhouse",
  external_id: "gh-1234",
  source_url: "https://boards.greenhouse.io/acme/jobs/1234",
  company_name: "Acme Corp",
  title: "Senior Full Stack Developer",
  location: "Remote",
  modality: "remote",
  salary_min: 130000,
  salary_max: 160000,
  salary_currency: "$",
  experience_required_min: 3,
  experience_required_max: 5,
  raw_description: "Build distributed web applications using React, TypeScript and Node.js.",
  cleaned_description: "Build distributed web applications using React, TypeScript and Node.js.",
  required_skills: ["React", "TypeScript", "Node.js"],
  preferred_skills: ["PostgreSQL", "Docker"],
  benefits: ["Health insurance", "401k match"],
  discovered_at: "2026-11-14T00:00:00Z",
  status: "discovered",
  is_expired: false,
  content_hash: "hash-101",
};

const mockScore: CompatibilityScore = {
  id: "score-101",
  job_id: "job-101",
  candidate_id: "cand-1",
  match_percentage: 88,
  overall_score: 88,
  technical_skills_score: 90,
  experience_score: 85,
  responsibilities_score: 85,
  tech_stack_score: 90,
  location_score: 100,
  seniority_score: 90,
  skills_matched: ["React", "TypeScript", "Node.js"],
  skills_missing: ["Docker"],
  mandatory_requirements_not_met: [],
  experience_gaps: [],
  strengths: ["Strong React 19 architecture background", "Node.js backends"],
  weaknesses: [],
  ai_recommendation: "Strong candidate for Senior Full Stack role.",
  recommended_action: "Tailor resume and proceed with application.",
  match_summary: "High technical and experience alignment.",
  calculated_at: "2026-11-14T00:05:00Z",
};

const mockProfile: CandidateProfile = {
  id: "cand-1",
  full_name: "Alex Developer",
  email: "alex@example.com",
  location: "San Francisco, CA",
  headline: "Senior Full Stack & React Engineer",
  summary: "4 years experience designing React, TypeScript, and FastAPI systems.",
  total_years_experience: 4,
  seniority_level: "Mid-Senior",
  programming_languages: ["TypeScript", "JavaScript", "Python"],
  frameworks: ["React", "Next.js", "FastAPI"],
  databases: ["PostgreSQL", "SQLite"],
  skills: [
    { name: "React", category: "frontend", proficiency: "expert", years_experience: 4 },
    { name: "TypeScript", category: "languages", proficiency: "expert", years_experience: 4 },
  ],
  work_history: [
    {
      company_name: "Tech Solutions Inc",
      role_title: "Full Stack Engineer",
      is_remote: true,
      start_date: "2022-01-01",
      is_current: true,
      highlights: ["Engineered real-time web application"],
      tech_stack: ["React", "TypeScript", "Node.js"],
    },
  ],
  preferences: {
    target_roles: ["Full Stack Developer", "React Developer"],
    min_years_experience: 2,
    max_years_experience: 5,
    modalities: ["remote", "hybrid"],
    target_locations: ["Worldwide", "Remote"],
    auto_discovery_enabled: true,
    discovery_interval_hours: 12,
  },
  raw_resume_text: "ALEX DEVELOPER\nFull Stack Engineer with 4 years experience...",
  is_verified: true,
};

const mockApplication: JobApplication = {
  id: "app-101",
  job_id: "job-101",
  candidate_id: "cand-1",
  status: "applied",
  applied_at: "2026-11-14T01:00:00Z",
  submission_method: "Direct Portal",
  notes: "Submitted via career board",
  interview_rounds: [],
  created_at: "2026-11-14T00:30:00Z",
  updated_at: "2026-11-14T01:00:00Z",
};

const mockApproval: ApplicationApproval = {
  id: "appr-101",
  application_id: "app-101",
  requested_action: "submit_application",
  approval_status: "pending",
  approval_channel: "desktop_hud",
  created_at: "2026-11-14T01:10:00Z",
};

const mockSchedule: ScheduleDiscoveryConfig = {
  enabled: true,
  interval_hours: 12,
  last_run_at: "2026-11-14T00:00:00Z",
  next_run_at: "2026-11-14T12:00:00Z",
};

const mockAdapters: AdapterStatusReport[] = [
  {
    adapter_name: "GreenhouseAdapter",
    source: "greenhouse",
    is_available: true,
    requires_auth: false,
    is_configured: true,
    configuration_hint: "Ready for public board sweeps",
  },
  {
    adapter_name: "LeverAdapter",
    source: "lever",
    is_available: true,
    requires_auth: false,
    is_configured: true,
    configuration_hint: "Ready for public site sweeps",
  },
];

describe("JobHuntingPage Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(jobHuntingApi.listJobs).mockResolvedValue({ total: 1, jobs: [mockJob] });
    vi.mocked(jobHuntingApi.listAdapters).mockResolvedValue(mockAdapters);
    vi.mocked(jobHuntingApi.listApplications).mockResolvedValue([mockApplication]);
    vi.mocked(jobHuntingApi.listPendingApprovals).mockResolvedValue([mockApproval]);
    vi.mocked(jobHuntingApi.getCandidateProfile).mockResolvedValue(mockProfile);
    vi.mocked(jobHuntingApi.getDiscoverySchedule).mockResolvedValue(mockSchedule);
    vi.mocked(jobHuntingApi.getScore).mockResolvedValue(mockScore);
    vi.mocked(jobHuntingApi.calculateMatch).mockResolvedValue(mockScore);
    vi.mocked(jobHuntingApi.listTailoredDocuments).mockResolvedValue({
      job_id: "job-101",
      total_versions: 1,
      documents: [
        {
          id: "doc-101",
          job_id: "job-101",
          candidate_id: "cand-1",
          version_number: 1,
          resume_markdown: "# Alex Developer\nTailored for Acme Corp",
          cover_letter_markdown: "Dear Acme Corp Hiring Team,\nI am thrilled to apply...",
          ats_keywords_included: ["React", "TypeScript"],
          customizations_summary: ["Highlighted React 19 architecture"],
          relevant_experience_identified: ["Full Stack Engineer at Tech Solutions"],
          relevant_skills_identified: ["React", "TypeScript", "Node.js"],
          original_resume_preserved: true,
          created_at: "2026-11-14T00:20:00Z",
        },
      ],
    });
    vi.mocked(jobHuntingApi.getDownloadUrl).mockImplementation(
      (docId, format, docType) => `/api/job-hunting/tailored-documents/${docId}/download?format=${format}&doc_type=${docType}`,
    );
  });

  it("renders the 11 subnav tabs and dashboard telemetry", async () => {
    render(<JobHuntingPage />);

    // Verify sub-navigation buttons are present
    expect(screen.getByRole("button", { name: /Dashboard/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Discover Jobs/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Recommended/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Job Details/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /AI Match Analysis/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Resume Studio/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Cover Letter/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Approvals/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Applications/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Interviews/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Settings/i })).toBeDefined();

    // Verify telemetry cards
    await screen.findByText("ALEX CAREER INTELLIGENCE DASHBOARD");
    expect(screen.getByText("Total Jobs Discovered")).toBeDefined();
    expect(screen.getByText("High Match (≥80%)")).toBeDefined();
  });

  it("navigates to Discover Jobs tab and displays adapter telemetry", async () => {
    render(<JobHuntingPage />);
    await screen.findByText("ALEX CAREER INTELLIGENCE DASHBOARD");

    fireEvent.click(screen.getByRole("button", { name: /Discover Jobs/i }));
    await screen.findByText(/MULTI-SOURCE/i);

    // Check Greenhouse adapter is shown
    expect(screen.getByText("GreenhouseAdapter")).toBeDefined();
    expect(screen.getByText("LeverAdapter")).toBeDefined();
  });

  it("navigates to Recommended Jobs and displays 88% match", async () => {
    render(<JobHuntingPage />);
    await screen.findByText("ALEX CAREER INTELLIGENCE DASHBOARD");

    fireEvent.click(screen.getByRole("button", { name: /Recommended/i }));
    await screen.findByText("RECOMMENDED OPPORTUNITIES (HIGH COMPATIBILITY)");

    expect(screen.getByText("88% MATCH")).toBeDefined();
    expect(screen.getByText("Senior Full Stack Developer")).toBeDefined();
  });

  it("navigates to AI Match Analysis and displays 10-factor weighted scoring", async () => {
    render(<JobHuntingPage />);
    await screen.findByText("ALEX CAREER INTELLIGENCE DASHBOARD");

    fireEvent.click(screen.getByRole("button", { name: /AI Match Analysis/i }));
    await screen.findByText("10-FACTOR AI COMPATIBILITY REPORT");

    expect(screen.getByText("88%")).toBeDefined();
    expect(screen.getByText(/Formula: Tech \(30%\)/i)).toBeDefined();
    expect(screen.getByText("Zero-Fabrication Guarantee:")).toBeDefined();
  });

  it("navigates to Resume Studio and displays dual-pane editor and preview", async () => {
    render(<JobHuntingPage />);
    await screen.findByText("ALEX CAREER INTELLIGENCE DASHBOARD");

    fireEvent.click(screen.getByRole("button", { name: /Resume Studio/i }));
    await screen.findByText(/RESUME STUDIO: SENIOR FULL STACK DEVELOPER/i);

    expect(screen.getByText(/ATS MARKDOWN SOURCE/i)).toBeDefined();
    expect(screen.getByText("LIVE HUD PREVIEW")).toBeDefined();
    expect(screen.getByRole("link", { name: /Download DOCX/i })).toBeDefined();
    expect(screen.getByRole("link", { name: /Download PDF/i })).toBeDefined();
  });

  it("navigates to Approvals tab and allows reviewing explicit approval", async () => {
    render(<JobHuntingPage />);
    await screen.findByText("ALEX CAREER INTELLIGENCE DASHBOARD");

    fireEvent.click(screen.getByRole("button", { name: /Approvals/i }));
    await screen.findByText("EXPLICIT HUMAN APPROVAL QUEUE");

    // Click "Review & Decide"
    const decideBtn = screen.getByRole("button", { name: /Review & Decide/i });
    fireEvent.click(decideBtn);

    // Dialog pops up
    await screen.findByText(/EXPLICIT USER APPROVAL REQUIRED/i);
    expect(screen.getByText(/ALEX requires your explicit consent/i)).toBeDefined();

    // Confirm approval
    vi.mocked(jobHuntingApi.decideApproval).mockResolvedValue({
      ...mockApproval,
      approval_status: "approved",
      decided_at: "2026-11-14T01:15:00Z",
    });

    fireEvent.click(screen.getByRole("button", { name: /Explicitly Approve Action/i }));

    await waitFor(() => {
      expect(jobHuntingApi.decideApproval).toHaveBeenCalledWith("appr-101", true, undefined);
    });
  });

  it("navigates to Settings tab and updates career preferences", async () => {
    render(<JobHuntingPage />);
    await screen.findByText("ALEX CAREER INTELLIGENCE DASHBOARD");

    fireEvent.click(screen.getByRole("button", { name: /Settings/i }));
    await screen.findByText("JOB HUNTING SETTINGS & CANDIDATE PROFILE");

    expect(screen.getByText("✓ VERIFIED PROFILE")).toBeDefined();
    expect(screen.getByDisplayValue("Alex Developer")).toBeDefined();
  });
});
