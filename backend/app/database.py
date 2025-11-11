"""
Database models and configuration for Dutch School Finder
Uses SQLAlchemy for ORM and supports both SQLite (dev) and PostgreSQL (production)
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
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


class TransportationRoute(Base):
    """Transportation options and travel times to schools"""
    __tablename__ = "transportation_routes"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)

    # Travel information
    mode = Column(String, nullable=False)  # walking, cycling, public_transit, driving, school_bus
    duration_minutes = Column(Integer)  # Estimated travel time
    distance_km = Column(Float)

    # Public transit specific
    transit_details = Column(JSON)  # Lines, transfers, schedules

    # School bus specific
    bus_route_name = Column(String)
    bus_pickup_time = Column(String)
    bus_pickup_location = Column(String)

    # Caching
    from_address = Column(String)  # Address this route is calculated from
    cached_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    school = relationship("School", backref="transportation_routes")


class AdmissionTimeline(Base):
    """Application timeline and deadlines for schools"""
    __tablename__ = "admission_timelines"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)

    # Timeline information
    academic_year = Column(String, nullable=False)  # e.g., "2024-2025"
    enrollment_opens = Column(DateTime)
    enrollment_deadline = Column(DateTime)
    acceptance_notification_date = Column(DateTime)
    school_year_start = Column(DateTime)

    # Requirements
    required_documents = Column(JSON)  # List of required documents

    # Municipality-specific
    municipality = Column(String)
    enrollment_system = Column(String)  # e.g., "Prewonen", "Schoolwijzer"
    enrollment_url = Column(String)

    # Additional info
    notes = Column(Text)

    # Relationship
    school = relationship("School", backref="admission_timelines")


class ApplicationStatus(Base):
    """Track application status for families (future user accounts feature)"""
    __tablename__ = "application_statuses"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)

    # User tracking (for future implementation)
    user_email = Column(String)  # Temporary identifier

    # Status
    status = Column(String)  # "interested", "applied", "waiting", "accepted", "enrolled", "declined"
    applied_date = Column(DateTime)
    waiting_list_position = Column(Integer)

    # Reminders
    reminder_sent = Column(Boolean, default=False)

    # Notes
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    school = relationship("School", backref="application_statuses")


class SchoolEvent(Base):
    """School events, open houses, and information evenings"""
    __tablename__ = "school_events"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)

    # Event details
    title = Column(String, nullable=False)
    event_type = Column(String)  # "open_house", "info_evening", "tour", "application_period", "other"
    description = Column(Text)

    # Date and time
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime)

    # Location
    location = Column(String)
    is_virtual = Column(Boolean, default=False)
    virtual_tour_url = Column(String)

    # Registration
    requires_booking = Column(Boolean, default=False)
    booking_url = Column(String)
    max_attendees = Column(Integer)
    current_attendees = Column(Integer, default=0)

    # Language
    language = Column(String)  # "Dutch", "English", "Both"

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationship
    school = relationship("School", backref="events")


class AfterSchoolCare(Base):
    """BSO (Buitenschoolse Opvang) - After-school care information"""
    __tablename__ = "after_school_care"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)

    # Provider information
    provider_name = Column(String, nullable=False)
    provider_website = Column(String)
    provider_phone = Column(String)
    provider_email = Column(String)

    # Location
    same_location_as_school = Column(Boolean, default=True)
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    # Operating hours
    opening_time = Column(String)  # e.g., "15:00"
    closing_time = Column(String)  # e.g., "18:30"
    operates_school_holidays = Column(Boolean, default=False)

    # Services and activities
    activities = Column(JSON)  # List of activities offered
    offers_homework_help = Column(Boolean, default=False)
    offers_sports = Column(Boolean, default=False)
    offers_arts_crafts = Column(Boolean, default=False)
    offers_outdoor_play = Column(Boolean, default=False)

    # Costs and capacity
    monthly_cost_euros = Column(Float)
    hourly_cost_euros = Column(Float)
    subsidy_eligible = Column(Boolean, default=True)
    capacity = Column(Integer)
    current_occupancy = Column(Integer)
    has_waiting_list = Column(Boolean, default=False)

    # Registration
    registration_url = Column(String)
    registration_deadline = Column(DateTime)

    # Quality
    inspection_rating = Column(String)
    staff_child_ratio = Column(String)  # e.g., "1:8"

    # Relationship
    school = relationship("School", backref="after_school_care")


class SpecialNeedsSupport(Base):
    """Special education needs and support services"""
    __tablename__ = "special_needs_support"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)

    # Support types
    supports_dyslexia = Column(Boolean, default=False)
    supports_adhd = Column(Boolean, default=False)
    supports_autism = Column(Boolean, default=False)
    supports_gifted = Column(Boolean, default=False)
    supports_physical_disability = Column(Boolean, default=False)
    supports_visual_impairment = Column(Boolean, default=False)
    supports_hearing_impairment = Column(Boolean, default=False)

    # Specialized services
    offers_speech_therapy = Column(Boolean, default=False)
    offers_occupational_therapy = Column(Boolean, default=False)
    offers_special_education_classrooms = Column(Boolean, default=False)

    # Accessibility
    wheelchair_accessible = Column(Boolean, default=False)
    has_elevator = Column(Boolean, default=False)
    has_accessible_restrooms = Column(Boolean, default=False)

    # Staff and resources
    special_education_staff_count = Column(Integer)
    support_staff_ratio = Column(String)  # e.g., "1 per 50 students"

    # Programs
    programs_offered = Column(JSON)  # List of specialized programs

    # Referral and funding
    referral_process = Column(Text)
    funding_info = Column(Text)

    # Additional information
    notes = Column(Text)
    parent_testimonials = Column(JSON)  # Array of testimonial objects

    # Relationship
    school = relationship("School", backref="special_needs_support")


class AcademicPerformance(Base):
    """Historical academic performance data for trend analysis"""
    __tablename__ = "academic_performance"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)

    # Academic year
    academic_year = Column(String, nullable=False)  # e.g., "2023-2024"
    year_start = Column(Integer, nullable=False)  # e.g., 2023

    # Performance metrics
    cito_score = Column(Float)
    inspection_rating = Column(String)
    inspection_score = Column(Float)

    # Enrollment
    student_count = Column(Integer)
    teacher_count = Column(Integer)
    teacher_turnover_rate = Column(Float)  # Percentage

    # Graduation/progression (for secondary schools)
    graduation_rate = Column(Float)  # Percentage
    university_acceptance_rate = Column(Float)  # Percentage

    # Trends
    year_over_year_change = Column(Float)  # Change from previous year

    # Data source
    data_source = Column(String)  # "DUO", "Inspectorate", "Manual"

    # Relationship
    school = relationship("School", backref="performance_history")


class ShareableComparison(Base):
    """Store shareable school comparisons"""
    __tablename__ = "shareable_comparisons"

    id = Column(Integer, primary_key=True, index=True)

    # Unique identifier for sharing
    share_id = Column(String, unique=True, nullable=False, index=True)

    # Comparison data
    school_ids = Column(JSON, nullable=False)  # Array of school IDs
    filters_applied = Column(JSON)  # Filters used in comparison

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Auto-expire after 30 days
    view_count = Column(Integer, default=0)

    # Optional user info (for future)
    created_by_email = Column(String)


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
