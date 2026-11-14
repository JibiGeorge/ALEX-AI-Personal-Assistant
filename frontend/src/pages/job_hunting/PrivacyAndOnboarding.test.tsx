import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { JobOnboardingWizard } from "../../components/onboarding/JobOnboardingWizard";
import { PrivacyView } from "./PrivacyView";
import { jobHuntingApi } from "../../services/jobHuntingApi";
import type { CandidateProfile } from "../../types/jobHunting";

vi.mock("../../services/jobHuntingApi", () => ({
  jobHuntingApi: {
    exportCareerData: vi.fn(),
    purgeCareerData: vi.fn(),
  },
}));

const mockProfile: CandidateProfile = {
  id: "cand-1",
  full_name: "Alex Dev",
  email: "alex@example.com",
  location: "San Francisco, CA",
  headline: "Senior Software Engineer",
  summary: "Experienced full-stack engineer.",
  total_years_experience: 6,
  seniority_level: "Senior",
  programming_languages: ["TypeScript", "Python"],
  frameworks: ["React", "FastAPI"],
  databases: ["PostgreSQL"],
  skills: [],
  work_history: [],
  preferences: {
    target_roles: ["Frontend Engineer"],
    target_locations: ["Remote"],
    modalities: ["remote"],
    minimum_salary: 140000,
    min_years_experience: 3,
    max_years_experience: 8,
    auto_discovery_enabled: true,
    discovery_interval_hours: 12,
  },
  is_verified: true,
};

describe("JobOnboardingWizard Component", () => {
  it("navigates through all 3 steps and submits profile data", async () => {
    const onSaveProfile = vi.fn().mockResolvedValue(undefined);
    const onUploadResume = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    render(
      <JobOnboardingWizard
        isOpen={true}
        onClose={onClose}
        profile={mockProfile}
        onSaveProfile={onSaveProfile}
        onUploadResume={onUploadResume}
      />,
    );

    expect(screen.getByText(/STEP 1 OF 3/i)).toBeInTheDocument();
    expect(screen.getByText(/Master Resume & Candidate Profile/i)).toBeInTheDocument();

    // Step 1 -> Step 2
    fireEvent.click(screen.getByText(/Continue to Step 2/i));
    expect(screen.getByText(/STEP 2 OF 3/i)).toBeInTheDocument();
    expect(screen.getByText(/Target Roles & Geographic Preferences/i)).toBeInTheDocument();

    // Step 2 -> Step 3
    fireEvent.click(screen.getByText(/Continue to Step 3/i));
    expect(screen.getByText(/STEP 3 OF 3/i)).toBeInTheDocument();
    expect(screen.getByText(/Compensation & Work Authorization/i)).toBeInTheDocument();

    // Complete setup
    fireEvent.click(screen.getByText(/Complete Setup & Launch Radar/i));

    await waitFor(() => {
      expect(onSaveProfile).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("handles ESC key to close wizard", () => {
    const onClose = vi.fn();
    render(
      <JobOnboardingWizard
        isOpen={true}
        onClose={onClose}
        profile={mockProfile}
        onSaveProfile={vi.fn()}
        onUploadResume={vi.fn()}
      />,
    );

    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});

describe("PrivacyView Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders transparency cards for local storage and cloud AI", () => {
    render(<PrivacyView onNotifySuccess={vi.fn()} onNotifyError={vi.fn()} />);

    expect(screen.getByText(/Stored Strictly Locally/i)).toBeInTheDocument();
    expect(screen.getByText(/Cloud Voice & Model Execution/i)).toBeInTheDocument();
    expect(screen.getByText(/DATA PORTABILITY & RIGHT TO ERASURE/i)).toBeInTheDocument();
  });

  it("triggers data export and calls jobHuntingApi", async () => {
    const onNotifySuccess = vi.fn();
    (jobHuntingApi.exportCareerData as any).mockResolvedValue({ version: "1.0", jobs: [] });

    render(<PrivacyView onNotifySuccess={onNotifySuccess} onNotifyError={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /Download Full JSON Archive/i }));

    await waitFor(() => {
      expect(jobHuntingApi.exportCareerData).toHaveBeenCalled();
      expect(onNotifySuccess).toHaveBeenCalledWith(expect.stringContaining("exported successfully"));
    });
  });

  it("opens confirmation dialog and purges data on user approval", async () => {
    const onNotifySuccess = vi.fn();
    const onDataPurged = vi.fn();
    (jobHuntingApi.purgeCareerData as any).mockResolvedValue({ jobs: 5 });

    render(
      <PrivacyView
        onNotifySuccess={onNotifySuccess}
        onNotifyError={vi.fn()}
        onDataPurged={onDataPurged}
      />,
    );

    // Click purge button to open modal
    fireEvent.click(screen.getByRole("button", { name: /Purge all career data/i }));
    expect(screen.getByText(/Confirm Complete Data Erasure/i)).toBeInTheDocument();

    // Confirm erasure
    fireEvent.click(screen.getByText(/Yes, Permanently Purge All Data/i));

    await waitFor(() => {
      expect(jobHuntingApi.purgeCareerData).toHaveBeenCalled();
      expect(onNotifySuccess).toHaveBeenCalledWith(expect.stringContaining("purged from SQLite"));
      expect(onDataPurged).toHaveBeenCalled();
    });
  });
});

