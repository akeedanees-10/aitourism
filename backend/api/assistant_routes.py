"""High-performance Weather and AI Travel Assistant endpoints with caching and connection pooling."""

from typing import Optional, List, Dict, Any
import httpx
from fastapi import APIRouter, Query
from backend.config import settings
from backend.schemas import WeatherResponse, AssistantMessage, AssistantResponse
from backend.recommend import get_recommender, recommend_destinations


router = APIRouter(tags=["Weather & AI Assistant"])

# Global in-memory response cache to serve repeated/similar queries in ~1 millisecond
_ASSISTANT_CACHE: Dict[str, AssistantResponse] = {}

# Shared HTTP client for connection reuse (avoids repeated TLS handshakes)
_SHARED_CLIENT: Optional[httpx.AsyncClient] = None


def get_shared_client() -> httpx.AsyncClient:
    """Return a persistent async HTTP client with keep-alive connections."""
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
        _SHARED_CLIENT = httpx.AsyncClient(
            timeout=5.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _SHARED_CLIENT


@router.get(
    "/weather",
    response_model=WeatherResponse,
    summary="Get destination weather forecast or climate guide",
)
async def get_weather(
    city: str = Query(..., description="Target city name"),
    state: Optional[str] = Query(default=None, description="Target state"),
):
    """Retrieve weather data for a city with live API or verified dataset fallback."""
    df = get_recommender().dataframe
    city_match = df[df["City"].str.lower() == city.strip().lower()]
    best_period = "All Year Round"
    if not city_match.empty:
        best_period = city_match.iloc[0]["Best Time to visit"]

    if settings.OPENWEATHER_API_KEY:
        try:
            client = get_shared_client()
            res = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": f"{city},IN",
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                },
            )
            if res.status_code == 200:
                data = res.json()
                return WeatherResponse(
                    city=city.title(),
                    state=state.title() if state else None,
                    temp_c=round(data["main"]["temp"], 1),
                    condition=data["weather"][0]["description"].title(),
                    humidity=data["main"]["humidity"],
                    wind_kph=round(data["wind"]["speed"] * 3.6, 1),
                    best_visiting_period=best_period,
                    is_live=True,
                    note="Live weather data provided by OpenWeatherMap.",
                )
        except Exception:
            pass

    return WeatherResponse(
        city=city.title(),
        state=state.title() if state else None,
        temp_c=None,
        condition="Seasonal Climate Guide",
        humidity=None,
        wind_kph=None,
        best_visiting_period=best_period,
        is_live=False,
        note=(
            "Live weather API key not configured. Displaying verified seasonal "
            "visiting guide from the tourism database."
        ),
    )


# -------------------------------------------------------------
# Fast Factual Generator (Local Database Facts)
# -------------------------------------------------------------
def _format_destination_points(dest) -> str:
    """Format point-by-point factual breakdown of a destination."""
    name = dest["Name"]
    city = dest["City"]
    state = dest["State"]
    zone = dest.get("Zone", "India")
    attraction_type = dest["Type"]
    significance = dest.get("Significance", "Cultural")
    est_year = dest.get("Establishment Year", "Not specified")
    fee = dest["Entrance Fee in INR"]
    rating = dest["Google review rating"]
    reviews = dest.get("Number of google review in lakhs", "N/A")
    duration = dest["time needed to visit in hrs"]
    best_time = dest["Best Time to visit"]
    weekly_off = dest.get("Weekly Off", "None")
    dslr = dest.get("DSLR Allowed", "Yes")
    airport = dest.get("Airport with 50km Radius", "No")

    fee_str = "Free Entry (₹0)" if fee == 0 else f"₹{fee} per person"
    weekly_off_str = "Open all days" if weekly_off in ["Not specified", "None", ""] else f"Closed on {weekly_off}"
    dslr_str = "Permitted" if str(dslr).lower() == "yes" else "Not permitted / restricted"
    airport_str = "Yes (within 50 km)" if str(airport).lower() == "yes" else "No (more than 50 km away)"

    points = [
        f"### 📍 Key Details for **{name}**",
        f"• **Location:** {city}, {state} ({zone} Zone)",
        f"• **Attraction Type:** {attraction_type}",
        f"• **Cultural Significance:** {significance}",
        f"• **Establishment / Heritage Era:** {est_year}",
        f"• **Entrance Fee:** {fee_str}",
        f"• **Visitor Rating:** ⭐ {rating}/5 ({reviews} lakh Google reviews)",
        f"• **Recommended Visit Duration:** ⏱️ {duration} hours",
        f"• **Best Time of Day to Visit:** ⏰ {best_time}",
        f"• **Weekly Closure:** 🚫 {weekly_off_str}",
        f"• **Photography & DSLR:** 📸 {dslr_str}",
        f"• **Airport Accessibility:** ✈️ {airport_str}",
        "",
        f"💡 **Visiting Tip:** Plan for about {duration} hours during the {best_time.lower()}. "
        + (f"Ensure you don't schedule your visit on {weekly_off} when it is closed." if weekly_off not in ["Not specified", "None", ""] else "Open throughout the week.")
    ]
    return "\n".join(points)


def _format_targeted_attribute_answer(dest, q_lower: str) -> Optional[str]:
    """Provide ultra-specific point answer if user asked about a single attribute."""
    name = dest["Name"]
    fee = dest["Entrance Fee in INR"]
    duration = dest["time needed to visit in hrs"]
    best_time = dest["Best Time to visit"]
    weekly_off = dest.get("Weekly Off", "Open all days")

    if any(k in q_lower for k in ["fee", "ticket", "cost", "price", "entry", "charge"]):
        fee_str = "Free entry (₹0)" if fee == 0 else f"₹{fee} per person"
        return (
            f"### 🎟️ Entrance Fee for **{name}**\n"
            f"• **Ticket Cost:** {fee_str}\n"
            f"• **Location:** {dest['City']}, {dest['State']}\n"
            f"• **Rating:** ⭐ {dest['Google review rating']}/5\n"
            f"• **Duration:** ⏱️ {duration} hours\n"
            f"• **Best Visiting Time:** ⏰ {best_time}"
        )

    if any(k in q_lower for k in ["closed", "weekly off", "open", "holiday", "off day"]):
        weekly_str = "Open every day of the week" if weekly_off in ["Not specified", "None", ""] else f"Closed every {weekly_off}"
        return (
            f"### 📅 Opening & Schedule for **{name}**\n"
            f"• **Weekly Off:** 🚫 {weekly_str}\n"
            f"• **Best Visiting Time:** ⏰ {best_time}\n"
            f"• **Time Needed:** ⏱️ {duration} hours\n"
            f"• **Entrance Fee:** {'Free (₹0)' if fee == 0 else f'₹{fee}'}"
        )

    if any(k in q_lower for k in ["time", "timing", "duration", "hours", "how long"]):
        return (
            f"### ⏱️ Visit Duration & Timings for **{name}**\n"
            f"• **Time Needed:** ⏱️ {duration} hours\n"
            f"• **Best Time of Day:** ⏰ {best_time}\n"
            f"• **Weekly Off:** {weekly_off}\n"
            f"• **Entrance Fee:** {'Free (₹0)' if fee == 0 else f'₹{fee}'}"
        )

    return None


# -------------------------------------------------------------
# Optimized LLM Callers with Fast Timeouts
# -------------------------------------------------------------
async def _call_gemini_fast(prompt: str, context: str) -> Optional[str]:
    """Call Google Gemini API with low latency and concise token budget."""
    if not settings.GEMINI_API_KEY:
        return None

    system_text = (
        "You are an expert, concise AI Travel Assistant for the 'ExploreAI' India Tourism Recommendation System. "
        "Answer the user query in crisp, structured bullet points with emojis "
        "(📍 Location, 🏷️ Attraction Type, 🏛️ Cultural Significance, 🎟️ Entrance Fee, ⏱️ Duration, ⏰ Best Time, 🚫 Weekly Off, ⭐ Rating, 💡 Highlights & Tips). "
        "Strictly use the verified database facts provided below. Keep your answer brief and direct."
    )
    user_text = f"Verified Database Context:\n{context}\n\nUser Question: {prompt}"

    payload = {
        "systemInstruction": {"parts": [{"text": system_text}]},
        "contents": [{"parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 320,  # Lower token count yields 2x-3x faster response
        },
    }

    client = get_shared_client()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    try:
        res = await client.post(url, json=payload, timeout=4.5)
        if res.status_code == 200:
            data = res.json()
            parts = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])
            )
            text = parts[0].get("text", "").strip()
            if text:
                return text
    except Exception:
        pass
    return None


@router.post(
    "/assistant/chat",
    response_model=AssistantResponse,
    summary="High-speed AI Travel Assistant with in-memory caching and Gemini RAG",
)
async def assistant_chat(msg: AssistantMessage):
    """Fast dataset-grounded travel assistant returning structured bullet points."""
    q = msg.query.strip()
    q_lower = q.lower()
    df = get_recommender().dataframe

    # 1. Cache hit check (serves in <1ms)
    cache_key = q_lower
    if cache_key in _ASSISTANT_CACHE:
        return _ASSISTANT_CACHE[cache_key]

    # 2. Exact destination match lookup
    matched_dest = None
    for _, row in df.sort_values(by="Name", key=lambda x: x.str.len(), ascending=False).iterrows():
        dest_name_lower = row["Name"].lower()
        if dest_name_lower in q_lower or (len(dest_name_lower) > 4 and dest_name_lower in q_lower.replace("'", "")):
            matched_dest = row
            break

    suggested_destinations = [matched_dest.to_dict()] if matched_dest is not None else []

    # 3. Fast-Path: If user specifically asks for single attribute (fee, timings, weekly off),
    # return immediately from verified dataset in 0.002 seconds!
    if matched_dest is not None:
        targeted = _format_targeted_attribute_answer(matched_dest, q_lower)
        if targeted:
            resp = AssistantResponse(
                query=msg.query,
                answer=targeted,
                suggested_destinations=suggested_destinations,
                source="dataset-verified-fast-lookup",
            )
            _ASSISTANT_CACHE[cache_key] = resp
            return resp

    # 4. Prepare RAG context for Gemini
    rag_context = ""
    if matched_dest is not None:
        rag_context = (
            f"Place: {matched_dest['Name']}, City: {matched_dest['City']}, State: {matched_dest['State']}, "
            f"Type: {matched_dest['Type']}, Fee: INR {matched_dest['Entrance Fee in INR']}, "
            f"Rating: {matched_dest['Google review rating']}/5, Duration: {matched_dest['time needed to visit in hrs']} hours, "
            f"Best Time: {matched_dest['Best Time to visit']}, Weekly Off: {matched_dest.get('Weekly Off', 'None')}, "
            f"Significance: {matched_dest.get('Significance', 'Historical')}, Established: {matched_dest.get('Establishment Year', 'N/A')}"
        )
    else:
        # Search by city or keywords
        matched_city = next((c for c in df["City"].dropna().unique() if c.lower() in q_lower), None)
        matched_state = next((s for s in df["State"].dropna().unique() if s.lower() in q_lower), None)
        recs = recommend_destinations(
            state=matched_state,
            city=matched_city,
            interests=q_lower.split(),
            budget=5000,
            available_hours=12,
            top_n=4,
        )
        if not recs.empty:
            suggested_destinations = recs.to_dict(orient="records")
            rag_context = "\n".join(
                f"- {r['Name']} ({r['City']}, {r['State']}): Type {r['Type']}, Fee INR {r['Entrance Fee in INR']}, "
                f"Rating {r['Google review rating']}/5, Duration {r['time needed to visit in hrs']} hrs, Best {r['Best Time to visit']}"
                for _, r in recs.iterrows()
            )

    # 5. Call Gemini Fast (with 4.5s timeout and keep-alive connection)
    if settings.GEMINI_API_KEY:
        gemini_text = await _call_gemini_fast(q, rag_context)
        if gemini_text:
            if matched_dest is not None and matched_dest["Name"].lower() not in gemini_text.lower():
                gemini_text = f"### 📍 **{matched_dest['Name']}**\n\n{gemini_text}"
            resp = AssistantResponse(
                query=msg.query,
                answer=gemini_text,
                suggested_destinations=suggested_destinations,
                source="google-gemini (gemini-3.5-flash)",
            )
            _ASSISTANT_CACHE[cache_key] = resp
            return resp

    # 6. Instant Fallback: If Gemini is unreachable or took >4.5s, serve verified dataset points immediately!
    if matched_dest is not None:
        local_points = _format_destination_points(matched_dest)
        resp = AssistantResponse(
            query=msg.query,
            answer=local_points,
            suggested_destinations=suggested_destinations,
            source="dataset-verified-knowledge",
        )
        _ASSISTANT_CACHE[cache_key] = resp
        return resp

    if suggested_destinations:
        items = ["### 📍 Top Recommendations matching your query:", ""]
        for idx, r in enumerate(suggested_destinations, start=1):
            fee_text = "Free" if r["Entrance Fee in INR"] == 0 else f"₹{r['Entrance Fee in INR']}"
            off_day = r.get("Weekly Off", "None")
            off_text = f" | Closed: {off_day}" if off_day not in ["Not specified", "None", ""] else ""
            items.extend([
                f"**{idx}. {r['Name']}** ({r['Type']})",
                f"  • **Location:** {r['City']}, {r['State']}",
                f"  • **Entrance Fee:** {fee_text}",
                f"  • **Rating:** ⭐ {r['Google review rating']}/5",
                f"  • **Duration:** ⏱️ {r['time needed to visit in hrs']} hours (Best: {r['Best Time to visit']}){off_text}",
                f"  • **Significance:** {r.get('Significance', 'Popular Attraction')}",
                ""
            ])
        resp = AssistantResponse(
            query=msg.query,
            answer="\n".join(items),
            suggested_destinations=suggested_destinations,
            source="content-similarity-engine",
        )
        _ASSISTANT_CACHE[cache_key] = resp
        return resp

    fallback_points = [
        "### 💡 How to Query the Tourism Assistant:",
        "Please specify a destination, city, or interest to get exact points:",
        "• **Specific Places:** *'Tell me about Lotus Temple'*, *'Points for Amber Fort'*, *'Details on Red Fort'*",
        "• **Direct Question:** *'What is the entrance fee for Humayun's Tomb?'*, *'When is Lotus Temple closed?'*",
        "• **City/State:** *'Best places in Delhi'*, *'Forts in Rajasthan'*, *'Temples in Tamil Nadu'*",
    ]
    return AssistantResponse(
        query=msg.query,
        answer="\n".join(fallback_points),
        suggested_destinations=[],
        source="dataset-knowledge",
    )
