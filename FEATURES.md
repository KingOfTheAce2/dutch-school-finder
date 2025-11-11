# 🎯 Extended Features Documentation

This document describes all the extended features implemented in the Dutch School Finder platform.

## 📋 Table of Contents

1. [Transportation Integration](#1-transportation-integration-)
2. [Admission Tracker](#2-admission-tracker-)
3. [School Events & Open Houses](#3-school-events--open-houses-)
4. [Export & Share](#4-export--share-)
5. [Academic Performance Trends](#5-academic-performance-trends-)
6. [Special Needs Support](#6-special-needs-support-)
7. [After-School Care (BSO)](#7-after-school-care-bso-)
8. [API Reference](#api-reference)

---

## 1. Transportation Integration 🚌

### Overview
Calculate and display travel times to schools using multiple modes of transportation, tailored for the Netherlands where cycling is extremely common.

### Features
- **Walking** - 5 km/h average speed
- **Cycling** - 15 km/h average (Dutch cyclists are fast!)
- **Public Transit** - Integration-ready for NS (trains) and 9292 (all transit)
- **Driving** - Urban traffic calculations
- **School Bus** - Availability and pickup information

### API Endpoints

#### Get Transportation Options
```http
GET /api/transportation/{school_id}?from_address={address}
```

**Example:**
```bash
curl "http://localhost:8000/api/transportation/1?from_address=Dam 1, Amsterdam"
```

**Response:**
```json
[
  {
    "mode": "walking",
    "duration_minutes": 12,
    "distance_km": 1.0,
    "display": "🚶 12 min walk"
  },
  {
    "mode": "cycling",
    "duration_minutes": 4,
    "distance_km": 1.0,
    "display": "🚴 4 min by bike"
  },
  {
    "mode": "public_transit",
    "duration_minutes": 18,
    "distance_km": 1.0,
    "display": "🚌 18 min (bus/tram)",
    "transit_details": {
      "lines": ["Bus 22"],
      "transfers": 0,
      "wait_time_minutes": 5
    }
  }
]
```

### Configuration

Set API keys in `.env` for live data:
```bash
NS_API_KEY=your_ns_api_key
9292_API_KEY=your_9292_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_key
```

---

## 2. Admission Tracker 📅

### Overview
Track application deadlines, timelines, and status for school enrollment across different municipalities.

### Features
- Application timeline per school and academic year
- Deadline tracking with calendar export
- Municipality-specific enrollment systems (Prewonen, Schoolwijzer, etc.)
- Required documents checklist
- Application status tracking ("Applied", "Waiting", "Accepted", etc.)
- Email reminders for deadlines (future feature)

### API Endpoints

#### Get Admission Timeline
```http
GET /api/admission-timeline/{school_id}?academic_year=2024-2025
```

#### Get Upcoming Deadlines
```http
GET /api/admission-deadlines?days_ahead=30&municipality=Amsterdam
```

#### Track Application Status
```http
POST /api/application-status
Content-Type: application/json

{
  "school_id": 1,
  "user_email": "parent@example.com",
  "status": "applied",
  "notes": "Submitted all documents"
}
```

### Municipality Integrations

| Municipality | System | Notes |
|--------------|--------|-------|
| Amsterdam | Prewonen | Primary schools enrollment |
| Rotterdam | Municipal Portal | Centralized system |
| Utrecht | School Enrollment API | Direct school application |
| Den Haag | Schoolwijzer | Municipal coordination |

---

## 3. School Events & Open Houses 🎓

### Overview
Aggregated calendar of school events, open days, and information sessions.

### Features
- Open houses (kijkdagen)
- Information evenings for parents
- School tours (in-person and virtual)
- Application period notifications
- Language filtering (Dutch/English/Both)
- Calendar export (iCal format)

### API Endpoints

#### Get Events
```http
GET /api/events?city=Amsterdam&language=English&limit=20
```

#### Export to Calendar
```http
GET /api/events/calendar/ical?school_id=1
```

Downloads `.ics` file compatible with:
- Google Calendar
- Apple Calendar
- Outlook
- Any iCal-compatible calendar

#### Create Event (for schools/admins)
```http
POST /api/events
Content-Type: application/json

{
  "school_id": 1,
  "title": "Open House - Spring 2025",
  "event_type": "open_house",
  "start_datetime": "2025-03-15T10:00:00",
  "end_datetime": "2025-03-15T12:00:00",
  "language": "Both",
  "requires_booking": true,
  "booking_url": "https://school.nl/book"
}
```

---

## 4. Export & Share 📄

### Overview
Export school comparisons and share them with family, partners, or advisors.

### Features
- CSV export for spreadsheet analysis
- PDF generation (future)
- Shareable comparison links (30-day expiration)
- Social media sharing (future)
- Print-friendly views

### API Endpoints

#### Export to CSV
```http
GET /api/export/schools/csv?ids=1,5,12
```

Downloads CSV file with complete school information.

#### Create Shareable Link
```http
POST /api/share/comparison
Content-Type: application/json

{
  "school_ids": [1, 5, 12],
  "filters_applied": {
    "city": "Amsterdam",
    "bilingual": true
  }
}
```

**Response:**
```json
{
  "share_id": "abc123xyz",
  "created_at": "2025-01-15T10:00:00",
  "expires_at": "2025-02-14T10:00:00",
  "view_count": 0
}
```

Share URL: `https://dutchschoolfinder.nl/share/abc123xyz`

#### View Shared Comparison
```http
GET /api/share/{share_id}
GET /api/share/{share_id}/schools
```

---

## 5. Academic Performance Trends 📈

### Overview
Historical performance data showing school improvement or decline over time.

### Features
- 5-year CITO score trends
- Inspection rating history
- Student enrollment trends
- Teacher turnover rates
- Performance badges:
  - 🌟 **Rising Star** - Rapidly improving (10+ point increase)
  - 🏆 **Consistent Excellence** - Sustained high performance
  - ⚠️ **Needs Attention** - Declining performance

### API Endpoints

#### Get Performance History
```http
GET /api/performance/{school_id}?years=5
```

#### Get Performance Trend Analysis
```http
GET /api/performance/{school_id}/trend
```

**Response:**
```json
{
  "school_id": 1,
  "school_name": "Example Primary School",
  "trend_direction": "improving",
  "years_of_data": 5,
  "total_change": 11.0,
  "average_annual_change": 2.2,
  "badge": "rising_star",
  "performance_history": [
    {
      "academic_year": "2023-2024",
      "cito_score": 544,
      "inspection_score": 8.5,
      "student_count": 250
    }
  ]
}
```

### Visualization Ideas
- Line charts showing CITO score progression
- Color-coded trend indicators
- Comparison with city/national averages

---

## 6. Special Needs Support ♿

### Overview
Comprehensive filtering and information for families with special education needs.

### Features

#### Support Types
- Dyslexia support
- ADHD accommodations
- Autism spectrum support
- Gifted and talented programs
- Physical accessibility
- Visual/hearing impairment support
- Speech therapy
- Occupational therapy

#### Accessibility Features
- Wheelchair accessible
- Elevator availability
- Accessible restrooms
- Specialized classrooms

### API Endpoints

#### Get Special Needs Info
```http
GET /api/special-needs/{school_id}
```

#### Search Schools by Special Needs
```http
GET /api/schools/special-needs?dyslexia=true&wheelchair_accessible=true&city=Amsterdam
```

Returns schools matching ANY of the criteria (OR logic).

### Data Sources
- Inspectorate special education reports
- School websites and policies
- Parent testimonials
- Municipality special education offices

---

## 7. After-School Care (BSO) 🎨

### Overview
BSO (Buitenschoolse Opvang) information for working parents.

### Features

#### Basic Information
- Provider name and contact
- Location (same as school or separate)
- Operating hours (typically until 18:00-18:30)
- Holiday programs

#### Services
- Homework help
- Sports activities
- Arts and crafts
- Outdoor play

#### Practical Details
- Monthly costs (€280-520 typical)
- Subsidy eligibility
- Capacity and waiting lists
- Registration process

### API Endpoints

#### Get BSO for School
```http
GET /api/after-school-care/{school_id}
```

#### Search BSO with Filters
```http
GET /api/after-school-care/search?max_cost=400&offers_homework_help=true&no_waiting_list=true
```

**Response:**
```json
[
  {
    "provider_name": "KidsFirst BSO",
    "same_location_as_school": true,
    "opening_time": "15:00",
    "closing_time": "18:30",
    "monthly_cost_euros": 380.0,
    "subsidy_eligible": true,
    "offers_homework_help": true,
    "has_waiting_list": false,
    "activities": ["Sports", "Arts and crafts", "Outdoor play"],
    "registration_url": "https://kidsfirst.nl/register"
  }
]
```

---

## API Reference

### Base URL
```
Development: http://localhost:8000
Production: https://api.dutchschoolfinder.nl
```

### Authentication
Currently no authentication required. Future versions will support:
- API keys for rate limiting
- User accounts for personalized features
- OAuth for school administrators

### Rate Limiting
No rate limits in current version. Production will implement:
- 100 requests/minute for anonymous users
- 1000 requests/minute for authenticated users

### Error Responses

```json
{
  "detail": "Error message here"
}
```

Common status codes:
- `200` - Success
- `400` - Bad request (invalid parameters)
- `404` - Resource not found
- `500` - Server error

---

## Database Schema

### New Tables

#### `transportation_routes`
Stores calculated transportation routes (cached).

#### `admission_timelines`
School-specific enrollment timelines and deadlines.

#### `application_statuses`
User application tracking (requires email for now, user accounts later).

#### `school_events`
Open houses, tours, and information sessions.

#### `after_school_care`
BSO provider information linked to schools.

#### `special_needs_support`
Special education services and accessibility.

#### `academic_performance`
Historical performance data (5+ years).

#### `shareable_comparisons`
Temporary storage for shared comparison links.

---

## Sample Data

Generate sample data for testing:

```bash
cd backend
python -m app.sample_data_generator
```

This populates:
- Admission timelines for 50 schools
- School events (2-4 per school)
- BSO information for primary schools
- Special needs support data
- 5 years of performance history

---

## Future Enhancements

### Phase 1 (Q1 2025)
- [ ] Real NS API integration
- [ ] Real 9292 API integration
- [ ] PDF export for comparisons
- [ ] User authentication

### Phase 2 (Q2 2025)
- [ ] Email deadline reminders
- [ ] SMS notifications
- [ ] Advanced filtering UI
- [ ] Mobile app (React Native)

### Phase 3 (Q3 2025)
- [ ] School administrator portal
- [ ] Parent reviews and ratings
- [ ] Housing integration (Funda API)
- [ ] Neighborhood quality scores

---

## Support & Feedback

- **Issues**: [GitHub Issues](https://github.com/yourusername/dutch-school-finder/issues)
- **Email**: support@dutchschoolfinder.com
- **Documentation**: [docs.dutchschoolfinder.nl](https://docs.dutchschoolfinder.nl)

---

**Last Updated**: January 2025
**Version**: 2.0.0
