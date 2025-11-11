"""
Dutch School Finder API
Main FastAPI application for serving school data to expat families in the Netherlands
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging

from .database import init_db, get_db
from .data_fetcher import fetch_and_store_schools, refresh_school_data
from .models import SchoolResponse, SchoolSearchParams
from .crud import (
    search_schools,
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
    db = next(get_db())
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
def get_school(school_id: int):
    """Get a single school by ID"""
    db = next(get_db())
    try:
        school = get_school_by_id(db, school_id)
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
        return school
    finally:
        db.close()


@app.get("/schools/search", response_model=List[SchoolResponse])
def search_schools_endpoint(
    city: Optional[str] = Query(None, description="Filter by city name"),
    school_type: Optional[str] = Query(None, description="Filter by school type"),
    min_rating: Optional[float] = Query(None, ge=0, le=10, description="Minimum quality rating"),
    name: Optional[str] = Query(None, description="Search by school name"),
    bilingual: Optional[bool] = Query(None, description="Filter bilingual schools"),
    international: Optional[bool] = Query(None, description="Filter international schools"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
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
    db = next(get_db())
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
    finally:
        db.close()


@app.get("/cities", response_model=List[str])
def get_cities():
    """Get a list of all cities with schools"""
    db = next(get_db())
    try:
        cities = get_all_cities(db)
        return cities
    finally:
        db.close()


@app.get("/types", response_model=List[str])
def get_types():
    """Get a list of all school types"""
    db = next(get_db())
    try:
        types = get_school_types(db)
        return types
    finally:
        db.close()


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
