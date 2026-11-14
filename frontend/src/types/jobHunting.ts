export type JobSource =
  | "linkedin_url"
  | "linkedin_alert"
  | "greenhouse"
  | "lever"
  | "company_careers"
  | "remoteok"
  | "web_search"
  | "direct_url"
  | "authorized_api";

export type WorkModality = "remote" | "hybrid" | "onsite";

export type ApplicationStatus =
  | "discovered"
  | "analyzed"
  | "tailored"
  | "ready_to_apply"
  | "applied"
  | "interviewing"
  | "offered"
  | "rejected"
  | "withdrawn";

export type ApprovalStatus = "pending" | "approved" | "rejected";

export interface SkillItem {
  name: string;
  category: string;
  proficiency: string;
  years_experience: number;
}

export interface WorkExperienceItem {
  id?: string;
  company_name: string;
  role_title: string;
  location?: string;
  is_remote: boolean;
  start_date: string;
  end_date?: string | null;
  is_current: boolean;
  highlights: string[];
  tech_stack: string[];
}

export interface CandidatePreferences {
  target_roles: string[];
  min_years_experience: number;
  max_years_experience: number;
  modalities: WorkModality[];
  target_locations: string[];
  minimum_salary?: number | null;
  auto_discovery_enabled: boolean;
  discovery_interval_hours: number;
}

export interface CandidateProfile {
  id: string;
  full_name: string;
  email: string;
  phone?: string | null;
  location: string;
  linkedin_url?: string | null;
  github_url?: string | null;
  portfolio_url?: string | null;
  headline: string;
  summary: string;
  total_years_experience: number;
  seniority_level: string;
  programming_languages: string[];
  frameworks: string[];
  databases: string[];
  skills: SkillItem[];
  work_history: WorkExperienceItem[];
  preferences: CandidatePreferences;
  master_resume_path?: string | null;
  raw_resume_text?: string | null;
  is_verified: boolean;
  verified_at?: string | null;
  verification_notes?: string | null;
  updated_at?: string;
}

export interface JobListing {
  id: string;
  source: JobSource;
  external_id?: string | null;
  source_url: string;
  company_name: string;
  title: string;
  location: string;
  modality: WorkModality;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string;
  experience_required_min: number;
  experience_required_max: number;
  raw_description: string;
  cleaned_description?: string | null;
  required_skills: string[];
  preferred_skills: string[];
  benefits: string[];
  posted_at?: string | null;
  discovered_at: string;
  status: ApplicationStatus;
  is_expired: boolean;
  expiry_checked_at?: string | null;
  content_hash: string;
}

export interface JobListResponse {
  total: number;
  jobs: JobListing[];
}

export interface CompatibilityScore {
  id: string;
  job_id: string;
  candidate_id: string;
  match_percentage: number;
  overall_score: number;
  technical_skills_score: number;
  experience_score: number;
  responsibilities_score: number;
  tech_stack_score: number;
  location_score: number;
  seniority_score: number;
  skills_matched: string[];
  skills_missing: string[];
  mandatory_requirements_not_met: string[];
  experience_gaps: string[];
  strengths: string[];
  weaknesses: string[];
  ai_recommendation: string;
  recommended_action: string;
  match_summary: string;
  calculated_at: string;
}

export interface TailoredDocument {
  id: string;
  job_id: string;
  candidate_id: string;
  version_number: number;
  resume_markdown: string;
  cover_letter_markdown: string;
  ats_keywords_included: string[];
  customizations_summary: string[];
  relevant_experience_identified: string[];
  relevant_skills_identified: string[];
  docx_resume_path?: string | null;
  pdf_resume_path?: string | null;
  docx_cover_letter_path?: string | null;
  pdf_cover_letter_path?: string | null;
  original_resume_preserved: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface TailoredDocumentListResponse {
  job_id: string;
  total_versions: number;
  documents: TailoredDocument[];
}

export interface InterviewRound {
  round_name: string;
  scheduled_at: string;
  interviewer?: string | null;
  feedback?: string | null;
  passed?: boolean | null;
}

export interface JobApplication {
  id: string;
  job_id: string;
  candidate_id: string;
  tailored_document_id?: string | null;
  status: ApplicationStatus;
  applied_at?: string | null;
  submission_method?: string | null;
  notes?: string | null;
  interview_rounds: InterviewRound[];
  compensation_offered?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationApproval {
  id: string;
  application_id: string;
  requested_action: string;
  approval_status: ApprovalStatus;
  approval_channel: string;
  user_confirmation_text?: string | null;
  decided_at?: string | null;
  created_at: string;
}

export interface ScheduleDiscoveryConfig {
  enabled: boolean;
  interval_hours: number;
  last_run_at?: string | null;
  next_run_at?: string | null;
}

export interface AdapterStatusReport {
  adapter_name: string;
  source: JobSource;
  is_available: boolean;
  requires_auth: boolean;
  is_configured: boolean;
  configuration_hint: string;
}

