"""Personalized Tourism Recommendation Engine.

Combines Content-Based Filtering (scikit-learn TF-IDF vectorization and
cosine similarity) with multi-factor business scoring:
- Content similarity between user interests and destination attributes.
- Google review ratings normalized to [0, 1].
- Affordability relative to user budget.
- Duration fit relative to available visiting hours.
- Time-of-day suitability (Morning, Afternoon, Evening, All).

Features:
- In-memory dataset caching to eliminate repeated disk I/O.
- Deterministic, explainable scoring with a detailed factor breakdown.
- Configurable scoring weights.
- Graceful constraint enforcement.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "cleaned_tourism.csv"

# Configurable default scoring weights (sum to 1.0)
DEFAULT_WEIGHTS = {
    "content_similarity": 0.35,  # TF-IDF cosine similarity
    "rating": 0.25,              # Google review rating normalized (0-1)
    "affordability": 0.15,       # Budget vs fee affordability (0-1)
    "duration_fit": 0.15,        # Visit duration proximity (0-1)
    "preferred_time": 0.10,      # Match for Morning/Afternoon/Evening (0-1)
}


class TourismRecommender:
    """Singleton-style recommender cache holding the dataset and TF-IDF index."""

    def __init__(self, data_path: Path = DATA_PATH):
        self.data_path = data_path
        self._df: Optional[pd.DataFrame] = None
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None
        self._load_and_index()

    def _load_and_index(self):
        """Load dataset, validate schema, build corpus and fit TF-IDF vectorizer."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.data_path}")

        df = pd.read_csv(self.data_path)
        df.columns = df.columns.str.strip()

        required = [
            "Name",
            "State",
            "City",
            "Type",
            "Entrance Fee in INR",
            "Google review rating",
            "time needed to visit in hrs",
            "Best Time to visit",
        ]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns in dataset: {missing}")

        # Ensure ID column exists
        if "id" not in df.columns:
            df.insert(0, "id", range(1, len(df) + 1))

        # Safe type conversions
        df["Entrance Fee in INR"] = (
            pd.to_numeric(df["Entrance Fee in INR"], errors="coerce")
            .fillna(0)
            .clip(lower=0)
            .astype(int)
        )
        df["Google review rating"] = (
            pd.to_numeric(df["Google review rating"], errors="coerce")
            .fillna(4.0)
            .clip(1.0, 5.0)
        )
        df["time needed to visit in hrs"] = (
            pd.to_numeric(df["time needed to visit in hrs"], errors="coerce")
            .fillna(2.0)
            .clip(0.5, 24.0)
        )

        for col in [
            "Name",
            "State",
            "City",
            "Type",
            "Significance",
            "Best Time to visit",
            "Zone",
            "Weekly Off",
        ]:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()

        # Build rich text corpus for Content-Based similarity:
        # Gives higher weight to attraction Type and cultural Significance
        corpus = (
            df["Type"]
            + " "
            + df["Type"]
            + " "
            + df["Significance"]
            + " "
            + df["Significance"]
            + " "
            + df["Name"]
            + " "
            + df["City"]
            + " "
            + df["State"]
            + " "
            + df["Best Time to visit"]
        ).str.lower()

        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b",
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(corpus)
        self._df = df.copy()

    @property
    def dataframe(self) -> pd.DataFrame:
        if self._df is None:
            self._load_and_index()
        return self._df.copy()

    def recommend(
        self,
        state: Optional[str] = None,
        city: Optional[str] = None,
        attraction_type: Optional[str] = None,
        interests: Optional[List[str]] = None,
        budget: float = 1000.0,
        available_hours: float = 8.0,
        preferred_time: Optional[str] = None,
        min_rating: Optional[float] = None,
        top_n: int = 10,
        weights: Optional[Dict[str, float]] = None,
    ) -> pd.DataFrame:
        """Compute personalized tourism recommendations using TF-IDF + multi-factor scoring."""
        if self._df is None:
            self._load_and_index()

        df = self._df.copy()
        w = dict(DEFAULT_WEIGHTS)
        if weights:
            w.update(weights)
        total_w = sum(w.values())
        if total_w > 0:
            w = {k: v / total_w for k, v in w.items()}

        # 1. State filter
        if state and state.strip():
            target_state = state.strip().lower()
            df = df[df["State"].str.lower().str.contains(target_state, regex=False)]

        # 2. City filter
        if city and city.strip():
            target_city = city.strip().lower()
            df = df[df["City"].str.lower().str.contains(target_city, regex=False)]

        # 3. Attraction type filter
        if attraction_type and attraction_type.strip():
            target_type = attraction_type.strip().lower()
            df = df[df["Type"].str.lower().str.contains(target_type, regex=False)]

        # 4. Budget filter (hard constraint with non-negative guard)
        effective_budget = max(0.0, float(budget))
        df = df[df["Entrance Fee in INR"] <= effective_budget]

        # 5. Visiting hours filter (hard constraint)
        effective_hours = max(0.5, float(available_hours))
        df = df[df["time needed to visit in hrs"] <= effective_hours]

        # 6. Minimum rating filter
        if min_rating is not None and min_rating > 0:
            df = df[df["Google review rating"] >= float(min_rating)]

        if df.empty:
            return pd.DataFrame()

        # -------------------------------------------------------------
        # Factor A: Content-Based Similarity using TF-IDF Cosine Similarity
        # -------------------------------------------------------------
        parsed_interests = [
            str(item).strip().lower()
            for item in (interests or [])
            if str(item).strip()
        ]
        query_text = " ".join(parsed_interests).strip()

        if query_text:
            query_vector = self._vectorizer.transform([query_text])
            sub_tfidf = self._tfidf_matrix[df.index]
            sims = cosine_similarity(query_vector, sub_tfidf).flatten()
            content_sim_series = pd.Series(sims, index=df.index).clip(0.0, 1.0)
        else:
            # Neutral baseline (0.50) when no specific interests are requested
            content_sim_series = pd.Series(0.50, index=df.index)

        # -------------------------------------------------------------
        # Factor B: Rating Score (0 to 1 scale)
        # -------------------------------------------------------------
        rating_series = (df["Google review rating"] / 5.0).clip(0.0, 1.0)

        # -------------------------------------------------------------
        # Factor C: Affordability Score (0 to 1 scale)
        # Places that are free or cost far less than budget receive higher scores
        # -------------------------------------------------------------
        denominator_budget = max(effective_budget, 1.0)
        affordability_series = (
            1.0 - (df["Entrance Fee in INR"] / denominator_budget)
        ).clip(0.0, 1.0)

        # -------------------------------------------------------------
        # Factor D: Duration Fit Score (0 to 1 scale)
        # Rewards visits that comfortably utilize the planned visiting window
        # -------------------------------------------------------------
        duration = df["time needed to visit in hrs"]
        duration_ratio = (duration / effective_hours).clip(0.0, 1.0)
        # Perfect fit is balanced utilization (e.g. 50-80% of window)
        duration_fit_series = (1.0 - (duration_ratio - 0.5).abs() * 0.5).clip(0.0, 1.0)

        # -------------------------------------------------------------
        # Factor E: Preferred Time Match (0 to 1 scale)
        # -------------------------------------------------------------
        if preferred_time and preferred_time.strip():
            pref = preferred_time.strip().lower()
            best_time_lower = df["Best Time to visit"].str.lower()
            time_series = best_time_lower.apply(
                lambda t: 1.0 if pref in t or t == "all" else 0.2
            )
        else:
            time_series = pd.Series(0.8, index=df.index)

        # -------------------------------------------------------------
        # Composite Recommendation Score (0 to 100)
        # -------------------------------------------------------------
        composite_score = (
            w["content_similarity"] * content_sim_series
            + w["rating"] * rating_series
            + w["affordability"] * affordability_series
            + w["duration_fit"] * duration_fit_series
            + w["preferred_time"] * time_series
        ) * 100.0

        df["Recommendation Score"] = composite_score.round(2)
        df["Personalization Score"] = df["Recommendation Score"]  # Alias for existing frontend

        # Sub-scores for explainability
        df["Content Similarity Score"] = (content_sim_series * 100).round(1)
        df["Rating Score"] = (rating_series * 100).round(1)
        df["Affordability Score"] = (affordability_series * 100).round(1)
        df["Duration Fit Score"] = (duration_fit_series * 100).round(1)
        df["Preferred Time Score"] = (time_series * 100).round(1)

        # Generate human-readable explanation
        def build_explanation(row):
            reasons = []
            if query_text and row["Content Similarity Score"] >= 30:
                reasons.append(f"Strong content match ({row['Content Similarity Score']}%) for your travel interests")
            if row["Google review rating"] >= 4.4:
                reasons.append(f"Highly rated ({row['Google review rating']}/5)")
            if row["Entrance Fee in INR"] == 0:
                reasons.append("Free entrance")
            elif row["Entrance Fee in INR"] <= effective_budget * 0.5:
                reasons.append(f"Budget-friendly (INR {row['Entrance Fee in INR']})")
            if preferred_time and row["Preferred Time Score"] >= 80:
                reasons.append(f"Ideal for {preferred_time} visits")
            if not reasons:
                reasons.append("Matches your location and schedule parameters")
            return "; ".join(reasons)

        df["Explanation"] = df.apply(build_explanation, axis=1)

        # Sort deterministically by composite score, then rating, then review volume
        sort_cols = ["Recommendation Score", "Google review rating"]
        if "Number of google review in lakhs" in df.columns:
            sort_cols.append("Number of google review in lakhs")

        df = df.sort_values(
            by=sort_cols,
            ascending=[False, False, False] if len(sort_cols) == 3 else [False, False],
            na_position="last",
        )

        output_cols = [
            "id",
            "Name",
            "State",
            "City",
            "Type",
            "Entrance Fee in INR",
            "Google review rating",
            "time needed to visit in hrs",
            "Best Time to visit",
            "Significance",
            "Weekly Off",
            "Airport with 50km Radius",
            "DSLR Allowed",
            "Recommendation Score",
            "Personalization Score",
            "Content Similarity Score",
            "Rating Score",
            "Affordability Score",
            "Duration Fit Score",
            "Preferred Time Score",
            "Explanation",
        ]
        present_cols = [col for col in output_cols if col in df.columns]
        return df[present_cols].head(max(1, int(top_n))).copy()


# Global cached engine instance
_ENGINE: Optional[TourismRecommender] = None


def get_recommender(force_reload: bool = False) -> TourismRecommender:
    """Retrieve or initialize the global TourismRecommender instance."""
    global _ENGINE
    if _ENGINE is None or force_reload:
        _ENGINE = TourismRecommender()
    return _ENGINE


def load_destinations() -> pd.DataFrame:
    """Load cached tourism destination dataframe (backward compatibility)."""
    return get_recommender().dataframe


def recommend_destinations(
    state: Optional[str] = None,
    interests: Optional[List[str]] = None,
    budget: float = 1000.0,
    available_hours: float = 8.0,
    preferred_time: Optional[str] = None,
    top_n: int = 10,
    city: Optional[str] = None,
    type: Optional[str] = None,
    min_rating: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Public recommendation API preserving backward compatibility."""
    return get_recommender().recommend(
        state=state,
        city=city,
        attraction_type=type,
        interests=interests,
        budget=budget,
        available_hours=available_hours,
        preferred_time=preferred_time,
        min_rating=min_rating,
        top_n=top_n,
        weights=weights,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("AI Tourism Recommendation System - TF-IDF Content Engine")
    print("=" * 60)

    test_recs = recommend_destinations(
        state="Delhi",
        interests=["temple", "historical", "peaceful"],
        budget=100.0,
        available_hours=4.0,
        preferred_time="Afternoon",
        top_n=5,
    )

    print("\nTop 5 Recommendations for Delhi (temple, historical):")
    for _, row in test_recs.iterrows():
        print(f"\n- {row['Name']} ({row['City']}, {row['State']})")
        print(f"  Type: {row['Type']} | Rating: {row['Google review rating']}/5 | Fee: INR {row['Entrance Fee in INR']}")
        print(f"  Score: {row['Recommendation Score']}/100 | Content Match: {row['Content Similarity Score']}%")
        print(f"  Explanation: {row['Explanation']}")
