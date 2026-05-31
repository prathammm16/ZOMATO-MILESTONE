import { FormEvent, useEffect, useMemo, useState } from "react";

type BudgetTier = "low" | "medium" | "high";

type Restaurant = {
  id: string;
  name: string;
  location: string;
  locality?: string | null;
  cuisines: string[];
  cost?: number | null;
  budget_tier: BudgetTier;
  rating: number;
};

type Recommendation = {
  rank: number;
  restaurant: Restaurant;
  explanation: string;
};

type RecommendationMetadata = {
  candidate_count: number;
  total_matches: number;
  truncated: boolean;
  llm_used: boolean;
  fallback_used: boolean;
  groq_latency_ms?: number | null;
};

type RecommendationResponse = {
  recommendations: Recommendation[];
  summary?: string | null;
  message?: string | null;
  validation_errors: string[];
  metadata: RecommendationMetadata;
};

type LocationsResponse = {
  cities: string[];
  localities: string[];
};

type HealthResponse = {
  status: string;
  restaurants: number;
};

type PreferenceForm = {
  location: string;
  budget: BudgetTier;
  cuisine: string;
  minRating: number;
  additionalPreferences: string;
  numRecommendations: number;
};

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const cuisineOptions = [
  "",
  "Italian",
  "North Indian",
  "Chinese",
  "South Indian",
  "Bakery",
  "Desserts",
  "Cafe",
  "Biryani",
  "Fast Food",
  "Continental",
];

const initialForm: PreferenceForm = {
  location: "Bangalore",
  budget: "medium",
  cuisine: "",
  minRating: 4,
  additionalPreferences: "Date night, family-friendly, quick service",
  numRecommendations: 5,
};

function App() {
  const [form, setForm] = useState<PreferenceForm>(initialForm);
  const [locations, setLocations] = useState<string[]>(["Bangalore"]);
  const [restaurantsLoaded, setRestaurantsLoaded] = useState<number>(0);
  const [response, setResponse] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [favorites, setFavorites] = useState<Record<string, Recommendation>>({});

  useEffect(() => {
    async function loadMetadata() {
      try {
        const [healthRes, locationsRes] = await Promise.all([
          fetch(`${API_BASE_URL}/health`),
          fetch(`${API_BASE_URL}/locations`),
        ]);

        if (!healthRes.ok || !locationsRes.ok) {
          throw new Error("The recommendation API is not responding.");
        }

        const health = (await healthRes.json()) as HealthResponse;
        const locationPayload = (await locationsRes.json()) as LocationsResponse;
        const combinedLocations = [
          ...locationPayload.cities,
          ...locationPayload.localities.filter((loc) => !locationPayload.cities.includes(loc)),
        ];

        setRestaurantsLoaded(health.restaurants);
        setLocations(combinedLocations.length ? combinedLocations : ["Bangalore"]);

        setForm((current) => {
          if (!combinedLocations.length || combinedLocations.includes(current.location)) {
            return current;
          }

          const preferred =
            combinedLocations.find((loc) => loc.toLowerCase() === "bangalore") ??
            combinedLocations[0];
          return { ...current, location: preferred };
        });
      } catch (error) {
        setMetadataError(error instanceof Error ? error.message : "Could not load API metadata.");
      }
    }

    loadMetadata();
  }, []);

  const stats = useMemo(() => {
    return {
      discovered: response?.metadata.total_matches ?? restaurantsLoaded,
      screened: response?.metadata.candidate_count ?? 0,
      selected: response?.recommendations.length ?? 0,
    };
  }, [response, restaurantsLoaded]);
  const favoriteItems = Object.values(favorites);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setSubmitError(null);
    setResponse(null);

    try {
      const res = await fetch(`${API_BASE_URL}/recommendations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          location: form.location,
          budget: form.budget,
          cuisine: form.cuisine || null,
          min_rating: form.minRating,
          additional_preferences: form.additionalPreferences || null,
          num_recommendations: form.numRecommendations,
        }),
      });

      if (!res.ok) {
        const errorPayload = await res.json().catch(() => null);
        throw new Error(errorPayload?.detail ?? "Recommendation request failed.");
      }

      const payload = (await res.json()) as RecommendationResponse;
      setResponse(payload);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function toggleFavorite(recommendation: Recommendation) {
    const restaurantId = recommendation.restaurant.id;
    setFavorites((current) => {
      const next = { ...current };
      if (next[restaurantId]) {
        delete next[restaurantId];
      } else {
        next[restaurantId] = recommendation;
      }
      return next;
    });
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="zomato-logo">zomato</span>
          <span className="brand-copy">AI Recommender</span>
        </div>
        <nav className="navlinks" aria-label="Primary navigation">
          <a href="#discover">Discover</a>
          <a href="#recommendations">For You</a>
          <a href="#pipeline">AI Picks</a>
          <span className="nav-badge">Live Demo</span>
        </nav>
      </header>

      <main className="layout">
        <aside className="refine-card" id="discover">
          <div className="panel-heading">
            <span className="panel-icon">=</span>
            <h2>Refine Search</h2>
          </div>

          <form onSubmit={handleSubmit}>
            <label>
              Location
              <input
                list="location-options"
                value={form.location}
                onChange={(event) => setForm({ ...form, location: event.target.value })}
                placeholder="Bangalore"
              />
              <datalist id="location-options">
                {locations.map((location) => (
                  <option key={location} value={location} />
                ))}
              </datalist>
            </label>

            <label>
              Number of Recommendations
              <div className="stepper">
                <button
                  type="button"
                  onClick={() =>
                    setForm({
                      ...form,
                      numRecommendations: Math.max(1, form.numRecommendations - 1),
                    })
                  }
                >
                  -
                </button>
                <strong>{form.numRecommendations}</strong>
                <button
                  type="button"
                  onClick={() =>
                    setForm({
                      ...form,
                      numRecommendations: Math.min(10, form.numRecommendations + 1),
                    })
                  }
                >
                  +
                </button>
              </div>
            </label>

            <fieldset>
              <legend>Budget</legend>
              <div className="segmented">
                {(["low", "medium", "high"] as BudgetTier[]).map((budget) => (
                  <button
                    key={budget}
                    type="button"
                    className={form.budget === budget ? "active" : ""}
                    onClick={() => setForm({ ...form, budget })}
                  >
                    {budget}
                  </button>
                ))}
              </div>
            </fieldset>

            <label>
              Cuisine
              <select
                value={form.cuisine}
                onChange={(event) => setForm({ ...form, cuisine: event.target.value })}
              >
                {cuisineOptions.map((cuisine) => (
                  <option key={cuisine || "any"} value={cuisine}>
                    {cuisine || "Any cuisine"}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Minimum Rating
              <div className="range-row">
                <span>{form.minRating.toFixed(1)}</span>
                <input
                  type="range"
                  min="0"
                  max="5"
                  step="0.5"
                  value={form.minRating}
                  onChange={(event) =>
                    setForm({ ...form, minRating: Number(event.target.value) })
                  }
                />
                <span>5.0</span>
              </div>
            </label>

            <label>
              Dining Mood
              <textarea
                value={form.additionalPreferences}
                onChange={(event) =>
                  setForm({ ...form, additionalPreferences: event.target.value })
                }
                placeholder="Date night, family-friendly, quick service..."
              />
            </label>

            <button className="submit-button" type="submit" disabled={loading}>
              {loading ? "Ranking..." : "Update Recommendations"}
            </button>
          </form>

          <p className="dataset-note">
            Dataset ready with <strong>{restaurantsLoaded ? restaurantsLoaded.toLocaleString() : "..."}</strong>{" "}
            restaurants. Backend: <strong>{API_BASE_URL}</strong>
          </p>
        </aside>

        <section className="content">
          <section className="hero">
            <div>
              <p className="eyebrow">Real data + Groq AI</p>
              <h1>Personalized Picks</h1>
              <p>Restaurant recommendations tailored to your palate.</p>
            </div>
            <span className={response?.metadata.fallback_used ? "status fallback" : "status"}>
              <span />
              {response?.metadata.fallback_used ? "Fallback Ranking" : "AI Ranking Active"}
            </span>
          </section>

          <section className="stats" aria-label="Recommendation stats">
            <StatCard label="Discovered" value={stats.discovered} helper="Restaurants" />
            <StatCard label="Screened" value={stats.screened} helper="Candidates" />
            <StatCard label="Selected" value={stats.selected} helper="Top Matches" />
          </section>

          <FavoritesSection favorites={favoriteItems} onToggleFavorite={toggleFavorite} />

          {metadataError && <Alert title="API status" message={metadataError} />}
          {submitError && <Alert title="Request failed" message={submitError} />}
          {response?.validation_errors.map((error) => (
            <Alert key={error} title="Preference check" message={error} />
          ))}
          {response?.summary && <Alert title="AI Summary" message={response.summary} featured />}
          {response?.message && !response.recommendations.length && (
            <Alert title="No matches found" message={response.message} />
          )}

          <section className="recommendation-area" id="recommendations">
            {loading ? (
              <LoadingGrid />
            ) : response?.recommendations.length ? (
              <div className="recommendation-grid">
                {response.recommendations.map((recommendation) => (
                  <RecommendationCard
                    key={`${recommendation.restaurant.id}-${recommendation.rank}`}
                    recommendation={recommendation}
                    isFavorite={Boolean(favorites[recommendation.restaurant.id])}
                    onToggleFavorite={toggleFavorite}
                  />
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <strong>Ready to discover</strong>
                <p>
                  Choose a location, budget, cuisine, and rating. The backend filters the dataset,
                  then Groq ranks grounded restaurant candidates.
                </p>
              </div>
            )}
          </section>

          <section className="pipeline" id="pipeline">
            <span>Preferences</span>
            <i />
            <span>Dataset filter</span>
            <i />
            <span>Groq ranking</span>
            <i />
            <span>Grounded results</span>
          </section>
        </section>
      </main>
    </div>
  );
}

function StatCard({ label, value, helper }: { label: string; value: number; helper: string }) {
  return (
    <article className="stat-card">
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
      <small>{helper}</small>
    </article>
  );
}

function Alert({
  title,
  message,
  featured = false,
}: {
  title: string;
  message: string;
  featured?: boolean;
}) {
  return (
    <article className={featured ? "alert featured" : "alert"}>
      <strong>{title}</strong>
      <p>{message}</p>
    </article>
  );
}

function FavoritesSection({
  favorites,
  onToggleFavorite,
}: {
  favorites: Recommendation[];
  onToggleFavorite: (recommendation: Recommendation) => void;
}) {
  return (
    <section className="favorites-section" aria-label="Favorite restaurants">
      <div className="favorites-header">
        <div>
          <span>Favorites</span>
          <h2>Saved Picks</h2>
        </div>
        <strong>{favorites.length}</strong>
      </div>

      {favorites.length ? (
        <div className="favorite-list">
          {favorites.map((recommendation) => {
            const restaurant = recommendation.restaurant;
            const area = restaurant.locality || restaurant.location;
            return (
              <article className="favorite-mini-card" key={restaurant.id}>
                <button
                  type="button"
                  aria-label={`Remove ${restaurant.name} from favorites`}
                  onClick={() => onToggleFavorite(recommendation)}
                >
                  ♥
                </button>
                <div>
                  <h3>{restaurant.name}</h3>
                  <p>
                    {area} · Rating {restaurant.rating.toFixed(1)}
                  </p>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <p className="favorites-empty">Tap the heart on any recommendation to save it here.</p>
      )}
    </section>
  );
}

function RecommendationCard({
  recommendation,
  isFavorite,
  onToggleFavorite,
}: {
  recommendation: Recommendation;
  isFavorite: boolean;
  onToggleFavorite: (recommendation: Recommendation) => void;
}) {
  const { restaurant } = recommendation;
  const area = restaurant.locality || restaurant.location;
  const cuisines = restaurant.cuisines.length ? restaurant.cuisines : ["Cuisine not listed"];
  const match = Math.max(72, 100 - (recommendation.rank - 1) * 6);

  return (
    <article className="recommendation-card">
      <div className="card-top">
        <div>
          <span className="rank">Rank #{recommendation.rank}</span>
          <h3>{restaurant.name}</h3>
        </div>
        <div className="card-actions">
          <span className="match">{match}% Match</span>
          <button
            className={isFavorite ? "favorite-button active" : "favorite-button"}
            type="button"
            aria-label={isFavorite ? "Remove from favourites" : "Add to favourites"}
            title={isFavorite ? "Remove from favourites" : "Add to favourites"}
            onClick={() => onToggleFavorite(recommendation)}
          >
            ♥
          </button>
        </div>
      </div>

      <div className="card-meta">
        <span>Rating {restaurant.rating.toFixed(1)}</span>
        <span>{restaurant.budget_tier}</span>
        <span>{area}</span>
        <span>{restaurant.cost ? `Rs. ${restaurant.cost.toFixed(0)} for two` : "Cost not listed"}</span>
      </div>

      <div className="chips">
        {cuisines.slice(0, 5).map((cuisine) => (
          <span key={cuisine}>{cuisine}</span>
        ))}
        {cuisines.length > 5 && <span>+{cuisines.length - 5} more</span>}
      </div>

      <div className="ai-reason">
        <strong>Why AI picked it</strong>
        <p>{recommendation.explanation}</p>
      </div>
    </article>
  );
}

function LoadingGrid() {
  return (
    <div className="recommendation-grid">
      {Array.from({ length: 6 }).map((_, index) => (
        <article className="recommendation-card skeleton" key={index}>
          <span />
          <span />
          <span />
          <span />
        </article>
      ))}
    </div>
  );
}

export default App;
