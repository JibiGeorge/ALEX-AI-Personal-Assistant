import { test as base, expect, Page, _electron, type ElectronApplication } from "@playwright/test";
import path from "node:path";

export interface AlexTestFixtures {
  alexPage: Page;
  electronApp?: ElectronApplication;
  injectDesktopBridge: (page: Page) => Promise<void>;
}

export const test = base.extend<AlexTestFixtures>({
  injectDesktopBridge: async ({}, use) => {
    const injector = async (page: Page) => {
      await page.addInitScript(() => {
        // High-fidelity window.alex desktop bridge polyfill for web-based E2E
        (window as any).alex = {
          toggleFullscreen: async () => {},
          getStatus: async () => ({
            status: "ready",
            backend_port: 8765,
            api_version: "0.1.0",
            loopback_only: true,
          }),
          getSystemMetrics: async () => ({
            cpu_percent: 28.5,
            memory_percent: 44.2,
            network_mb_per_sec: 1.4,
            disk_percent: 52.0,
            gpu_percent: 15.0,
          }),
          getSystemVerification: async () => ({
            settings_healthy: true,
            storage_healthy: true,
            metrics_healthy: true,
            reminders_healthy: true,
          }),
          getSystemAlerts: async () => ({ alerts: [] }),
          getSystemBriefing: async () => ({
            summary: "All systems nominal.",
            tasks_due: [],
            alerts: [],
          }),
          listActions: async () => ({
            actions: [
              {
                id: "system_metrics",
                name: "System Metrics",
                description: "Retrieves current hardware utilization.",
                enabled: true,
                requires_confirmation: false,
                timeout_seconds: 5,
              },
              {
                id: "job_search",
                name: "Job Search",
                description: "Searches open developer listings.",
                enabled: true,
                requires_confirmation: false,
                timeout_seconds: 15,
              },
            ],
          }),
          setActionEnabled: async (id: string, enabled: boolean) => ({
            id,
            enabled,
          }),
          executeAction: async (id: string, parameters: any, confirmed: boolean) => ({
            execution_id: "exec-1",
            action_id: id,
            parameters,
            outcome: "done",
            output: { message: "Executed successfully" },
            timestamp: new Date().toISOString(),
          }),
          getActionHistory: async () => ({ executions: [] }),
          getSettings: async () => ({
            settings: {
              assistant_name: "ALEX",
              voice_name: "en-US-Standard-C",
              theme: "holographic",
              auto_start: false,
            },
            api_key_configured: true,
            keyring_available: true,
          }),
          updateSettings: async (settings: any) => ({
            settings,
            api_key_configured: true,
            keyring_available: true,
          }),
          saveApiKey: async () => ({ success: true }),
          listMemory: async () => ({
            entries: [
              {
                id: "mem-1",
                category: "identity",
                key: "user_name",
                value: "Alex Operator",
                updated_at: new Date().toISOString(),
              },
            ],
          }),
          upsertMemory: async (cat: string, key: string, val: any) => ({
            category: cat,
            key,
            value: val,
            updated_at: new Date().toISOString(),
          }),
          deleteMemory: async () => {},
          listReminders: async () => ({
            reminders: [
              {
                id: "rem-1",
                message: "Verify daily pipeline",
                due_at: new Date(Date.now() + 3600000).toISOString(),
                status: "pending",
              },
            ],
          }),
          createReminder: async (msg: string, due: string) => ({
            id: "rem-new",
            message: msg,
            due_at: due,
            status: "pending",
          }),
          cancelReminder: async () => {},
          listDueReminders: async () => ({ reminders: [] }),
          markReminderDelivered: async () => ({}),
          notifyReminder: async () => {},
          notifySystemAlert: async () => {},
          sendMessage: async (text: string) => ({
            id: "turn-1",
            output_text: `Acknowledged: ${text}`,
            conversation_id: "conv-1",
          }),
          captureScreen: async () => null,
          searchWeb: async () => ({
            query: "react jobs",
            results: [{ title: "React Dev", url: "https://example.com" }],
          }),
          openExternal: async () => {},
          openWeatherSearch: async () => {},
          getLoginItemStatus: async () => ({ enabled: false }),
          setLoginItemEnabled: async () => ({ enabled: false }),
          createDesktopShortcut: async () => {},
          startVoice: async () => {},
          sendVoiceAudio: () => {},
          sendVoiceText: async (t: string) => ({ output_text: `Echo: ${t}` }),
          interruptVoice: async () => {},
          stopVoice: async () => {},
          onVoiceEvent: () => () => {},
          getWakeStatus: async () => ({ enabled: false, model: "hey_jarvis" }),
          toggleWakeWord: async () => ({ enabled: false }),
          installWakeModels: async () => ({ installed: true }),
          wakeAssistant: async () => {},
          sleepAssistant: async () => {},
          ensureMicrophoneAccess: async () => ({ granted: true }),
          ensureCameraAccess: async () => ({ granted: true, status: "granted" }),
          getMediaStatus: async () => ({ active: false }),
          resolveMedia: async (s: string) => ({
            source: s,
            title: s,
            url: s,
          }),
          controlMedia: async () => {},
          requestBackend: async (method: string, route: string, body?: any) => {
            // Mock backend routes for Job Hunting & Core modules
            if (route.includes("/profile")) {
              return {
                id: "cand-1",
                full_name: "Alex Developer",
                email: "alex@example.com",
                location: "Worldwide (Remote)",
                headline: "Full Stack Engineer (React/TypeScript/Python)",
                total_years_experience: 4,
                programming_languages: ["TypeScript", "JavaScript", "Python"],
                frameworks: ["React", "FastAPI", "Next.js"],
                databases: ["PostgreSQL", "SQLite"],
                skills: [],
                work_history: [],
                is_verified: true,
              };
            }
            if (route.includes("/jobs") || route.includes("/discover")) {
              return {
                jobs: [
                  {
                    id: "job-e2e-1",
                    title: "Senior Full Stack Developer",
                    company_name: "Quantum Dynamics",
                    location: "Remote / Worldwide",
                    modality: "remote",
                    required_skills: ["React", "TypeScript", "FastAPI"],
                    preferred_skills: ["Docker", "Playwright"],
                    experience_required_min: 3,
                    experience_required_max: 5,
                    source: "greenhouse",
                    source_url: "https://boards.greenhouse.io/quantum/jobs/123",
                    cleaned_description: "Building next-generation distributed systems with React and FastAPI.",
                  },
                ],
                total: 1,
              };
            }
            if (route.includes("/match")) {
              return {
                overall_score: 92.5,
                recommendation: "Strong Match",
                skills_match_score: 95.0,
                experience_score: 90.0,
                responsibilities_score: 92.0,
                stack_score: 94.0,
                location_score: 100.0,
                seniority_score: 90.0,
                matched_skills: ["React", "TypeScript", "FastAPI"],
                missing_skills: [],
                mandatory_requirements_met: true,
                strengths: ["Extensive React & TypeScript production experience"],
                weaknesses: [],
              };
            }
            if (route.includes("/adapters")) {
              return [
                {
                  adapter_name: "greenhouse",
                  is_available: true,
                  source_type: "board",
                  requires_auth: false,
                  configuration_hint: "Public boards supported directly",
                },
                {
                  adapter_name: "lever",
                  is_available: true,
                  source_type: "board",
                  requires_auth: false,
                  configuration_hint: "Public boards supported directly",
                },
              ];
            }
            if (route.includes("/approvals")) {
              return [];
            }
            if (route.includes("/applications")) {
              return [];
            }
            return { success: true };
          },
        };
      });
    };
    await use(injector);
  },

  alexPage: async ({ page, injectDesktopBridge }, use) => {
    await injectDesktopBridge(page);
    await page.goto("/?skip_startup=true");
    await page.waitForLoadState("domcontentloaded");
    await use(page);
  },
});

export { expect };
