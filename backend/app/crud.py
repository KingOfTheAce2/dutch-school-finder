"""
CRUD (Create, Read, Update, Delete) operations for school data
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from .database import School
from .models import SchoolSearchParams


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


def delete_school(db: Session, school_id: int) -> bool:
    """Delete a school record"""
    school = get_school_by_id(db, school_id)
    if school:
        db.delete(school)
        db.commit()
        return True
    return False
