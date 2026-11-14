import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { JobComparisonView } from "./JobComparisonView";
import { jobHuntingApi } from "../../services/jobHuntingApi";
import type { JobListing, CompatibilityScore, JobComparisonResponse } from "../../types/jobHunting";

vi.mock("../../services/jobHuntingApi", () => ({
  jobHuntingApi: {
    compareJobs: vi.fn(),
  },
}));

const mockJobs: JobListing[] = [
  {
    id: "job-1",
    source: "lever",
    source_url: "https://example.com/job-1",
    company_name: "Tech Corp",
    title: "Senior Full Stack Engineer",
    location: "San Francisco, CA",
    modality: "onsite",
    country: "USA",
    city: "San Francisco",
    state: "CA",
    latitude: 37.7749,
    longitude: -122.4194,
    experience_required_min: 5,
    experience_required_max: 8,
    raw_description: "Build cutting-edge enterprise AI systems.",
    required_skills: ["React", "TypeScript", "Python"],
    preferred_skills: [],
    benefits: [],
    discovered_at: "2026-11-14T00:00:00Z",
    status: "discovered",
    is_expired: false,
    content_hash: "hash1",
  },
  {
    id: "job-2",
    source: "remoteok",
    source_url: "https://example.com/job-2",
    company_name: "Cloud Scale",
    title: "Remote Frontend Architect",
    location: "Worldwide / Remote",
    modality: "remote",
    latitude: null,
    longitude: null,
    experience_required_min: 7,
    experience_required_max: 10,
    raw_description: "Lead remote frontend architecture across micro-frontends.",
    required_skills: ["React", "TypeScript", "Performance"],
    preferred_skills: [],
    benefits: [],
    discovered_at: "2026-11-14T00:00:00Z",
    status: "discovered",
    is_expired: false,
    content_hash: "hash2",
  },
];

const mockScores: Record<string, CompatibilityScore> = {
  "job-1": {
    id: "score-1",
    job_id: "job-1",
    candidate_id: "cand-1",
    match_percentage: 88,
    overall_score: 88,
    technical_skills_score: 90,
    experience_score: 85,
    responsibilities_score: 85,
    tech_stack_score: 90,
    seniority_score: 90,
    work_experience_score: 85,
    education_score: 90,
    industry_score: 85,
    location_score: 85,
    match_tier: "excellent",
    matching_skills: ["React", "TypeScript", "Python"],
    missing_skills: [],
    skills_matched: ["React", "TypeScript", "Python"],
    skills_missing: [],
    mandatory_requirements_not_met: [],
    experience_gaps: [],
    strengths: ["Solid React & TypeScript expertise"],
    weaknesses: [],
    why_matched: "Solid React & TypeScript expertise",
    why_not_matched: "",
    ai_recommendation: "Strong candidate fit",
    recommended_action: "Apply",
    match_summary: "Strong skills match",
    calculated_at: "2026-11-14T00:00:00Z",
  },
  "job-2": {
    id: "score-2",
    job_id: "job-2",
    candidate_id: "cand-1",
    match_percentage: 92,
    overall_score: 92,
    technical_skills_score: 95,
    experience_score: 90,
    responsibilities_score: 90,
    tech_stack_score: 95,
    seniority_score: 90,
    work_experience_score: 90,
    education_score: 90,
    industry_score: 90,
    location_score: 100,
    match_tier: "excellent",
    matching_skills: ["React", "TypeScript"],
    missing_skills: ["Performance"],
    skills_matched: ["React", "TypeScript"],
    skills_missing: ["Performance"],
    mandatory_requirements_not_met: [],
    experience_gaps: [],
    strengths: ["Full remote alignment and deep TypeScript experience"],
    weaknesses: [],
    why_matched: "Full remote alignment and deep TypeScript experience",
    why_not_matched: "Missing micro-frontends specific benchmarking",
    ai_recommendation: "Exceptional alignment",
    recommended_action: "Apply immediately",
    match_summary: "Premier alignment",
    calculated_at: "2026-11-14T00:00:00Z",
  },
};

const mockComparisonResponse: JobComparisonResponse = {
  compared_jobs: [
    {
      job_id: "job-1",
      title: "Senior Full Stack Engineer",
      company_name: "Tech Corp",
      location: "San Francisco, CA",
      modality: "onsite",
      salary: "$160,000 - $190,000",
      experience_required: "5+ years",
      match_percentage: 88,
      match_tier: "excellent",
      responsibilities: ["Build enterprise AI systems", "Lead cross-functional sprints"],
      required_skills: ["React", "TypeScript", "Python"],
      matching_skills: ["React", "TypeScript", "Python"],
      missing_skills: [],
      growth_potential: "High - direct exposure to founding team",
      company_info: "Fast-growing Series B startup",
    },
    {
      job_id: "job-2",
      title: "Remote Frontend Architect",
      company_name: "Cloud Scale",
      location: "Worldwide / Remote",
      modality: "remote",
      salary: "$175,000 - $210,000",
      experience_required: "7+ years",
      match_percentage: 92,
      match_tier: "excellent",
      responsibilities: ["Architect micro-frontends", "Mentor staff engineers"],
      required_skills: ["React", "TypeScript", "Performance"],
      matching_skills: ["React", "TypeScript"],
      missing_skills: ["Performance"],
      growth_potential: "Very High - principal track",
      company_info: "Global distributed infrastructure provider",
    },
  ],
  best_fit_job_id: "job-2",
  best_fit_job_title: "Remote Frontend Architect",
  best_fit_company: "Cloud Scale",
  ai_recommendation_reason:
    "Remote Frontend Architect at Cloud Scale is the premier match with 92% compatibility, top-tier compensation, and 100% remote alignment.",
  comparison_summary: "Comparing 2 top opportunities across tech stack, salary and career growth.",
};

describe("JobComparisonView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(jobHuntingApi.compareJobs).mockResolvedValue(mockComparisonResponse);
  });

  it("renders comparison matrix and fetches comparison data for selected jobs", async () => {
    const onSelectJob = vi.fn();
    const onNavigateTab = vi.fn();

    render(
      <JobComparisonView
        jobs={mockJobs}
        scores={mockScores}
        selectedJobId="job-1"
        onSelectJob={onSelectJob}
        onNavigateTab={onNavigateTab}
      />
    );

    expect(screen.getByTestId("job-comparison-view")).toBeDefined();
    expect(screen.getByText(/MULTI-OPPORTUNITY COMPARISON MATRIX/i)).toBeDefined();

    // Verify API called with initial pair
    await waitFor(() => {
      expect(jobHuntingApi.compareJobs).toHaveBeenCalledWith(["job-1", "job-2"]);
    });

    // Check best fit banner
    await waitFor(() => {
      expect(screen.getByText(/AI CAREER RECOMMENDATION/i)).toBeDefined();
      expect(
        screen.getByText(/Remote Frontend Architect at Cloud Scale is the premier match/i)
      ).toBeDefined();
    });

    // Check comparison cards and values
    expect(screen.getByText("88% MATCH")).toBeDefined();
    expect(screen.getByText("92% MATCH")).toBeDefined();
    expect(screen.getByText("★ TOP FIT")).toBeDefined();
    expect(screen.getByText("💰 $160,000 - $190,000")).toBeDefined();
    expect(screen.getByText("💰 $175,000 - $210,000")).toBeDefined();
    expect(screen.getByText(/High - direct exposure to founding team/i)).toBeDefined();
    expect(screen.getByText(/Very High - principal track/i)).toBeDefined();
  });

  it("handles empty jobs gracefully", () => {
    const onSelectJob = vi.fn();
    const onNavigateTab = vi.fn();

    render(
      <JobComparisonView
        jobs={[]}
        scores={{}}
        selectedJobId={null}
        onSelectJob={onSelectJob}
        onNavigateTab={onNavigateTab}
      />
    );

    expect(screen.getByText(/No opportunities available to compare/i)).toBeDefined();
  });
});
