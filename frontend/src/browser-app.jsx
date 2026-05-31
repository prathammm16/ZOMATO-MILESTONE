const { useEffect, useMemo, useState } = React;

const API_BASE_URL = "http://127.0.0.1:8000";

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

const initialForm = {
  location: "Bangalore",
  budget: "medium",
  cuisine: "",
  minRating: 4,
  additionalPreferences: "Date night, family-friendly, quick service",
  numRecommendations: 5,
};

function App() {
  const [form, setForm] = useState(initialForm);
  const [locations, setLocations] = useState(["Bangalore"]);
  const [restaurantsLoaded, setRestaurantsLoaded] = useState(0);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [favorites, setFavorites] = useState({});

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

        const health = await healthRes.json();
        const locationPayload = await locationsRes.json();
        const combined = [
          ...locationPayload.cities,
          ...locationPayload.localities.filter((loc) => !locationPayload.cities.includes(loc)),
        ];

        setRestaurantsLoaded(health.restaurants);
        setLocations(combined.length ? combined : ["Bangalore"]);
        if (combined.length && !combined.includes(form.location)) {
          setForm((current) => ({ ...current, location: combined[0] }));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load API metadata.");
      }
    }

    loadMetadata();
  }, []);

  const stats = useMemo(
    () => ({
      discovered: response?.metadata?.total_matches ?? restaurantsLoaded,
      screened: response?.metadata?.candidate_count ?? 0,
      selected: response?.recommendations?.length ?? 0,
    }),
    [response, restaurantsLoaded],
  );
  const favoriteItems = Object.values(favorites);

  async function submitPreferences(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
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
        const payload = await res.json().catch(() => null);
        throw new Error(payload?.detail ?? "Recommendation request failed.");
      }

      setResponse(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function toggleFavorite(recommendation) {
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

          <form onSubmit={submitPreferences}>
            <label>
              Location
              <input
                list="location-options"
                value={form.location}
                onChange={(event) => setForm({ ...form, location: event.target.value })}
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
                {["low", "medium", "high"].map((budget) => (
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
            <span className={response?.metadata?.fallback_used ? "status fallback" : "status"}>
              <span />
              {response?.metadata?.fallback_used ? "Fallback Ranking" : "AI Ranking Active"}
            </span>
          </section>

          <section className="stats" aria-label="Recommendation stats">
            <StatCard label="Discovered" value={stats.discovered} helper="Restaurants" />
            <StatCard label="Screened" value={stats.screened} helper="Candidates" />
            <StatCard label="Selected" value={stats.selected} helper="Top Matches" />
          </section>

          <FavoritesSection favorites={favoriteItems} onToggleFavorite={toggleFavorite} />

          {error && <Alert title="Status" message={error} />}
          {response?.validation_errors?.map((message) => (
            <Alert key={message} title="Preference check" message={message} />
          ))}
          {response?.summary && <Alert title="AI Summary" message={response.summary} featured />}
          {response?.message && !response.recommendations?.length && (
            <Alert title="No matches found" message={response.message} />
          )}

          <section className="recommendation-area" id="recommendations">
            {loading ? (
              <LoadingGrid />
            ) : response?.recommendations?.length ? (
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

function StatCard({ label, value, helper }) {
  return (
    <article className="stat-card">
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
      <small>{helper}</small>
    </article>
  );
}

function Alert({ title, message, featured = false }) {
  return (
    <article className={featured ? "alert featured" : "alert"}>
      <strong>{title}</strong>
      <p>{message}</p>
    </article>
  );
}

function FavoritesSection({ favorites, onToggleFavorite }) {
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

function RecommendationCard({ recommendation, isFavorite, onToggleFavorite }) {
  const { restaurant } = recommendation;
  const area = restaurant.locality || restaurant.location;
  const cuisines = restaurant.cuisines?.length ? restaurant.cuisines : ["Cuisine not listed"];
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

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
