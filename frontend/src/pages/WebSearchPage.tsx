import { useState, type FormEvent } from "react";

import { alexApi } from "../services/alexApi";
import type { WebSearchMode, WebSearchResponse } from "../types/api";

interface WebSearchPageProps {
  apiKeyConfigured: boolean;
  onOpenSettings: () => void;
  onError: (message: string) => void;
}

const modes: { value: WebSearchMode; label: string }[] = [
  { value: "search", label: "Web search" },
  { value: "news", label: "Latest news" },
  { value: "research", label: "Research" },
  { value: "price", label: "Price lookup" },
  { value: "compare", label: "Compare" },
];

export function WebSearchPage({
  apiKeyConfigured,
  onOpenSettings,
  onError,
}: WebSearchPageProps) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<WebSearchMode>("search");
  const [weatherCity, setWeatherCity] = useState("");
  const [weatherWhen, setWeatherWhen] = useState("today");
  const [items, setItems] = useState("");
  const [aspect, setAspect] = useState("general");
  const [result, setResult] = useState<WebSearchResponse | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanQuery = query.trim();
    if (!cleanQuery || busy || !apiKeyConfigured) return;
    const comparisons = items.split(",").map((item) => item.trim()).filter(Boolean);
    if (mode === "compare" && comparisons.length < 2) {
      onError("Enter at least two comma-separated items to compare.");
      return;
    }

    setBusy(true);
    setResult(null);
    try {
      setResult(await alexApi.searchWeb({
        query: cleanQuery,
        mode,
        ...(mode === "compare" ? { items: comparisons, aspect } : {}),
      }));
    } catch (error) {
      onError(error instanceof Error ? error.message : "Web search failed.");
    } finally {
      setBusy(false);
    }
  }

  async function openWeather(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const city = weatherCity.trim();
    if (!city) return;
    try {
      await alexApi.openWeatherSearch(city, weatherWhen);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Could not open weather search.");
    }
  }

  return (
    <section className="conversation-layout web-search-layout">
      <div className="conversation-heading">
        <div>
          <div className="eyebrow">GROUNDED WEB SEARCH</div>
          <h3>Search with sources</h3>
        </div>
        <span className="session-label"><span className="session-dot" /> GEMINI SEARCH</span>
      </div>
      <form className="web-search-form" onSubmit={(event) => void submit(event)}>
        <label htmlFor="web-search-query">Search query</label>
        <textarea
          id="web-search-query"
          maxLength={4000}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask about current facts, news, products, or a topic…"
          required
          rows={2}
          value={query}
        />
        <div className="web-search-options">
          <label>
            Search mode
            <select onChange={(event) => setMode(event.target.value as WebSearchMode)} value={mode}>
              {modes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          {mode === "compare" && (
            <>
              <label>
                Items (comma-separated)
                <input
                  maxLength={800}
                  onChange={(event) => setItems(event.target.value)}
                  placeholder="Product A, Product B"
                  value={items}
                />
              </label>
              <label>
                Compare by
                <input maxLength={200} onChange={(event) => setAspect(event.target.value)} value={aspect} />
              </label>
            </>
          )}
        </div>
        <div className="web-search-submit-row">
          <p>Results use live web grounding. Review cited sources for accuracy.</p>
          <button className="send-button" disabled={!apiKeyConfigured || busy || !query.trim()}>
            {busy ? "Searching…" : "Search"}
          </button>
        </div>
      </form>

      <form className="weather-search-form" onSubmit={(event) => void openWeather(event)}>
        <h4>Open weather search</h4>
        <div className="web-search-options">
          <label>
            City
            <input
              maxLength={150}
              onChange={(event) => setWeatherCity(event.target.value)}
              placeholder="City name"
              required
              value={weatherCity}
            />
          </label>
          <label>
            When
            <input
              maxLength={100}
              onChange={(event) => setWeatherWhen(event.target.value)}
              value={weatherWhen}
            />
          </label>
        </div>
        <div className="web-search-submit-row">
          <p>Opens a Google Search page in your default browser; Alex does not fetch forecast data.</p>
          <button className="button button-secondary" disabled={!weatherCity.trim()} type="submit">
            Open weather search
          </button>
        </div>
      </form>

      {!apiKeyConfigured ? (
        <div className="key-needed">
          <span>Gemini API key required</span>
          <button className="button button-secondary" onClick={onOpenSettings} type="button">Open Settings</button>
        </div>
      ) : busy ? (
        <p className="web-search-status" role="status">Searching web sources…</p>
      ) : result ? (
        <div className="web-search-results" aria-live="polite">
          <h4>{modes.find((item) => item.value === result.mode)?.label}: {result.query}</h4>
          <p className="web-search-answer">{result.answer}</p>
          <div className="web-search-sources">
            <h4>Sources ({result.sources.length})</h4>
            {result.sources.length ? (
              <ol>
                {result.sources.map((source) => (
                  <li key={source.url}>
                    <button
                      className="web-search-source"
                      onClick={() => void alexApi.openExternal(source.url).catch((error: unknown) =>
                        onError(error instanceof Error ? error.message : "Could not open source."))}
                      type="button"
                    >
                      <strong>{source.title}</strong>
                      <span>{source.url}</span>
                    </button>
                  </li>
                ))}
              </ol>
            ) : (
              <p>No source links were returned. Treat this answer as unverified.</p>
            )}
          </div>
        </div>
      ) : (
        <div className="conversation-empty web-search-empty">
          <div className="chat-emblem">⌕</div>
          <h2>Search current information</h2>
          <p>Choose a mode and Alex will return a grounded answer with source links when available.</p>
        </div>
      )}
    </section>
  );
}
