# Technical Architecture & System Design Documentation

**Project Title:** AI-Based Personalized Tourism Recommendation System  
**Version:** 2.0.0  
**Stack:** FastAPI, Python 3.12, scikit-learn, SQLAlchemy, SQLite, HTML5, CSS3, JavaScript, Leaflet.js

---

## 1. System Architecture Overview

The system is organized into a clean, 3-tier decoupled architecture:
1. **Frontend Presentation Tier:** Single-page responsive web client with navigation tabs, interactive Leaflet maps, a stay-area and accommodation planner, a multi-day itinerary builder, and modal dialogs.
2. **Backend Application & Service Tier:** High-performance asynchronous FastAPI service with modular API routers, JWT authentication, and in-memory TF-IDF caching.
3. **Data & Persistence Tier:** Relational database (SQLite locally, scalable to PostgreSQL) managed via SQLAlchemy ORM, alongside verified CSV datasets.

```mermaid
graph TD
    subgraph Client["Frontend Client (Browser)"]
        UI["Modern Web Interface (HTML5 / CSS3 / Vanilla JS)"]
        MAP["Leaflet.js Interactive Map"]
        STAY_UI["Stay-Area & Accommodation Finder"]
        AUTH_UI["JWT Auth & LocalStorage Session"]
        ITIN_UI["Day-by-Day Itinerary Builder"]
    end

    subgraph API["FastAPI Application Server"]
        ROUTER["Modular API Routers"]
        AUTH_SVC["Auth Service (bcrypt + PyJWT)"]
        REC_SVC["Recommendation Service (scikit-learn TF-IDF)"]
        ITIN_SVC["Itinerary Service & Budget Validation"]
        STAY_SVC["Stay Catalog & Tariff Search"]
        WEATHER_SVC["Weather Provider & Graceful Fallback"]
        ASSISTANT_SVC["AI Travel Assistant (Dataset Grounded)"]
    end

    subgraph Data["Persistence & Knowledge Layer"]
        DB[(SQLite Database / SQLAlchemy ORM)]
        STAY_CSV[("Stay areas & sourced accommodations CSVs")]
        CSV[("Verified Tourism Dataset (cleaned_tourism.csv)")]
        TFIDF_CACHE["In-Memory TF-IDF Vector Matrix"]
    end

    UI -->|REST API Requests / JSON| ROUTER
    MAP -->|Geo Queries| ROUTER
    AUTH_UI -->|Bearer JWT Header| ROUTER
    ITIN_UI -->|CRUD Requests| ROUTER
    STAY_UI -->|City, area & tariff filters| ROUTER

    ROUTER --> AUTH_SVC
    ROUTER --> REC_SVC
    ROUTER --> ITIN_SVC
    ROUTER --> STAY_SVC
    ROUTER --> WEATHER_SVC
    ROUTER --> ASSISTANT_SVC

    AUTH_SVC --> DB
    ITIN_SVC --> DB
    STAY_SVC --> DB
    STAY_CSV --> DB
    REC_SVC --> TFIDF_CACHE
    TFIDF_CACHE -.-> CSV
    ASSISTANT_SVC --> DB
```

---

## 2. Recommendation Algorithm Formulation

The core recommendation engine combines **Content-Based Filtering (Machine Learning / NLP)** with **Multi-Factor Business Rule Constraints**.

### 2.1 Content-Based Similarity (TF-IDF & Cosine Similarity)
A rich text document is constructed for every destination in the dataset:
$$\text{Document}_i = \text{Type}_i \parallel \text{Type}_i \parallel \text{Significance}_i \parallel \text{Significance}_i \parallel \text{Name}_i \parallel \text{City}_i \parallel \text{State}_i \parallel \text{BestTime}_i$$

*Note: $\text{Type}$ and $\text{Significance}$ are repeated to assign higher term-frequency weight to attraction categories in the vocabulary space.*

The vocabulary is transformed using scikit-learn's `TfidfVectorizer(ngram_range=(1, 2), stop_words='english')`. Given a user's interest query string $Q$, the query vector $\vec{v}_Q$ is matched against each destination vector $\vec{v}_i$ using Cosine Similarity:
$$\text{Sim}(Q, i) = \frac{\vec{v}_Q \cdot \vec{v}_i}{\|\vec{v}_Q\| \|\vec{v}_i\|} \in [0.0, 1.0]$$

If no specific interest keywords are provided by the user, $\text{Sim}(Q, i)$ is assigned a neutral baseline of $0.50$.

### 2.2 Multi-Factor Scoring Factors
1. **Rating Factor ($S_{\text{rating}}$):**
   $$S_{\text{rating}} = \frac{\text{Rating}}{5.0} \in [0.0, 1.0]$$
2. **Affordability Factor ($S_{\text{afford}}$):**
   $$S_{\text{afford}} = \max\left(0, 1.0 - \frac{\text{Entrance Fee}}{\max(\text{Budget}, 1.0)}\right) \in [0.0, 1.0]$$
3. **Duration Fit Factor ($S_{\text{duration}}$):**
   $$S_{\text{duration}} = \max\left(0, 1.0 - \left|\frac{\text{Time Needed}}{\text{Available Hours}} - 0.5\right| \times 0.5\right) \in [0.0, 1.0]$$
4. **Preferred Time Factor ($S_{\text{time}}$):**
   $$S_{\text{time}} = \begin{cases} 1.0 & \text{if preferred period matches or best time is 'All'} \\ 0.2 & \text{otherwise} \end{cases}$$

### 2.3 Composite Recommendation Score
The final score (scaled to $[0, 100]$) is computed using documented, configurable weights:
$$\text{Score} = \left( 0.35 \times \text{Sim}(Q, i) + 0.25 \times S_{\text{rating}} + 0.15 \times S_{\text{afford}} + 0.15 \times S_{\text{duration}} + 0.10 \times S_{\text{time}} \right) \times 100$$

---

## 3. Database Entity-Relationship Model

```mermaid
erDiagram
    USERS ||--o{ SAVED_DESTINATIONS : "saves"
    USERS ||--o{ ITINERARIES : "creates"
    DESTINATIONS ||--o{ SAVED_DESTINATIONS : "bookmarked in"
    DESTINATIONS ||--o{ ITINERARY_ACTIVITIES : "scheduled in"
    STAY_AREAS ||--o{ ACCOMMODATIONS : "contains"
    ACCOMMODATIONS ||--o{ ITINERARY_STAYS : "selected for"
    ITINERARIES ||--o| ITINERARY_STAYS : "plans one stay"
    ITINERARIES ||--o{ ITINERARY_DAYS : "contains"
    ITINERARY_DAYS ||--o{ ITINERARY_ACTIVITIES : "schedules"

    USERS {
        int id PK
        string email UK
        string hashed_password
        string full_name
        string role
        datetime created_at
    }

    DESTINATIONS {
        int id PK
        string name
        string state
        string city
        string type
        float rating
        int entrance_fee_inr
        float time_needed_hours
        string best_time
        string significance
        string weekly_off
        string airport_within_50km
    }

    STAY_AREAS {
        int id PK
        string city
        string state
        string name
        text description
        text nearby_attractions
        string budget_category
    }

    ACCOMMODATIONS {
        int id PK
        int stay_area_id FK
        string name
        string property_type
        string address
        int price_min_inr
        int price_max_inr
        text amenities
        string source_url
    }

    SAVED_DESTINATIONS {
        int id PK
        int user_id FK
        int destination_id FK
        text notes
        datetime created_at
    }

    ITINERARIES {
        int id PK
        int user_id FK
        string title
        text description
        float total_budget
        float estimated_entrance_fee
        datetime created_at
        datetime updated_at
    }

    ITINERARY_STAYS {
        int id PK
        int itinerary_id FK
        int accommodation_id FK
        int nights
        int nightly_min_inr
        int nightly_max_inr
    }

    ITINERARY_DAYS {
        int id PK
        int itinerary_id FK
        int day_number
        text notes
    }

    ITINERARY_ACTIVITIES {
        int id PK
        int itinerary_day_id FK
        int destination_id FK
        int order_index
        string time_slot
        float planned_hours
        text notes
    }
```

---

## 4. API Endpoints Directory

| Method | Endpoint | Description | Protected |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | System status & API version | No |
| `GET` | `/health` | Application health check | No |
| `GET` | `/recommend` | Personalized TF-IDF recommendation engine | No |
| `GET` | `/destinations` | Paginated catalog search and filters | No |
| `GET` | `/destinations/{id}` | Full destination detail lookup | No |
| `GET` | `/states` | List of all available Indian states | No |
| `GET` | `/destination-types` | List of unique attraction types | No |
| `GET` | `/stay-areas` | Suggested neighborhoods by city or state | No |
| `GET` | `/accommodations` | Filter accommodation by city, destination, area, type, and nightly tariff | No |
| `POST` | `/auth/register` | Register new user account | No |
| `POST` | `/auth/login` | Login and receive Bearer JWT token | No |
| `GET` | `/users/me` | Retrieve profile of authenticated user | Yes (User) |
| `GET` | `/users/me/saved-destinations` | List user's bookmarked destinations | Yes (User) |
| `POST` | `/users/me/saved-destinations` | Bookmark destination | Yes (User) |
| `DELETE` | `/users/me/saved-destinations/{id}` | Remove bookmarked destination | Yes (User) |
| `POST` | `/itineraries` | Create multi-day itinerary with activities and an optional stay plan | Yes (User) |
| `GET` | `/itineraries` | List all user itineraries | Yes (User) |
| `GET` | `/itineraries/{id}` | Get specific itinerary details | Yes (User) |
| `PUT` | `/itineraries/{id}` | Update itinerary title, budget, days, or stay plan | Yes (User) |
| `DELETE` | `/itineraries/{id}` | Delete itinerary | Yes (User) |
| `GET` | `/weather` | Weather forecast or seasonal climate guidance | No |
| `POST` | `/assistant/chat` | Dataset-grounded AI tourism chatbot | No |
| `GET` | `/admin/stats` | System metrics, users count, catalog volume | Yes (Admin) |

---

## 5. Security & Verification Strategy
- **Password Security:** Salted hashing with `bcrypt` (work factor 12).
- **Authentication:** Stateless JSON Web Tokens (`HS256`) with 24-hour expiration.
- **Resource Ownership:** All itinerary and saved destination operations verify that the authenticated `user_id` matches the resource owner.
- **Data Validation:** Strict Pydantic models validate input types, regex strings, and range constraints prior to execution.
