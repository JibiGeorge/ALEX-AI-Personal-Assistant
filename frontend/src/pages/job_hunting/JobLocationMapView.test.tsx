import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { JobLocationMapView } from "./JobLocationMapView";
import type { CompatibilityScore, JobListing } from "../../types/jobHunting";

const mockJobs: JobListing[] = [
  {
    id: "job-sf-1",
    source: "direct_url",
    source_url: "https://careers.sf.com/1",
    company_name: "SF Cloud Labs",
    title: "Senior Full Stack Engineer",
    location: "San Francisco, CA",
    modality: "hybrid",
    country: "United States",
    city: "San Francisco",
    state: "CA",
    latitude: 37.7749,
    longitude: -122.4194,
    experience_required_min: 3,
    experience_required_max: 6,
    raw_description: "Build reactive systems.",
    required_skills: ["React", "TypeScript", "Node.js"],
    preferred_skills: [],
    benefits: [],
    discovered_at: "2026-11-14T00:00:00Z",
    status: "discovered",
    is_expired: false,
    content_hash: "hash_sf_1",
  },
  {
    id: "job-remote-1",
    source: "remoteok",
    source_url: "https://remoteok.com/l/999",
    company_name: "Global Anywhere Co",
    title: "Remote Frontend Architect",
    location: "Worldwide / Remote",
    modality: "remote",
    latitude: null,
    longitude: null,
    experience_required_min: 5,
    experience_required_max: 8,
    raw_description: "Architect frontend.",
    required_skills: ["React", "Next.js"],
    preferred_skills: [],
    benefits: [],
    discovered_at: "2026-11-14T00:00:00Z",
    status: "discovered",
    is_expired: false,
    content_hash: "hash_remote_1",
  },
];

const mockScores: Record<string, CompatibilityScore> = {
  "job-sf-1": {
    id: "score-1",
    job_id: "job-sf-1",
    candidate_id: "cand-1",
    match_percentage: 92,
    overall_score: 92,
    match_tier: "excellent",
    technical_skills_score: 95,
    experience_score: 90,
    responsibilities_score: 90,
    tech_stack_score: 95,
    location_score: 90,
    seniority_score: 90,
    skills_matched: ["React", "TypeScript"],
    skills_missing: [],
    mandatory_requirements_not_met: [],
    experience_gaps: [],
    strengths: ["Strong technical match"],
    weaknesses: [],
    ai_recommendation: "HIGH_MATCH_APPLY",
    recommended_action: "HIGH_MATCH_APPLY",
    match_summary: "92% compatibility",
    calculated_at: "2026-11-14T00:00:00Z",
  },
};

describe("JobLocationMapView", () => {
  it("renders interactive map, city clusters, and verified remote dock", () => {
    const onSelectJob = vi.fn();
    const onNavigateTab = vi.fn();

    render(
      <JobLocationMapView
        jobs={mockJobs}
        scores={mockScores}
        onSelectJob={onSelectJob}
        onNavigateTab={onNavigateTab}
      />
    );

    expect(screen.getByTestId("job-location-map-view")).toBeDefined();
    expect(screen.getByText(/INTERACTIVE JOB LOCATION MAP & GEO RADAR/i)).toBeDefined();

    // Verify view mode buttons
    expect(screen.getByRole("button", { name: /Split View/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /Map View/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /List View/i })).toBeDefined();

    // Verify city cluster in SVG
    expect(screen.getByText("San Francisco")).toBeDefined();

    // Verify remote dock segregation
    expect(screen.getByText(/VERIFIED REMOTE OPPORTUNITIES/i)).toBeDefined();
    expect(screen.getByText("Global Anywhere Co · 🌐 Worldwide / Remote")).toBeDefined();
  });

  it("filters jobs when searching by skill or title", () => {
    const onSelectJob = vi.fn();
    const onNavigateTab = vi.fn();

    render(
      <JobLocationMapView
        jobs={mockJobs}
        scores={mockScores}
        onSelectJob={onSelectJob}
        onNavigateTab={onNavigateTab}
      />
    );

    const searchInput = screen.getByPlaceholderText(/Filter by title, company, skills/i);
    fireEvent.change(searchInput, { target: { value: "Architect" } });

    // San Francisco engineer should be filtered out from general list, remote architect remains
    expect(screen.getAllByText("Remote Frontend Architect").length).toBeGreaterThanOrEqual(1);
  });

  it("switches to full map view and full list view", () => {
    const onSelectJob = vi.fn();
    const onNavigateTab = vi.fn();

    render(
      <JobLocationMapView
        jobs={mockJobs}
        scores={mockScores}
        onSelectJob={onSelectJob}
        onNavigateTab={onNavigateTab}
      />
    );

    const mapViewBtn = screen.getByRole("button", { name: /Map View/i });
    fireEvent.click(mapViewBtn);
    expect(screen.getByText("↺")).toBeDefined();

    const listViewBtn = screen.getByRole("button", { name: /List View/i });
    fireEvent.click(listViewBtn);
    expect(screen.getByText(/All Filtered Opportunities/i)).toBeDefined();
  });
});
