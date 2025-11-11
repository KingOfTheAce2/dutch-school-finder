"""
CRUD (Create, Read, Update, Delete) operations for school data
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from .database import School
from .models import SchoolSearchParams, SchoolWithDistance
from .distance import haversine_distance, calculate_bounding_box, format_distance


def get_school_count(db: Session) -> int:
    """Get total number of schools in database"""
    return db.query(School).count()


def get_schools(db: Session, limit: int = 100, offset: int = 0) -> List[School]:
    """Get schools with pagination"""
    return db.query(School).offset(offset).limit(limit).all()


def get_school_by_id(db: Session, school_id: int) -> Optional[School]:
    """Get a single school by ID"""
    return db.query(School).filter(School.id == school_id).first()


def get_school_by_brin(db: Session, brin_code: str) -> Optional[School]:
    """Get a school by BRIN code"""
    return db.query(School).filter(School.brin_code == brin_code).first()


def get_schools_by_city(db: Session, city: str, limit: int = 100) -> List[School]:
    """Get schools in a specific city"""
    return db.query(School).filter(
        func.lower(School.city) == func.lower(city)
    ).limit(limit).all()


def get_schools_by_type(db: Session, school_type: str, limit: int = 100) -> List[School]:
    """Get schools of a specific type"""
    return db.query(School).filter(
        func.lower(School.school_type) == func.lower(school_type)
    ).limit(limit).all()


def get_all_cities(db: Session) -> List[str]:
    """Get list of all unique cities"""
    cities = db.query(School.city).distinct().order_by(School.city).all()
    return [city[0] for city in cities if city[0]]


def get_school_types(db: Session) -> List[str]:
    """Get list of all unique school types"""
    types = db.query(School.school_type).distinct().order_by(School.school_type).all()
    return [t[0] for t in types if t[0]]


def search_schools(db: Session, params: SchoolSearchParams) -> List[School]:
    """
    Search schools with multiple filters
    """
    query = db.query(School)

    # Filter by city
    if params.city:
        query = query.filter(func.lower(School.city).contains(func.lower(params.city)))

    # Filter by school type
    if params.school_type:
        query = query.filter(func.lower(School.school_type) == func.lower(params.school_type))

    # Filter by name
    if params.name:
        query = query.filter(func.lower(School.name).contains(func.lower(params.name)))

    # Filter by minimum rating
    if params.min_rating:
        query = query.filter(School.inspection_score >= params.min_rating)

    # Filter bilingual schools
    if params.bilingual:
        query = query.filter(School.is_bilingual == True)

    # Filter international schools
    if params.international:
        query = query.filter(School.is_international == True)

    # Apply pagination
    query = query.offset(params.offset).limit(params.limit)

    return query.all()


def create_school(db: Session, school_data: dict) -> School:
    """Create a new school record"""
    school = School(**school_data)
    db.add(school)
    db.commit()
    db.refresh(school)
    return school


def update_school(db: Session, school_id: int, school_data: dict) -> Optional[School]:
    """Update an existing school record"""
    school = get_school_by_id(db, school_id)
    if school:
        for key, value in school_data.items():
            setattr(school, key, value)
        db.commit()
        db.refresh(school)
    return school


def search_schools_by_proximity(
    db: Session,
    params: SchoolSearchParams,
    latitude: float,
    longitude: float,
    radius_km: float
) -> List[SchoolWithDistance]:
    """
    Search for schools within a radius of given coordinates

    Args:
        db: Database session
        params: Search parameters (filters)
        latitude: Center point latitude
        longitude: Center point longitude
        radius_km: Search radius in kilometers

    Returns:
        List of schools with distance information, sorted by distance
    """
    # Start with base query
    query = db.query(School)

    # Apply filters from params
    if params.school_type:
        query = query.filter(func.lower(School.school_type) == func.lower(params.school_type))

    if params.min_rating:
        query = query.filter(School.inspection_score >= params.min_rating)

    if params.bilingual:
        query = query.filter(School.is_bilingual == True)

    if params.international:
        query = query.filter(School.is_international == True)

    # Filter by bounding box for efficiency
    min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(latitude, longitude, radius_km)
    query = query.filter(
        School.latitude >= min_lat,
        School.latitude <= max_lat,
        School.longitude >= min_lon,
        School.longitude <= max_lon
    )

    # Filter out schools without coordinates
    query = query.filter(
        School.latitude.isnot(None),
        School.longitude.isnot(None)
    )

    # Get all matching schools
    schools = query.all()

    # Calculate exact distances and filter by radius
    schools_with_distance = []
    for school in schools:
        distance = haversine_distance(
            latitude, longitude,
            school.latitude, school.longitude
        )

        # Only include schools within radius
        if distance <= radius_km:
            # Convert SQLAlchemy model to dict and add distance
            school_dict = {
                "id": school.id,
                "name": school.name,
                "brin_code": school.brin_code,
                "city": school.city,
                "postal_code": school.postal_code,
                "address": school.address,
                "school_type": school.school_type,
                "education_structure": school.education_structure,
                "latitude": school.latitude,
                "longitude": school.longitude,
                "inspection_rating": school.inspection_rating,
                "inspection_score": school.inspection_score,
                "cito_score": school.cito_score,
                "is_bilingual": school.is_bilingual,
                "is_international": school.is_international,
                "offers_english": school.offers_english,
                "phone": school.phone,
                "email": school.email,
                "website": school.website,
                "denomination": school.denomination,
                "student_count": school.student_count,
                "description": school.description,
                "distance_km": round(distance, 2),
                "distance_formatted": format_distance(distance)
            }

            schools_with_distance.append(SchoolWithDistance(**school_dict))

    # Sort by distance
    schools_with_distance.sort(key=lambda s: s.distance_km)

    # Apply limit
    return schools_with_distance[:params.limit]


def delete_school(db: Session, school_id: int) -> bool:
    """Delete a school record"""
    school = get_school_by_id(db, school_id)
    if school:
        db.delete(school)
        db.commit()
        return True
    return False
