export type JobSource =
  | "linkedin_url"
  | "linkedin_alert"
  | "greenhouse"
  | "lever"
  | "company_careers"
  | "remoteok"
  | "web_search"
  | "direct_url"
  | "authorized_api"
  | "indeed"
  | "naukri"
  | "foundit"
  | "glassdoor"
  | "wellfound"
  | "instahyre";

export type WorkModality = "remote" | "hybrid" | "onsite";

export type ApplicationStatus =
  | "discovered"
  | "saved"
  | "interested"
  | "analyzed"
  | "bookmarked"
  | "tailored"
  | "ready_to_apply"
  | "ready_for_review"
  | "applied"
  | "assessment"
  | "interview_scheduled"
  | "interview_completed"
  | "interviewing"
  | "offered"
  | "offer_received"
  | "rejected"
  | "withdrawn"
  | "archived";

export type ApprovalStatus = "pending" | "approved" | "rejected";

export interface SkillItem {
  name: string;
  category: string;
  proficiency: string;
  years_experience: number;
}

export interface EducationItem {
  institution: string;
  degree: string;
  field_of_study?: string | null;
  graduation_year?: number | null;
  location?: string | null;
}

export interface CertificationItem {
  name: string;
  issuing_organization?: string | null;
  issue_year?: number | null;
  credential_url?: string | null;
}

export interface ProjectItem {
  title: string;
  description: string;
  tech_stack: string[];
  project_url?: string | null;
}

export interface CareerRecommendations {
  strengths: string[];
  weaknesses: string[];
  missing_keywords: string[];
  skills_to_improve: string[];
  recommended_certifications: string[];
  suggested_job_titles: string[];
  recommended_career_paths: string[];
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
  factor_weights?: Record<string, number> | null;
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
  education?: EducationItem[];
  certifications?: string[];
  projects?: ProjectItem[];
  tools_and_platforms?: string[];
  non_technical_skills?: string[];
  industry_experience?: string[];
  management_experience?: string | null;
  expected_salary?: string | null;
  notice_period?: string | null;
  current_location?: string | null;
  preferred_locations?: string[];
  missing_information?: string[];
  career_recommendations?: CareerRecommendations | null;
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
  country?: string | null;
  city?: string | null;
  state?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  workplace_type?: string;
  employment_type?: string;
  logo_url?: string | null;
  application_deadline?: string | null;
  recruiter_info?: string | null;
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
  match_tier?: "excellent" | "good" | "potential" | "low";
  technical_skills_score: number;
  work_experience_score?: number;
  experience_score: number;
  responsibilities_score: number;
  education_score?: number;
  industry_score?: number;
  tech_stack_score: number;
  location_score: number;
  seniority_score: number;
  factor_weights?: Record<string, number>;
  skills_matched: string[];
  skills_missing: string[];
  matching_skills?: string[];
  missing_skills?: string[];
  mandatory_requirements_not_met: string[];
  experience_gaps: string[];
  strengths: string[];
  weaknesses: string[];
  why_matched?: string;
  why_not_matched?: string;
  ai_recommendation: string;
  recommended_action: string;
  match_summary: string;
  calculated_at: string;
}

export interface JobComparisonItem {
  job_id: string;
  title: string;
  company_name: string;
  location: string;
  modality: string;
  salary: string;
  responsibilities: string[];
  required_skills: string[];
  matching_skills: string[];
  missing_skills: string[];
  experience_required: string;
  match_percentage: number;
  match_tier: string;
  company_info: string;
  growth_potential: string;
}

export interface JobComparisonResponse {
  compared_jobs: JobComparisonItem[];
  best_fit_job_id: string;
  best_fit_job_title: string;
  best_fit_company: string;
  ai_recommendation_reason: string;
  comparison_summary: string;
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

