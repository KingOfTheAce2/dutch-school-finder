"""
Unified education institution model supporting:
- Childcare (0-4 years)
- Primary schools (4-12 years)
- Secondary schools (12-18 years)
- MBO (vocational education)
- HBO (universities of applied sciences)
- Universities (research universities)
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, JSON, DateTime
from datetime import datetime
from .database import Base


class EducationInstitution(Base):
    """
    Unified table for all education types
    Replaces 'School' to support childcare, MBO, HBO, universities
    """
    __tablename__ = "education_institutions"

    id = Column(Integer, primary_key=True, index=True)

    # Type (required)
    institution_type = Column(String, nullable=False, index=True)
    # Values: 'childcare', 'primary', 'secondary', 'mbo', 'hbo', 'university'

    # Basic Info (universal)
    name = Column(String, nullable=False, index=True)
    city = Column(String, nullable=False, index=True)
    address = Column(String)
    postal_code = Column(String)
    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)

    # Contact (universal)
    phone = Column(String)
    email = Column(String)
    website = Column(String)

    # Quality (universal)
    rating = Column(Float)  # 0-10 scale
    rating_source = Column(String)  # 'Inspectorate', 'GGD', etc.
    rating_label = Column(String)  # 'Excellent', 'Good', 'Satisfactory'

    # Language Support (universal - important for expats)
    is_bilingual = Column(Boolean, default=False)
    is_international = Column(Boolean, default=False)
    offers_english = Column(Boolean, default=False)

    # Type-specific data (JSON for flexibility)
    details = Column(JSON)
    """
    For childcare: {
      "lrk_number": "...",
      "capacity": 50,
      "age_group": "0-4",
      "type": "dagopvang" | "BSO" | "gastouderopvang",
      "owner": "Organization name",
      "registration_date": "2020-01-01"
    }

    For primary/secondary schools: {
      "brin_code": "...",
      "school_type": "Primary" | "Secondary",
      "education_structure": "VMBO" | "HAVO" | "VWO",
      "cito_score": 540,
      "denomination": "Catholic" | "Protestant" | "Public",
      "student_count": 450
    }

    For MBO: {
      "institution_code": "...",
      "programs": ["ICT", "Healthcare", "Business"],
      "levels": [1, 2, 3, 4],
      "student_count": 5000
    }

    For HBO/University: {
      "institution_code": "...",
      "programs": ["Computer Science", "Engineering"],
      "english_programs": ["Data Science", "AI"],
      "student_count": 25000,
      "international_students": 5000
    }
    """

    # Additional information
    description = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EducationInstitution(type={self.institution_type}, name={self.name}, city={self.city})>"


# Institution type constants
class InstitutionType:
    CHILDCARE = "childcare"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MBO = "mbo"
    HBO = "hbo"
    UNIVERSITY = "university"

    @classmethod
    def all(cls):
        return [cls.CHILDCARE, cls.PRIMARY, cls.SECONDARY, cls.MBO, cls.HBO, cls.UNIVERSITY]

    @classmethod
    def validate(cls, type_value: str) -> bool:
        return type_value in cls.all()
