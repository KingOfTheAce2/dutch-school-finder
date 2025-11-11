"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional


class SchoolBase(BaseModel):
    """Base school model with common fields"""
    name: str
    brin_code: Optional[str] = None
    city: str
    postal_code: Optional[str] = None
    address: Optional[str] = None
    school_type: Optional[str] = None
    education_structure: Optional[str] = None


class SchoolResponse(SchoolBase):
    """School response model for API endpoints"""
    id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    inspection_rating: Optional[str] = None
    inspection_score: Optional[float] = None
    cito_score: Optional[float] = None
    is_bilingual: bool = False
    is_international: bool = False
    offers_english: bool = False
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    denomination: Optional[str] = None
    student_count: Optional[int] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class SchoolSearchParams(BaseModel):
    """Parameters for school search"""
    city: Optional[str] = None
    school_type: Optional[str] = None
    min_rating: Optional[float] = None
    name: Optional[str] = None
    bilingual: Optional[bool] = None
    international: Optional[bool] = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
