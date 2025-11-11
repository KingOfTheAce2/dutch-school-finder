"""
Dutch School Finder API
Main FastAPI application for serving school data to expat families in the Netherlands
"""
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging
from sqlalchemy.orm import Session

from .database import init_db, get_db
from .data_fetcher import fetch_and_store_schools, refresh_school_data
from .models import SchoolResponse, SchoolSearchParams, SchoolWithDistance
from .geocoding import geocode_address, geocode_city
from .distance import haversine_distance
from .crud import (
    search_schools,
    search_schools_by_proximity,
    get_school_by_id,
    get_schools_by_city,
    get_schools_by_type,
    get_all_cities,
    get_school_types
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dutch School Finder API",
    description="API for finding and comparing schools in the Netherlands",
    version="1.0.0"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database and load initial data"""
    logger.info("Starting Dutch School Finder API...")
    init_db()

    # Check if we need to load initial data
    db = next(get_db())
    try:
        from .crud import get_school_count
        count = get_school_count(db)
        if count == 0:
            logger.info("No schools in database, fetching initial data...")
            await fetch_and_store_schools()
        else:
            logger.info(f"Database already contains {count} schools")
    finally:
        db.close()


@app.get("/")
def read_root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Dutch School Finder API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "schools": "/schools",
            "search": "/schools/search",
            "cities": "/cities",
            "types": "/types"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "dutch-school-finder"}


@app.get("/schools", response_model=List[SchoolResponse])
def get_schools(
    limit: int = Query(50, ge=1, le=500, description="Number of schools to return"),
    offset: int = Query(0, ge=0, description="Number of schools to skip"),
    db: Session = Depends(get_db)
):
    """Get a list of schools with pagination"""
    try:
        from .crud import get_schools as get_schools_db
        schools = get_schools_db(db, limit=limit, offset=offset)
        return schools
    except Exception as e:
        logger.error(f"Error fetching schools: {e}")
        raise HTTPException(status_code=500, detail="Error fetching schools")


@app.get("/schools/{school_id}", response_model=SchoolResponse)
def get_school(school_id: int, db: Session = Depends(get_db)):
    """Get a single school by ID"""
    school = get_school_by_id(db, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school


@app.get("/schools/search", response_model=List[SchoolResponse])
def search_schools_endpoint(
    city: Optional[str] = Query(None, description="Filter by city name"),
    school_type: Optional[str] = Query(None, description="Filter by school type"),
    min_rating: Optional[float] = Query(None, ge=0, le=10, description="Minimum quality rating"),
    name: Optional[str] = Query(None, description="Search by school name"),
    bilingual: Optional[bool] = Query(None, description="Filter bilingual schools"),
    international: Optional[bool] = Query(None, description="Filter international schools"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Search schools with multiple filters

    - **city**: Filter by city name (case-insensitive)
    - **school_type**: Filter by type (primary, secondary, special education)
    - **min_rating**: Minimum inspection rating
    - **name**: Search by school name (partial match)
    - **bilingual**: Show only bilingual schools
    - **international**: Show only international schools
    """
    try:
        params = SchoolSearchParams(
            city=city,
            school_type=school_type,
            min_rating=min_rating,
            name=name,
            bilingual=bilingual,
            international=international,
            limit=limit,
            offset=offset
        )
        schools = search_schools(db, params)
        return schools
    except Exception as e:
        logger.error(f"Error searching schools: {e}")
        raise HTTPException(status_code=500, detail="Error searching schools")


@app.get("/cities", response_model=List[str])
def get_cities(db: Session = Depends(get_db)):
    """Get a list of all cities with schools"""
    cities = get_all_cities(db)
    return cities


@app.get("/types", response_model=List[str])
def get_types(db: Session = Depends(get_db)):
    """Get a list of all school types"""
    types = get_school_types(db)
    return types


@app.get("/schools/nearby", response_model=List[SchoolWithDistance])
def get_nearby_schools(
    address: str = Query(..., description="Address to search from (e.g., 'Dam 1, Amsterdam')"),
    radius_km: float = Query(5.0, ge=0.1, le=50.0, description="Search radius in kilometers"),
    school_type: Optional[str] = Query(None, description="Filter by school type"),
    min_rating: Optional[float] = Query(None, ge=0, le=10, description="Minimum quality rating"),
    bilingual: Optional[bool] = Query(None, description="Filter bilingual schools"),
    international: Optional[bool] = Query(None, description="Filter international schools"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Find schools near a specific address

    This endpoint:
    1. Geocodes the provided address
    2. Finds schools within the specified radius
    3. Calculates distances
    4. Returns schools sorted by distance

    Example: /schools/nearby?address=Dam 1, Amsterdam&radius_km=5&school_type=Primary
    """
    try:
        # Try to geocode the full address
        logger.info(f"Geocoding address: {address}")

        # Parse address (try to extract city if possible)
        parts = address.split(',')
        if len(parts) >= 2:
            street = parts[0].strip()
            city = parts[1].strip()
            coords = geocode_address(street, city)
        else:
            # Try geocoding as-is
            coords = geocode_city(address)

        if not coords:
            raise HTTPException(
                status_code=404,
                detail=f"Could not geocode address: '{address}'. Please try a more specific address like 'Dam 1, Amsterdam'"
            )

        lat, lon = coords
        logger.info(f"Geocoded to: ({lat}, {lon})")

        # Search for nearby schools
        params = SchoolSearchParams(
            school_type=school_type,
            min_rating=min_rating,
            bilingual=bilingual,
            international=international,
            limit=limit
        )

        schools = search_schools_by_proximity(
            db, params, lat, lon, radius_km
        )

        return schools

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in nearby search: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching nearby schools: {str(e)}")


@app.get("/geocode")
def geocode_endpoint(
    address: str = Query(..., description="Address to geocode"),
):
    """
    Geocode an address to coordinates
    Useful for testing and debugging

    Example: /geocode?address=Dam 1, Amsterdam
    """
    try:
        # Try to parse city from address
        parts = address.split(',')
        if len(parts) >= 2:
            street = parts[0].strip()
            city = parts[1].strip()
            coords = geocode_address(street, city)
        else:
            coords = geocode_city(address)

        if not coords:
            raise HTTPException(status_code=404, detail=f"Could not geocode address: '{address}'")

        lat, lon = coords
        return {
            "address": address,
            "latitude": lat,
            "longitude": lon,
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        raise HTTPException(status_code=500, detail=f"Geocoding error: {str(e)}")


@app.post("/admin/refresh-data")
async def refresh_data():
    """
    Admin endpoint to refresh school data from DUO
    (In production, this should be protected with authentication)
    """
    try:
        result = await refresh_school_data()
        return {"status": "success", "message": "School data refreshed", "details": result}
    except Exception as e:
        logger.error(f"Error refreshing data: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing data: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
