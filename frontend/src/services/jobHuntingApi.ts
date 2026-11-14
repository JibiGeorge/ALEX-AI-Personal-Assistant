import type {
  AdapterStatusReport,
  ApplicationApproval,
  ApplicationStatus,
  CandidatePreferences,
  CandidateProfile,
  CareerRecommendations,
  CompatibilityScore,
  JobApplication,
  JobComparisonResponse,
  JobListResponse,
  JobListing,
  ScheduleDiscoveryConfig,
  TailoredDocument,
  TailoredDocumentListResponse,
} from "../types/jobHunting";

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  // If running inside Electron desktop shell and requestBackend bridge is available
  if (typeof window !== "undefined" && window.alex?.requestBackend) {
    return window.alex.requestBackend(method, path, body);
  }

  // Fallback for standard browser / test runners:
  const token = typeof window !== "undefined" ? (window as any).__ALEX_TOKEN__ || "" : "";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      errorDetail = await res.text().catch(() => errorDetail);
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const jobHuntingApi = {
  // -------------------------------------------------------------------------
  // Jobs & Discovery
  // -------------------------------------------------------------------------
  listJobs: (filters?: {
    status?: ApplicationStatus;
    modality?: string;
    source?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<JobListResponse> => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.modality) params.set("modality", filters.modality);
    if (filters?.source) params.set("source", filters.source);
    if (filters?.search) params.set("search", filters.search);
    if (filters?.limit) params.set("limit", String(filters.limit));
    if (filters?.offset) params.set("offset", String(filters.offset));
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<JobListResponse>("GET", `/api/job-hunting/jobs${qs}`);
  },

  getJob: (jobId: string): Promise<JobListing> =>
    request<JobListing>("GET", `/api/job-hunting/jobs/${jobId}`),

  discoverJobs: (
    query = "Software Developer",
    location = "Worldwide",
    modalities = ["remote", "hybrid"],
    maxResults = 25,
  ): Promise<JobListing[]> =>
    request<JobListing[]>("POST", "/api/job-hunting/discover", {
      query,
      location,
      modalities,
      max_results: maxResults,
    }),

  ingestLinkedInAlert: (alertText: string, defaultModality = "remote"): Promise<JobListing[]> =>
    request<JobListing[]>("POST", "/api/job-hunting/ingest/linkedin-alert", {
      alert_text: alertText,
      default_modality: defaultModality,
    }),

  ingestLinkedInUrl: (
    url: string,
    optionalTitle?: string,
    optionalCompany?: string,
    modality = "remote",
  ): Promise<JobListing> =>
    request<JobListing>("POST", "/api/job-hunting/ingest/linkedin-url", {
      url,
      optional_title: optionalTitle,
      optional_company: optionalCompany,
      modality,
    }),

  ingestLinkedInDataExport: async (file: File): Promise<JobListing[]> => {
    let payload: { filename: string; raw_text?: string; content_base64?: string };
    if (file.name.endsWith(".csv")) {
      const text = await file.text();
      payload = { filename: file.name, raw_text: text };
    } else {
      const buffer = await file.arrayBuffer();
      let binary = "";
      const bytes = new Uint8Array(buffer);
      for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      const b64 = btoa(binary);
      payload = { filename: file.name, content_base64: b64 };
    }
    return request<JobListing[]>("POST", "/api/job-hunting/ingest/linkedin-data-export", payload);
  },

  ingestDirectUrl: (
    url: string,
    title?: string,
    company?: string,
    rawText?: string,
    modality = "remote",
  ): Promise<JobListing> =>
    request<JobListing>("POST", "/api/job-hunting/ingest/url", {
      url,
      title,
      company,
      raw_text: rawText,
      modality,
    }),

  ingestGreenhouse: (boardToken: string, filterRole?: string): Promise<JobListing[]> =>
    request<JobListing[]>("POST", "/api/job-hunting/ingest/greenhouse", {
      board_token: boardToken,
      filter_role: filterRole,
    }),

  ingestLever: (siteName: string, filterRole?: string): Promise<JobListing[]> =>
    request<JobListing[]>("POST", "/api/job-hunting/ingest/lever", {
      site_name: siteName,
      filter_role: filterRole,
    }),

  listAdapters: (): Promise<AdapterStatusReport[]> =>
    request<AdapterStatusReport[]>("GET", "/api/job-hunting/adapters"),

  // -------------------------------------------------------------------------
  // Matching & Compatibility Scoring
  // -------------------------------------------------------------------------
  calculateMatch: (jobId: string): Promise<CompatibilityScore> =>
    request<CompatibilityScore>("POST", `/api/job-hunting/jobs/${jobId}/match`),

  getScore: (jobId: string): Promise<CompatibilityScore> =>
    request<CompatibilityScore>("GET", `/api/job-hunting/jobs/${jobId}/score`),

  // -------------------------------------------------------------------------
  // Resume Studio & Cover Letter Studio
  // -------------------------------------------------------------------------
  tailorResume: (jobId: string, instructions?: string): Promise<TailoredDocument> => {
    const qs = instructions ? `?instructions=${encodeURIComponent(instructions)}` : "";
    return request<TailoredDocument>("POST", `/api/job-hunting/jobs/${jobId}/tailor-resume${qs}`);
  },

  listTailoredDocuments: (jobId: string): Promise<TailoredDocumentListResponse> =>
    request<TailoredDocumentListResponse>("GET", `/api/job-hunting/jobs/${jobId}/tailored-documents`),

  getTailoredDocument: (jobId: string): Promise<TailoredDocument> =>
    request<TailoredDocument>("GET", `/api/job-hunting/jobs/${jobId}/tailored-document`),

  getTailoredDocumentById: (docId: string): Promise<TailoredDocument> =>
    request<TailoredDocument>("GET", `/api/job-hunting/tailored-documents/${docId}`),

  updateTailoredDocument: (
    docId: string,
    payload: {
      resume_markdown?: string;
      cover_letter_markdown?: string;
      create_new_version?: boolean;
    },
  ): Promise<TailoredDocument> =>
    request<TailoredDocument>("PUT", `/api/job-hunting/tailored-documents/${docId}`, payload),

  getDownloadUrl: (docId: string, format = "pdf", docType = "resume"): string =>
    `/api/job-hunting/tailored-documents/${docId}/download?format=${format}&doc_type=${docType}`,

  // -------------------------------------------------------------------------
  // Applications & Explicit Approvals
  // -------------------------------------------------------------------------
  listApplications: (status?: ApplicationStatus): Promise<JobApplication[]> => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<JobApplication[]>("GET", `/api/job-hunting/applications${qs}`);
  },

  getApplication: (applicationId: string): Promise<JobApplication> =>
    request<JobApplication>("GET", `/api/job-hunting/applications/${applicationId}`),

  updateApplicationStatus: (
    applicationId: string,
    status: ApplicationStatus,
    notes?: string,
  ): Promise<JobApplication> =>
    request<JobApplication>("PATCH", `/api/job-hunting/applications/${applicationId}/status`, {
      status,
      notes,
    }),

  recordInterview: (
    applicationId: string,
    roundName: string,
    scheduledAt: string,
    interviewer?: string,
    feedback?: string,
  ): Promise<JobApplication> =>
    request<JobApplication>("POST", `/api/job-hunting/applications/${applicationId}/interviews`, {
      round_name: roundName,
      scheduled_at: scheduledAt,
      interviewer,
      feedback,
    }),

  listPendingApprovals: (): Promise<ApplicationApproval[]> =>
    request<ApplicationApproval[]>("GET", "/api/job-hunting/approvals/pending"),

  decideApproval: (
    approvalId: string,
    approved: boolean,
    userConfirmationText?: string,
  ): Promise<ApplicationApproval> =>
    request<ApplicationApproval>("POST", `/api/job-hunting/approvals/${approvalId}/decision`, {
      approved,
      user_confirmation_text: userConfirmationText,
    }),

  // -------------------------------------------------------------------------
  // Candidate Profile & Settings
  // -------------------------------------------------------------------------
  getCandidateProfile: (): Promise<CandidateProfile> =>
    request<CandidateProfile>("GET", "/api/job-hunting/profile"),

  updateCandidateProfile: (profile: Partial<CandidateProfile>): Promise<CandidateProfile> =>
    request<CandidateProfile>("PUT", "/api/job-hunting/profile", profile),

  updateCandidatePreferences: (
    preferences: Partial<CandidatePreferences>,
  ): Promise<CandidateProfile> =>
    request<CandidateProfile>("PUT", "/api/job-hunting/profile/preferences", preferences),

  uploadMasterResume: (payload: { raw_text?: string; file_name?: string }): Promise<CandidateProfile> =>
    request<CandidateProfile>("POST", "/api/job-hunting/profile/upload-resume", payload),

  getDiscoverySchedule: (): Promise<ScheduleDiscoveryConfig> =>
    request<ScheduleDiscoveryConfig>("GET", "/api/job-hunting/discovery/schedule"),

  updateDiscoverySchedule: (enabled: boolean, intervalHours: number): Promise<ScheduleDiscoveryConfig> =>
    request<ScheduleDiscoveryConfig>("PUT", "/api/job-hunting/discovery/schedule", {
      enabled,
      interval_hours: intervalHours,
    }),

  // -------------------------------------------------------------------------
  // Comparison & Career Recommendations
  // -------------------------------------------------------------------------
  compareJobs: (jobIds: string[]): Promise<JobComparisonResponse> =>
    request<JobComparisonResponse>("POST", "/api/job-hunting/compare", { job_ids: jobIds }),

  getCareerRecommendations: (): Promise<CareerRecommendations> =>
    request<CareerRecommendations>("GET", "/api/job-hunting/career-recommendations"),

  ingestLinkedInProfile: (url: string): Promise<CandidateProfile> =>
    request<CandidateProfile>("POST", "/api/job-hunting/profile/linkedin", { url }),

  // -------------------------------------------------------------------------
  // Data Governance & Privacy
  // -------------------------------------------------------------------------
  exportCareerData: (): Promise<Record<string, unknown>> =>
    request<Record<string, unknown>>("GET", "/api/job-hunting/data/export"),

  purgeCareerData: (): Promise<Record<string, number>> =>
    request<Record<string, number>>("POST", "/api/job-hunting/data/purge"),
};

