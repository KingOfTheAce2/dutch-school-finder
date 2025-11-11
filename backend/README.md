# Dutch School Finder - Backend API

FastAPI-based backend for the Dutch School Finder application.

## Features

- RESTful API for school data
- Search and filter schools by city, type, quality rating
- Support for bilingual and international school filtering
- SQLite (development) and PostgreSQL (production) support
- Automatic data fetching and caching
- English translations of Dutch education terminology

## Setup

### Prerequisites

- Python 3.9+
- pip or poetry

### Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Running the API

Development mode with auto-reload:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use Python directly:
```bash
python -m app.main
```

The API will be available at http://localhost:8000

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### Schools

- `GET /schools` - List all schools (with pagination)
- `GET /schools/{id}` - Get a specific school by ID
- `GET /schools/search` - Search schools with filters
  - Query parameters: `city`, `school_type`, `name`, `min_rating`, `bilingual`, `international`

### Metadata

- `GET /cities` - List all cities with schools
- `GET /types` - List all school types

### Admin

- `POST /admin/refresh-data` - Refresh school data from sources

## Database Schema

### School Model

```python
- id: Integer (Primary Key)
- name: String
- brin_code: String (Unique, Dutch school identifier)
- city: String
- postal_code: String
- address: String
- school_type: String (Primary, Secondary, Special Education)
- education_structure: String (VMBO, HAVO, VWO, etc.)
- latitude: Float
- longitude: Float
- inspection_rating: String
- inspection_score: Float (0-10)
- cito_score: Float (for primary schools)
- is_bilingual: Boolean
- is_international: Boolean
- offers_english: Boolean
- phone: String
- email: String
- website: String
- denomination: String
- student_count: Integer
- description: Text
```

## Data Sources

The API integrates (or can integrate) with:

1. **DUO Open Data** - Official Dutch education data
   - URL: https://opendata.duo.nl/
   - Contains: School registrations, student counts, basic info

2. **Scholen op de Kaart** - School quality and inspection data
   - URL: https://scholenopdekaart.nl/
   - Contains: Inspection ratings, quality scores

3. **Sample Data** - For demonstration, the API generates realistic sample data

## Development

### Running Tests

```bash
pytest
```

### Code Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application and routes
│   ├── database.py      # Database models and connection
│   ├── models.py        # Pydantic models for validation
│   ├── crud.py          # Database operations
│   ├── data_fetcher.py  # Data fetching and processing
│   └── translations.py  # Dutch-English translations
├── requirements.txt
├── .env.example
└── README.md
```

## Deployment

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Heroku

```bash
# Procfile
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables for Production

Set these in your production environment:
- `DATABASE_URL` - PostgreSQL connection string
- `CORS_ORIGINS` - Allowed frontend origins
- Any API keys for external services

## Future Enhancements

- [ ] Real-time data sync with DUO API
- [ ] Geocoding service integration
- [ ] Advanced filtering (distance from address, rating ranges)
- [ ] User favorites and saved searches
- [ ] Email notifications for new schools
- [ ] Integration with housing APIs (Funda, Pararius)
