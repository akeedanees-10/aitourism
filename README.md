# AI-Based Personalized Tourism Recommendation System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=Python&logoColor=white)](https://www.python.org/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-TF--IDF-F7931E.svg?style=flat&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![SQLite](https://img.shields.io/badge/SQLite-SQLAlchemy-003B57.svg?style=flat&logo=SQLite&logoColor=white)](https://sqlite.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-Interactive%20Maps-199900.svg?style=flat&logo=Leaflet&logoColor=white)](https://leafletjs.com/)
[![Tests](https://img.shields.io/badge/Pytest-30%20Passing-brightgreen.svg?style=flat&logo=pytest&logoColor=white)](https://pytest.org/)

An advanced, full-stack tourism planning and recommendation platform for destinations across India. Combines **Machine Learning Content-Based Filtering (scikit-learn TF-IDF + Cosine Similarity)** with multi-factor business constraints, persistent SQLite database storage, JWT authentication, multi-day itinerary building with comprehensive budget enforcement (entrance fees + stay tariffs + food estimates), interactive Leaflet maps, a sourced hotel and stay-area planner, curated culinary discovery, weather guidance, and a dataset-grounded AI travel assistant.

---

## 1. Project Overview & Problem Statement

### 1.1 Problem Statement
Travelers frequently face information overload when planning journeys across India. Existing recommendation systems often present generic, disjointed lists or rely on naive substring matching that fails to capture the semantic nuance of user interests (e.g., matching *"peaceful spiritual getaway"* to religious or temple retreats). Furthermore, most platforms fail to integrate entrance fee budgets, visit duration scheduling, accommodation tariffs, and daily food expenses into a single cohesive interface.

### 1.2 Proposed Solution
This system provides an end-to-end intelligent travel advisor:
- **Semantic Content-Based Filtering:** Vectorizes destination descriptions, types, and significance using **scikit-learn TF-IDF** and computes cosine similarity against user interests.
- **Multi-Factor Business Ranking:** Blends content similarity with normalized Google review ratings, affordability relative to budget, duration fit, and preferred visiting period.
- **Relational Persistence:** Backed by SQLite and SQLAlchemy ORM to manage user accounts, bookmarked places, and day-by-day itineraries.
- **Interactive Geospatial Experience:** Powered by Leaflet.js with direct Google Maps and OpenStreetMap route links.
- **Comprehensive Trip Budgeting:** Live cost breakdown and warnings combining entrance fees, indicative accommodation tariffs, and daily food estimates across travelers and days.
- **Accommodation Planner:** Browse and select budget-friendly, standard, or premium stays by city, stay area, property type, and indicative tariffs; easily attach nights and edit/remove from itineraries.
- **Food & Dining Planning:** Optional culinary budgeting with preset tiers (Budget ₹350/day, Standard ₹750/day, Premium ₹1,600/day), custom daily rates, or curated regional eateries.
- **Factual AI Travel Assistant:** Answers queries about Indian tourist spots using verified dataset facts with zero hallucinations.

---

## 2. Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Leaflet.js (OpenStreetMap), Responsive UI |
| **Backend API** | Python 3.12, FastAPI, Uvicorn, Pydantic V2, Starlette |
| **Machine Learning** | scikit-learn (`TfidfVectorizer`, `cosine_similarity`), NumPy, Pandas |
| **Database & ORM** | SQLite, SQLAlchemy 2.0 (designed to easily migrate to PostgreSQL) |
| **Security & Auth** | Passwords hashed with `bcrypt`, stateless authentication via `PyJWT` (HS256) |
| **Testing** | pytest 9.1+, HTTPX, FastAPI TestClient (24 automated tests passing) |

---

## 3. System Architecture & Workflow

```
   ┌────────────────────────────────────────────────────────┐
   │                   Browser Frontend                     │
   │ Explore | Stay Planner | Leaflet Map | Itinerary Plan  │
   └──────────────────────────┬─────────────────────────────┘
                              │ JSON / REST API (CORS)
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │                 FastAPI Backend Server                 │
   │ /recommend | /destinations | /accommodations | /auth  │
   └───────────────┬────────────────────────┬───────────────┘
                   │                        │
         SQLAlchemy ORM            scikit-learn TF-IDF
                   ▼                        ▼
   ┌───────────────────────┐      ┌─────────────────────────┐
   │  SQLite (tourism.db)  │      │ In-Memory TF-IDF Index  │
   │ Users, Trips, Stays   │      │ (cleaned_tourism.csv)   │
   └───────────────────────┘      └─────────────────────────┘
```

---

## 4. Dataset Description & Preprocessing

The system utilizes verified tourism records covering major attractions across India (`data/Top Indian Places to Visit.csv` and `data/cleaned_tourism.csv`).

### 4.1 Dataset Fields
- `id`: Stable 1-indexed primary key integer
- `Name`: Attraction name (e.g., India Gate, Lotus Temple, Red Fort)
- `State` & `City`: Geographic location in India (32 unique states covered)
- `Type`: Attraction classification (78 unique types: Fort, Temple, Beach, Cave, Park, etc.)
- `Establishment Year`: Construction or founding year
- `time needed to visit in hrs`: Typical visiting duration (0.5 to 7.0 hours)
- `Google review rating`: Public rating (1.4 to 4.9 out of 5.0, Mean: 4.48)
- `Entrance Fee in INR`: Entrance fee (₹0 to ₹7,500, Median: ₹0)
- `Best Time to visit`: Recommended visiting period (Morning, Afternoon, Evening, All)
- `Significance`: Cultural, historical, religious, or architectural significance
- `Weekly Off`: Scheduled closure day (e.g., Monday, Friday, None)
- `Airport with 50km Radius`: Accessibility indicator (Yes / No)

### 4.2 Data Quality & Normalization
The reproducible audit script (`backend/explore_data.py`):
1. Preserves the raw dataset `Top Indian Places to Visit.csv` without modification.
2. Strips all leading/trailing whitespace across text fields.
3. Fixes typographical inconsistencies (e.g. `'Maharastra'` $\rightarrow$ `'Maharashtra'`).
4. Normalizes visiting periods (`'All '` and `'Anytime'` $\rightarrow$ `'All'`).
5. Drops duplicate records (reducing raw rows from 325 to 323 unique attractions).
6. Assigns stable sequential primary keys (`id`).

### 4.3 Stay-Area & Accommodation Catalog

`data/stay_areas.csv` and `data/accommodations.csv` provide a small starter catalog for Agra, Delhi, Jaipur, and Varanasi. Listings are linked to neighborhoods and include property type, amenities, source links, and published tariff ranges where available. The backend seeds these records into SQLite on startup. Tariffs are indicative and should be confirmed with each property; the app does not provide live availability or booking.

Starter sources include the [Taj Mahal accommodation directory](https://tajmahal.gov.in/accomodation.aspx), [Delhi Tourism budget-hotel directory](https://delhitourism.gov.in/accommodation/budget_eco_hotel.html), [RTDC Hotel Swagatam listing and 2026–27 tariff](https://rtdc.tourism.rajasthan.gov.in/Client/HotelDetails.aspx?HotelID=JaipurSwagatam), and the official [Hotel Vishwanath Inn](https://hotelvishwanath.in/) and [Hotel Rudra Ganga](https://rudraganga.in/) sites.

---

## 5. Recommendation Engine Details

Located in [`backend/recommend.py`](file:///C:/Users/anees/OneDrive/Desktop/AI_Tourism_Recommendation/backend/recommend.py):

### 5.1 Content Similarity (TF-IDF)
Corpus text is constructed by combining:
```python
corpus = (df["Type"] + " " + df["Type"] + " " + df["Significance"] + " " + df["Significance"] + " " + df["Name"] + " " + df["City"] + " " + df["State"] + " " + df["Best Time to visit"]).str.lower()
```
The query string is transformed into a vector and compared via **Cosine Similarity**:
$$\text{Sim}(Q, i) = \frac{\vec{v}_Q \cdot \vec{v}_i}{\|\vec{v}_Q\| \|\vec{v}_i\|}$$

### 5.2 Multi-Factor Formula & Weights
The final composite score ($0 \text{ to } 100$) is computed as:
$$\text{Score} = (0.35 \times \text{Similarity} + 0.25 \times \text{Rating} + 0.15 \times \text{Affordability} + 0.15 \times \text{DurationFit} + 0.10 \times \text{Timing}) \times 100$$

Every recommendation includes a human-readable **Explanation** explaining why it was chosen (e.g., *"Strong content match for your travel interests (82%); Highly rated (4.6/5); Free entrance"*).

---

## 6. Local Setup & Execution Guide (Windows PowerShell)

### Prerequisites
- Python 3.12 installed
- Windows PowerShell

### 6.1 Clone & Navigate
```powershell
cd C:\Users\anees\OneDrive\Desktop\AI_Tourism_Recommendation
```

### 6.2 Activate Virtual Environment & Install Dependencies
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 6.3 Run Dataset Cleaning & Audit Script (Optional)
```powershell
python backend/explore_data.py
```

### 6.4 Launch the Unified Web Application (Recommended)
You can launch the complete web application with a single command:
```powershell
python run.py
```
*Or on Windows, simply double-click **`start.bat`**.*

This command:
1. Initializes SQLite tables and seeds starter datasets.
2. Serves both the interactive frontend web application and REST API at **`http://127.0.0.1:8000`**.
3. Automatically opens the web application in your default browser.

### 6.5 Alternative: Manual Uvicorn Launch
```powershell
python -m uvicorn backend.main:app --reload
```
- Web Application: **`http://127.0.0.1:8000`** (or `http://127.0.0.1:8000/app`)
- Interactive Swagger API Docs: **`http://127.0.0.1:8000/docs`**
- System Health Check: **`http://127.0.0.1:8000/health`**

---

## 7. Running Automated Tests

Run the complete test suite with pytest:
```powershell
python -m pytest -v tests
```
**Test Results: 30 tests passing**
- `tests/test_recommend.py`: Validates TF-IDF similarity, score bounds, determinism, hard budget/hour constraints, and empty states.
- `tests/test_destinations.py`: Validates catalog pagination, state/type listings, and single destination lookups.
- `tests/test_auth.py`: Validates user registration, duplicate prevention, password hashing, and JWT token protection.
- `tests/test_itineraries.py`: Validates saved bookmarks, multi-day itinerary creation, update, and deletion.
- `tests/test_assistant_and_admin.py`: Validates weather fallback, dataset assistant chat, and role-based admin stats.

---

## 8. College Project Evaluation & Demonstration Steps

During evaluation, demonstrate the system in this sequence:
1. **Show Dataset Integrity:** Explain `data/Top Indian Places to Visit.csv` and run `backend/explore_data.py` to demonstrate data cleaning.
2. **Show Recommendation Engine:** Open `http://127.0.0.1:8000/docs` or `frontend/index.html`. Type `historical, fort` under interests with budget `₹100`. Show how forts rank top with explainable score breakdowns.
3. **Show Interactive Map:** Click **Interactive Map** in the frontend to demonstrate Leaflet pins across India with direct direction links.
4. **Show User Authentication & Saved Trips:** Register a new user, save a destination to favorites, and show it appearing under **Saved Places**.
5. **Show Multi-Day Itinerary Planner:** Add activities for Day 1 and Day 2. Set budget to ₹100 and demonstrate the live **budget warning alert** when entrance fees exceed budget. Print/export the itinerary.
6. **Show AI Assistant:** Ask questions like *"Tell me about Lotus Temple"* or *"Recommend forts in Rajasthan"* to demonstrate zero-hallucination dataset retrieval.
7. **Show Stay Planner:** Search Agra, Delhi, Jaipur, or Varanasi by stay area and property type. Select a listing and number of nights, then show the lodging estimate in the itinerary budget.
8. **Run Automated Tests:** Execute `python -m pytest -v tests` in PowerShell to prove 24/24 passing tests.

---

## 9. Limitations & Future Enhancements

### Current Limitations
- The dataset currently covers 323 curated Indian attractions; expanding to thousands of localized attractions would enhance rural coverage.
- The starter accommodation catalog covers four cities, uses published directory tariffs where available, and does not show live room availability or booking confirmation.
- Stay matching currently uses city and neighborhood names; exact hotel-to-attraction distances need accurate coordinates for both records.
- Live weather requires an external OpenWeatherMap API key (the system uses seasonal climate guidance when offline).

### Planned Enhancements
- Integration with OpenRouteService for real-time driving distances between itinerary stops.
- Mobile application using React Native or Flutter.
- User review submission with NLP sentiment analysis.
