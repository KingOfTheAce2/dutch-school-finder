"""
Database models and configuration for Dutch School Finder
Uses SQLAlchemy for ORM and supports both SQLite (dev) and PostgreSQL (production)
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL - can be configured via environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./schools.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class School(Base):
    """School model representing educational institutions in the Netherlands"""
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)

    # Basic information
    name = Column(String, nullable=False, index=True)
    brin_code = Column(String, unique=True, index=True)  # Dutch school identifier
    city = Column(String, nullable=False, index=True)
    postal_code = Column(String)
    address = Column(String)

    # School type and level
    school_type = Column(String, index=True)  # Primary, Secondary, Special Education
    education_structure = Column(String)  # e.g., VMBO, HAVO, VWO for secondary

    # Location
    latitude = Column(Float)
    longitude = Column(Float)

    # Quality indicators
    inspection_rating = Column(String)  # Good, Satisfactory, Weak, Very Weak
    inspection_score = Column(Float)  # Numerical score (0-10)
    cito_score = Column(Float)  # Average CITO score for primary schools

    # Expat-friendly features
    is_bilingual = Column(Boolean, default=False)
    is_international = Column(Boolean, default=False)
    offers_english = Column(Boolean, default=False)

    # Additional information
    phone = Column(String)
    email = Column(String)
    website = Column(String)
    denomination = Column(String)  # Religious affiliation

    # Metadata
    student_count = Column(Integer)
    description = Column(Text)

    def __repr__(self):
        return f"<School(name={self.name}, city={self.city}, type={self.school_type})>"


def init_db():
    """Initialize database and create all tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
