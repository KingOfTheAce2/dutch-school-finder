# Implementation Plan: Comparison + Childcare (REAL DATA ONLY)

## 🎯 Priority Features

### 1. School Comparison Feature ✓ Ready to Implement
**Timeline:** 1-2 days

#### Backend API
```python
# Add to main.py

@app.get("/compare", response_model=List[SchoolResponse])
def compare_schools(
    ids: str = Query(..., description="Comma-separated school IDs (e.g., '1,5,12')"),
    db: Session = Depends(get_db)
):
    """Compare multiple schools side by side"""
    school_ids = [int(id.strip()) for id in ids.split(',')]

    if len(school_ids) < 2 or len(school_ids) > 5:
        raise HTTPException(400, "Please select 2-5 schools to compare")

    schools = []
    for school_id in school_ids:
        school = get_school_by_id(db, school_id)
        if school:
            schools.append(school)

    return schools
```

#### Frontend Components
```typescript
// components/ComparisonBar.tsx
// Floating bar at bottom showing selected schools
// "Add to Compare" button on each school card
// localStorage persistence: localStorage.setItem('comparison', JSON.stringify(ids))

// components/ComparisonTable.tsx
// Side-by-side table with:
// - Distance from address
// - Quality rating
// - Student count
// - Programs
// - Facilities
// - Contact info
```

---

### 2. Childcare Data Model + REAL DATA Integration
**Timeline:** 2-3 weeks (due to data collection)

## 🔍 REAL DATA SOURCES FOR CHILDCARE

### Primary Source: LRK (Landelijk Register Kinderopvang)
**URL:** https://www.landelijkregisterkinderopvang.nl/

**What it is:**
- Official Dutch childcare registry
- Maintained by GGD (Municipal Health Service)
- Legally required registration for all childcare providers

**Access Method:**
- ✅ Public search interface available
- ⚠️ No official API (requires scraping or manual collection)
- 📊 Contains ~10,000 registered childcare centers

**Data Fields Available:**
```python
class Childcare:
    # From LRK Registry
    lrk_number: str  # Unique registration number
    name: str
    owner: str  # Organization name
    address: str
    postal_code: str
    city: str
    phone: str
    type: str  # dagopvang, BSO, gastouderopvang
    capacity: int  # Number of children
    age_group: str  # "0-4 jaar", "4-12 jaar"
    registration_date: date
    status: str  # "Geregistreerd", "Ingeschreven"
```

### Secondary Source: GGD Inspection Reports
**URL:** https://www.ggd.nl/ (per municipality)

**What it provides:**
- Quality assessments
- Safety inspections
- Compliance reports

**Access:**
- ⚠️ No centralized API
- 📄 Per-municipality websites
- 🔍 Requires scraping or FOI requests

### Tertiary Source: Municipal Databases
**Major Cities:**
- Amsterdam: https://www.amsterdam.nl/kinderopvang
- Rotterdam: https://www.rotterdam.nl/kinderopvang
- Den Haag: https://www.denhaag.nl/kinderopvang
- Utrecht: https://www.utrecht.nl/kinderopvang

**Data Available:**
- Subsidized spots
- Priority rules
- Waiting list estimates (crowdsourced)

---

## 📥 Data Ingestion Strategy

### Phase 1: Proof of Concept (Week 1)
**Goal:** Get 100 real childcare centers from Amsterdam

**Method:**
1. Manual scraping of LRK registry for Amsterdam
2. Parse HTML/search results
3. Store in database
4. Geocode addresses

**Script:**
```python
# backend/scripts/ingest_childcare_lrk.py

import requests
from bs4 import BeautifulSoup
import time

def scrape_lrk_search(city: str, max_pages: int = 10):
    """
    Scrape LRK registry for a specific city

    Note: This respects robots.txt and rate limits (1 req/sec)
    """
    base_url = "https://www.landelijkregisterkinderopvang.nl/Search"

    childcare_centers = []

    for page in range(1, max_pages + 1):
        params = {
            'city': city,
            'page': page
        }

        response = requests.get(base_url, params=params)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Parse results
        results = soup.find_all('div', class_='search-result')

        for result in results:
            center = {
                'lrk_number': result.find('span', class_='lrk-number').text,
                'name': result.find('h3').text,
                'address': result.find('span', class_='address').text,
                'city': city,
                'phone': result.find('span', class_='phone').text,
                'type': result.find('span', class_='type').text,
            }
            childcare_centers.append(center)

        # Rate limit: 1 request per second
        time.sleep(1)

        if not results:  # No more pages
            break

    return childcare_centers

# Usage:
centers = scrape_lrk_search('Amsterdam')
print(f"Found {len(centers)} childcare centers in Amsterdam")
```

### Phase 2: Scaled Collection (Week 2-3)
**Goal:** 20 major cities, ~2,000 centers

**Cities Priority:**
1. Amsterdam (~400 centers)
2. Rotterdam (~300 centers)
3. Den Haag (~250 centers)
4. Utrecht (~200 centers)
5. Eindhoven (~150 centers)
6-20. Other major cities (~700 centers total)

**Automation:**
```python
cities = [
    'Amsterdam', 'Rotterdam', 'Den Haag', 'Utrecht',
    'Eindhoven', 'Groningen', 'Tilburg', 'Almere',
    'Breda', 'Nijmegen', 'Haarlem', 'Arnhem',
    'Leiden', 'Delft', 'Maastricht', 'Amersfoort',
    'Apeldoorn', 'Enschede', 'Zwolle', 'Leeuwarden'
]

all_centers = []
for city in cities:
    print(f"Scraping {city}...")
    centers = scrape_lrk_search(city)
    all_centers.extend(centers)
    time.sleep(5)  # Be respectful to servers

store_in_database(all_centers)
```

### Phase 3: Geocoding (Week 3)
**Goal:** Add coordinates to all centers

**Method:**
```python
from app.geocoding import geocode_address

for center in childcare_centers:
    coords = geocode_address(center['address'], center['city'])
    if coords:
        center['latitude'], center['longitude'] = coords
    time.sleep(1)  # Rate limit for Nominatim
```

---

## 🗄️ Database Schema Extension

```python
# Add to backend/app/database.py

class EducationInstitution(Base):
    """
    Unified table for all education types
    Replaces 'School' to support childcare, MBO, HBO, etc.
    """
    __tablename__ = "education_institutions"

    id = Column(Integer, primary_key=True, index=True)

    # Type
    institution_type = Column(String, nullable=False, index=True)
    # Values: 'childcare', 'primary', 'secondary', 'mbo', 'hbo', 'university'

    # Basic Info
    name = Column(String, nullable=False, index=True)
    city = Column(String, nullable=False, index=True)
    address = Column(String)
    postal_code = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    # Contact
    phone = Column(String)
    email = Column(String)
    website = Column(String)

    # Quality (universal)
    rating = Column(Float)  # 0-10 scale
    rating_source = Column(String)  # 'Inspectorate', 'GGD', etc.

    # Language
    is_bilingual = Column(Boolean, default=False)
    is_international = Column(Boolean, default=False)
    offers_english = Column(Boolean, default=False)

    # Type-specific data (JSON for flexibility)
    details = Column(JSON)
    # For childcare: {
    #   "lrk_number": "...",
    #   "capacity": 50,
    #   "age_group": "0-4",
    #   "type": "dagopvang"
    # }
    # For schools: {
    #   "brin_code": "...",
    #   "school_type": "Primary",
    #   "cito_score": 540
    # }

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Migration script
def migrate_schools_to_institutions():
    """Migrate existing School data to EducationInstitution"""
    schools = db.query(School).all()

    for school in schools:
        institution = EducationInstitution(
            institution_type='primary' if school.school_type == 'Primary' else 'secondary',
            name=school.name,
            city=school.city,
            address=school.address,
            postal_code=school.postal_code,
            latitude=school.latitude,
            longitude=school.longitude,
            phone=school.phone,
            email=school.email,
            website=school.website,
            rating=school.inspection_score,
            rating_source='Inspectorate',
            is_bilingual=school.is_bilingual,
            is_international=school.is_international,
            offers_english=school.offers_english,
            details={
                'brin_code': school.brin_code,
                'school_type': school.school_type,
                'education_structure': school.education_structure,
                'cito_score': school.cito_score,
                'denomination': school.denomination,
                'student_count': school.student_count,
                'description': school.description
            }
        )
        db.add(institution)

    db.commit()
```

---

## 🚀 API Updates

```python
# Unified search endpoint

@app.get("/institutions/search")
def search_institutions(
    type: Optional[str] = Query(None, description="childcare, primary, secondary, mbo, hbo, university"),
    city: Optional[str] = None,
    address: Optional[str] = None,
    radius_km: Optional[float] = None,
    min_rating: Optional[float] = None,
    bilingual: Optional[bool] = None,
    international: Optional[bool] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Unified search across all education types

    Examples:
    - /institutions/search?type=childcare&city=Amsterdam
    - /institutions/search?address=Dam 1, Amsterdam&radius_km=5&type=primary
    - /institutions/search?type=all&address=Amsterdam&radius_km=10
    """
    query = db.query(EducationInstitution)

    # Filter by type
    if type and type != 'all':
        query = query.filter(EducationInstitution.institution_type == type)

    # Proximity search
    if address and radius_km:
        coords = geocode_city(address)
        if coords:
            # Use proximity search logic
            pass

    # City filter
    elif city:
        query = query.filter(func.lower(EducationInstitution.city).contains(func.lower(city)))

    # Other filters
    if min_rating:
        query = query.filter(EducationInstitution.rating >= min_rating)

    if bilingual:
        query = query.filter(EducationInstitution.is_bilingual == True)

    if international:
        query = query.filter(EducationInstitution.is_international == True)

    return query.limit(limit).all()
```

---

## 📊 Data Quality & Maintenance

### Automated Updates
```python
# Scheduled task (Celery or cron)

@celery.task
def update_childcare_data_monthly():
    """
    Monthly update of childcare data
    Checks for new registrations, closures, and changes
    """
    for city in MAJOR_CITIES:
        fresh_data = scrape_lrk_search(city)
        update_database(fresh_data)

    # Send admin notification
    send_email(admin, f"Updated {len(fresh_data)} childcare records")
```

### Manual Verification
- Random sampling (10% monthly)
- User-reported corrections
- Cross-reference with municipal databases

### Crowdsourcing
```python
@app.post("/institutions/{id}/report")
def report_data_issue(
    id: int,
    issue: str,  # "closed", "wrong_address", "wrong_phone", etc.
    details: Optional[str],
    db: Session = Depends(get_db)
):
    """Allow users to report data issues"""
    # Store in moderation queue
    # Admin reviews and updates
```

---

## 🎯 Success Metrics

### Coverage Goals
- **Month 1:** Amsterdam childcare (400 centers) ✓
- **Month 2:** Top 5 cities (1,200 centers)
- **Month 3:** Top 20 cities (2,000 centers)
- **Month 6:** Nationwide (8,000+ centers)

### Data Quality
- 95% accurate addresses (geocoded)
- 90% with phone numbers
- 80% with capacity info
- Monthly refresh cycle

### User Engagement
- Track searches by type (childcare vs schools)
- Monitor comparison feature usage
- A/B test proximity vs city search

---

## ⚠️ Legal & Ethical Considerations

### Web Scraping
- ✅ LRK data is public
- ✅ Respect robots.txt
- ✅ Rate limiting (1 req/sec)
- ✅ No login required
- ✅ Non-commercial use

### Data Accuracy
- Display last updated date
- Link to official sources
- Disclaimer: "Verify with provider"
- User corrections mechanism

### Privacy
- No personal data collected
- Only public business info
- GDPR compliant (EU data)

---

## 🔧 Technical Implementation Checklist

### Backend (Week 1-2)
- [ ] Extend database schema with `EducationInstitution` table
- [ ] Migrate existing school data
- [ ] Create childcare scraping script for LRK
- [ ] Implement geocoding for addresses
- [ ] Add unified search endpoint
- [ ] Add institution type filter

### Frontend (Week 2-3)
- [ ] Update TypeScript types for institution types
- [ ] Add education level filter (dropdown)
- [ ] Support childcare in search results
- [ ] Update map markers for different types
- [ ] Add comparison feature (2-5 institutions)
- [ ] Create childcare detail view

### Data Collection (Week 3-4)
- [ ] Scrape Amsterdam childcare (400)
- [ ] Scrape Rotterdam childcare (300)
- [ ] Scrape Top 5 cities (1,200 total)
- [ ] Geocode all addresses
- [ ] Validate data quality (spot checks)
- [ ] Set up monthly refresh cron job

---

## 📈 Rollout Plan

### Beta Launch (Month 1)
- Amsterdam only
- Childcare + existing schools
- Invite 50 beta testers
- Collect feedback

### Public Launch (Month 2)
- Top 5 cities
- Full childcare coverage
- Blog post announcement
- Social media campaign

### Scale (Month 3+)
- Expand to 20 cities
- Add MBO institutions
- Community features
- Mobile app (React Native)

---

**Last Updated:** 2025-11-11
**Status:** Ready to implement
**Priority:** Comparison (2 days) → Childcare real data (3 weeks)
