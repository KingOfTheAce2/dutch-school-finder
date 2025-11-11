# Dutch Education Navigator - Implementation Roadmap

## 🎯 Vision
Transform from "Dutch School Finder" to "Dutch Education Navigator" - a comprehensive platform covering the entire Dutch education journey from birth to PhD, multilingual, and better than scholenindebuurt.nl.

---

## ✅ Phase 1: Foundation (COMPLETED)
**Status:** ✓ Delivered

**What's Built:**
- FastAPI backend with school data
- React frontend with proximity search
- 188 schools (Primary + Secondary) with static data
- Interactive Leaflet map
- Distance-based search (solving "Amsterdam → Maastricht" problem)
- Quality ratings and filters
- Responsive design

**Data Coverage:**
- Primary schools: 125
- Secondary schools: 63
- Bilingual: 25
- International: 4
- Cities: 20

---

## 🚧 Phase 2: i18n & Comparison (IN PROGRESS)
**Status:** Foundation started, needs completion

### 2.1 Internationalization (i18n)
**Completed:**
- ✓ react-i18next integration
- ✓ Language files (English, Dutch)
- ✓ Translation infrastructure

**TODO:**
- [ ] Add Spanish, German, French translations
- [ ] Language switcher component in header
- [ ] Initialize i18n in App.tsx
- [ ] Translate all UI components
- [ ] Add language-specific number/date formatting
- [ ] SEO: Meta tags per language

**Files to Update:**
```
frontend/src/
├── locales/
│   ├── en.json ✓
│   ├── nl.json ✓
│   ├── es.json (NEW)
│   ├── de.json (NEW)
│   └── fr.json (NEW)
├── components/
│   ├── LanguageSwitcher.tsx (NEW)
│   ├── Header.tsx (update with i18n)
│   ├── SearchPanel.tsx (update with i18n)
│   └── ... (update all components)
└── main.tsx (import i18n)
```

### 2.2 School Comparison Feature
**Inspired by:** scholenindebuurt.nl comparison

**Features:**
- Select 2-5 institutions for side-by-side comparison
- Comparison table with key metrics:
  - Quality ratings
  - Distance from home
  - Student count
  - Denomination
  - Programs offered
  - Facilities
- Save comparisons to local storage
- Share comparison via URL
- Export to PDF

**Implementation:**
```
Backend:
- GET /compare?ids=1,2,3,4,5
- Returns detailed comparison data

Frontend:
- components/ComparisonBar.tsx (floating bar with selected items)
- components/ComparisonTable.tsx (full comparison view)
- localStorage for persistence
- URL params for sharing
```

---

## 📚 Phase 3: Expand Education Types
**Status:** Not started

### 3.1 Childcare (Kinderopvang) - Ages 0-4
**Why:** Complete the pre-school gap

**Data Requirements:**
- Daycare centers (dagopvang)
- After-school care (BSO - buitenschoolse opvang)
- Preschool/playgroups (peuterspeelzaal)

**Sources:**
- LRK (Landelijk Register Kinderopvang) - public registry
- GGD inspection reports
- Municipal databases

**Data Points:**
```python
class Childcare:
    name: str
    type: str  # dagopvang, BSO, peuterspeelzaal
    city: str
    address: str
    coordinates: (lat, lon)
    age_range: str  # "0-4 years"
    capacity: int
    rating: float  # GGD inspection
    opening_hours: str
    price_per_day: float  # if available
    languages: list[str]  # Dutch, English, etc.
    facilities: list[str]  # outdoor play, meals, etc.
```

**Estimated Data:**
- ~8,000-10,000 childcare centers nationwide
- Focus on 20 major cities initially

### 3.2 MBO - Vocational Education
**Why:** Cover 12-18 year olds choosing vocational path

**Data Requirements:**
- MBO institutions (~70 nationwide)
- Programs/courses offered
- Entry requirements
- Diploma types (Level 1-4)

**Sources:**
- MBO Raad (MBO Council)
- DUO data
- Institution websites

**Data Points:**
```python
class MBOInstitution:
    name: str
    city: str
    branches: list[Branch]  # multiple locations
    programs: list[Program]
    total_students: int
    rating: float
    facilities: list[str]
    international_programs: bool
```

**Programs:**
- Level 1: Assistentenopleiding (entry level)
- Level 2: Basisberoepsopleiding (basic vocational)
- Level 3: Vakopleiding (professional)
- Level 4: Middenkaderopleiding/Specialistenopleiding (middle management/specialist)

**Estimated Data:**
- 70 MBO institutions
- ~500 main programs

### 3.3 HBO - Universities of Applied Sciences
**Why:** Cover higher education practical track

**Data Requirements:**
- HBO institutions (~37 nationwide)
- Bachelor programs
- Master programs
- English-taught programs (key for expats!)

**Sources:**
- Vereniging Hogescholen
- DUO data
- NVAO (accreditation)
- Institution websites

**Data Points:**
```python
class HBOInstitution:
    name: str
    cities: list[str]  # multiple campuses
    programs: list[Program]
    total_students: int
    ranking: dict  # Keuzegids, Elsevier
    facilities: list[str]
    english_programs: list[Program]  # critical for expats
    tuition_fees: dict  # EU vs non-EU
```

**Key Programs to Highlight:**
- Technology (ICT, Engineering)
- Business (IB, Marketing)
- Health (Nursing, Physiotherapy)
- Education (Teacher training)
- Arts (Design, Music)

**Estimated Data:**
- 37 HBO institutions
- ~200 campuses
- ~400 bachelor programs
- ~200 master programs

### 3.4 WO - Research Universities
**Why:** Complete the education spectrum

**Data Requirements:**
- 14 research universities
- Bachelor programs
- Master programs
- PhD programs
- English programs (critical!)

**Sources:**
- VSNU (Association of Universities)
- DUO data
- University rankings (THE, QS)
- Institution websites

**Data Points:**
```python
class University:
    name: str
    city: str
    type: str  # general, technical, specialized
    faculties: list[Faculty]
    programs: list[Program]
    total_students: int
    international_students: int
    rankings: dict  # THE, QS, ARWU
    research_output: str
    english_programs: list[Program]
    tuition_fees: dict
```

**Universities:**
1. Leiden University
2. University of Amsterdam (UvA)
3. Vrije Universiteit Amsterdam
4. Utrecht University
5. Erasmus University Rotterdam
6. University of Groningen
7. Radboud University
8. Maastricht University
9. Delft University of Technology (TU Delft)
10. Eindhoven University of Technology (TU/e)
11. University of Twente
12. Wageningen University
13. Tilburg University
14. Open University

**Estimated Data:**
- 14 universities
- ~600 bachelor programs
- ~800 master programs
- ~350 English-taught programs

---

## 🗄️ Phase 4: Unified Data Model
**Status:** Design phase

### Database Schema Update

```sql
-- Universal education institution table
CREATE TABLE institutions (
    id INTEGER PRIMARY KEY,
    type VARCHAR,  -- childcare, primary, secondary, mbo, hbo, university
    name VARCHAR,
    city VARCHAR,
    address VARCHAR,
    latitude FLOAT,
    longitude FLOAT,

    -- Quality
    rating FLOAT,
    rating_source VARCHAR,  -- Inspectorate, GGD, Keuzegids, etc.

    -- Language
    is_bilingual BOOLEAN,
    is_international BOOLEAN,
    languages JSON,  -- [{"language": "en", "level": "full"}]

    -- Metadata
    website VARCHAR,
    phone VARCHAR,
    email VARCHAR,
    description TEXT,

    -- Type-specific data (JSON for flexibility)
    details JSON
);

-- Programs table (for MBO/HBO/University)
CREATE TABLE programs (
    id INTEGER PRIMARY KEY,
    institution_id INTEGER,
    name VARCHAR,
    level VARCHAR,  -- bachelor, master, mbo-4, etc.
    language VARCHAR,
    duration_months INTEGER,
    tuition_fee FLOAT,
    entry_requirements JSON,
    description TEXT
);

-- Comparison table (user-saved comparisons)
CREATE TABLE comparisons (
    id INTEGER PRIMARY KEY,
    user_session VARCHAR,  -- or user_id if we add auth
    institution_ids JSON,  -- [1, 5, 12, 34]
    created_at TIMESTAMP,
    share_token VARCHAR  -- for URL sharing
);
```

---

## 💡 Phase 5: Beyond scholenindebuurt.nl
**Status:** Feature wishlist

### What Makes Us Better?

**1. Complete Education Journey**
- scholenindebuurt.nl: Only primary/secondary schools
- **Us:** Childcare → Primary → Secondary → MBO/HBO/University

**2. Multilingual (i18n)**
- scholenindebuurt.nl: Dutch only
- **Us:** EN, NL, ES, DE, FR (expat-first)

**3. Proximity-First Design**
- scholenindebuurt.nl: City-based filtering
- **Us:** Address-based with km radius + "schools near me"

**4. Expat-Optimized**
- scholenindebuurt.nl: Generic Dutch audience
- **Us:**
  - Prominent bilingual/international filters
  - English-taught program highlights
  - Cultural context explanations
  - Visa/enrollment process guides

**5. Comparison Feature**
- scholenindebuurt.nl: Has comparison
- **Us:** Same, but cross-level (compare childcare AND primary for planning)

**6. Unified Search**
- scholenindebuurt.nl: Separate school search
- **Us:** "What's near me?" - childcare + schools + universities in one map

**7. Data Enrichment**
- scholenindebuurt.nl: Basic school data
- **Us:**
  - Waitlist estimates (crowd-sourced)
  - Parent reviews (moderated)
  - Open house dates
  - Admission deadlines
  - Integration with housing search (future: "Show homes near good schools")

---

## 🚀 Phase 6: Advanced Features (Future)
**Status:** Vision

### 6.1 Personalized Recommendations
```
"We have a 3-year-old and 7-year-old. Moving to Amsterdam from London."
→ AI suggests: Nearby childcare + primary + English programs
```

### 6.2 Enrollment Assistant
- Lottery system explainer
- Deadline calendar
- Required documents checklist
- Priority rules calculator

### 6.3 Community Features
- Parent reviews (verified)
- Waitlist crowd-sourcing
- School event calendar
- WhatsApp/Discord integration for expat parents

### 6.4 Housing Integration
- "Show apartments near schools rated 8+"
- Funda/Pararius API integration
- Commute time calculator

### 6.5 Financial Calculator
- Tuition cost estimator
- Childcare benefits calculator (kinderopvangtoeslag)
- Student finance options (DUO loans for HBO/University)

---

## 📊 Implementation Timeline

### Immediate (Week 1-2)
- ✓ i18n foundation
- [ ] Complete i18n for existing features
- [ ] Language switcher component
- [ ] Comparison bar UI
- [ ] Comparison API endpoint

### Short-term (Week 3-4)
- [ ] Childcare data model
- [ ] Sample childcare data (20 cities)
- [ ] Childcare search UI
- [ ] MBO data model
- [ ] Sample MBO data

### Medium-term (Month 2-3)
- [ ] HBO data ingestion
- [ ] University data ingestion
- [ ] Unified search interface
- [ ] Cross-type comparison
- [ ] SEO optimization

### Long-term (Month 4+)
- [ ] User accounts (optional)
- [ ] Saved searches
- [ ] Parent reviews (moderated)
- [ ] Enrollment assistant
- [ ] Mobile app (React Native)

---

## 🎨 UX/UI Improvements

### Navigation
```
+------------------------------------------+
|  Dutch Education Navigator  🏫 [EN ▼]   |
|  [Childcare] [Schools] [MBO] [HBO] [WO] |
+------------------------------------------+
|                                          |
|  Search: [Address input] [Radius: 5km]  |
|  Level: [All ▼]  Type: [All ▼]          |
|  [🌐 Bilingual] [🌍 International]       |
|                                          |
+------------------------------------------+
|  Map View  |  List View  |  Compare (3) |
+------------------------------------------+
```

### Comparison View
```
+----------------------------------+
| Comparing 3 institutions    [×]  |
+----------------------------------+
|           | School A | MBO B | HBO C |
|-----------|---------|-------|-------|
| Distance  | 1.2 km  | 3.5 km| 5.1 km|
| Rating    | 8.5     | 7.8   | 9.0   |
| Language  | Bilingual| Dutch| English|
| Students  | 450     | 2,500 | 15,000|
| Programs  | -       | 12    | 45    |
+----------------------------------+
```

---

## 📦 Data Sources Summary

| Type | Source | Availability | Est. Records |
|------|--------|--------------|--------------|
| Childcare | LRK Registry | ✓ Public | ~10,000 |
| Primary | DUO + Inspectorate | ✓ Public | ~6,500 |
| Secondary | DUO + Inspectorate | ✓ Public | ~650 |
| MBO | MBO Raad | ✓ Public | ~70 |
| HBO | Vereniging Hogescholen | ✓ Public | ~37 |
| University | VSNU | ✓ Public | 14 |
| Programs | Institution websites | ⚠️ Manual | ~2,000 |
| Reviews | Crowd-sourced | ⚠️ Manual | N/A |

✓ = Readily available
⚠️ = Requires manual collection

---

## 🔧 Technical Stack

**Backend:**
- FastAPI (Python)
- SQLAlchemy ORM
- PostgreSQL (production) / SQLite (dev)
- Celery (for data refresh tasks)

**Frontend:**
- React 18 + TypeScript
- react-i18next (multilingual)
- React-Leaflet (maps)
- Axios (API)
- LocalStorage (comparison persistence)

**DevOps:**
- Vercel/Netlify (frontend)
- Railway/Render (backend)
- GitHub Actions (CI/CD)
- Sentry (error tracking)

---

## 💰 Business Model (Optional)

1. **Freemium:**
   - Free: Basic search, 3 comparisons
   - Premium (€5/month): Unlimited comparisons, saved searches, alerts

2. **Affiliate:**
   - International schools (referral fees)
   - Housing platforms (integration)
   - Relocation services

3. **B2B:**
   - Employer partnerships (expat relocation packages)
   - Municipality integrations (official data feeds)

4. **Advertising:**
   - Targeted ads for education services
   - Language schools, tutoring

---

## 📝 Next Steps

**Priority 1 (This Sprint):**
1. Complete i18n integration
2. Build language switcher
3. Create comparison feature
4. Update README with new vision

**Priority 2 (Next Sprint):**
1. Expand data model for all education types
2. Ingest childcare data (top 10 cities)
3. Build unified search interface
4. Add MBO/HBO/University basic data

**Priority 3 (Future):**
1. Community features
2. Housing integration
3. Mobile app
4. AI recommendations

---

**Last Updated:** 2025-11-11
**Version:** 2.0 Roadmap
**Status:** Foundation complete, expansion in progress
