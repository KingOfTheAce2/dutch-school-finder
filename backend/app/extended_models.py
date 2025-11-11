"""
Extended Pydantic models for new features
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Transportation Models
class TransportationRouteResponse(BaseModel):
    """Transportation route information"""
    id: int
    school_id: int
    mode: str
    duration_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    transit_details: Optional[Dict[str, Any]] = None
    bus_route_name: Optional[str] = None
    bus_pickup_time: Optional[str] = None
    bus_pickup_location: Optional[str] = None
    from_address: Optional[str] = None

    class Config:
        from_attributes = True


class TransportationRequest(BaseModel):
    """Request for transportation calculation"""
    school_id: int
    from_address: str
    modes: List[str] = ["walking", "cycling", "public_transit", "driving"]


# Admission Timeline Models
class AdmissionTimelineResponse(BaseModel):
    """Admission timeline information"""
    id: int
    school_id: int
    academic_year: str
    enrollment_opens: Optional[datetime] = None
    enrollment_deadline: Optional[datetime] = None
    acceptance_notification_date: Optional[datetime] = None
    school_year_start: Optional[datetime] = None
    required_documents: Optional[List[str]] = None
    municipality: Optional[str] = None
    enrollment_system: Optional[str] = None
    enrollment_url: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ApplicationStatusRequest(BaseModel):
    """Create or update application status"""
    school_id: int
    user_email: str
    status: str
    waiting_list_position: Optional[int] = None
    notes: Optional[str] = None


class ApplicationStatusResponse(BaseModel):
    """Application status response"""
    id: int
    school_id: int
    user_email: str
    status: str
    applied_date: Optional[datetime] = None
    waiting_list_position: Optional[int] = None
    reminder_sent: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# School Events Models
class SchoolEventResponse(BaseModel):
    """School event information"""
    id: int
    school_id: int
    title: str
    event_type: Optional[str] = None
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    location: Optional[str] = None
    is_virtual: bool
    virtual_tour_url: Optional[str] = None
    requires_booking: bool
    booking_url: Optional[str] = None
    max_attendees: Optional[int] = None
    current_attendees: int
    language: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class SchoolEventCreate(BaseModel):
    """Create new school event"""
    school_id: int
    title: str
    event_type: Optional[str] = None
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    location: Optional[str] = None
    is_virtual: bool = False
    virtual_tour_url: Optional[str] = None
    requires_booking: bool = False
    booking_url: Optional[str] = None
    max_attendees: Optional[int] = None
    language: Optional[str] = None


# After-School Care (BSO) Models
class AfterSchoolCareResponse(BaseModel):
    """After-school care (BSO) information"""
    id: int
    school_id: int
    provider_name: str
    provider_website: Optional[str] = None
    provider_phone: Optional[str] = None
    provider_email: Optional[str] = None
    same_location_as_school: bool
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    operates_school_holidays: bool
    activities: Optional[List[str]] = None
    offers_homework_help: bool
    offers_sports: bool
    offers_arts_crafts: bool
    offers_outdoor_play: bool
    monthly_cost_euros: Optional[float] = None
    hourly_cost_euros: Optional[float] = None
    subsidy_eligible: bool
    capacity: Optional[int] = None
    current_occupancy: Optional[int] = None
    has_waiting_list: bool
    registration_url: Optional[str] = None
    registration_deadline: Optional[datetime] = None
    inspection_rating: Optional[str] = None
    staff_child_ratio: Optional[str] = None

    class Config:
        from_attributes = True


# Special Needs Support Models
class SpecialNeedsSupportResponse(BaseModel):
    """Special needs support information"""
    id: int
    school_id: int
    supports_dyslexia: bool
    supports_adhd: bool
    supports_autism: bool
    supports_gifted: bool
    supports_physical_disability: bool
    supports_visual_impairment: bool
    supports_hearing_impairment: bool
    offers_speech_therapy: bool
    offers_occupational_therapy: bool
    offers_special_education_classrooms: bool
    wheelchair_accessible: bool
    has_elevator: bool
    has_accessible_restrooms: bool
    special_education_staff_count: Optional[int] = None
    support_staff_ratio: Optional[str] = None
    programs_offered: Optional[List[str]] = None
    referral_process: Optional[str] = None
    funding_info: Optional[str] = None
    notes: Optional[str] = None
    parent_testimonials: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


# Academic Performance Models
class AcademicPerformanceResponse(BaseModel):
    """Historical academic performance data"""
    id: int
    school_id: int
    academic_year: str
    year_start: int
    cito_score: Optional[float] = None
    inspection_rating: Optional[str] = None
    inspection_score: Optional[float] = None
    student_count: Optional[int] = None
    teacher_count: Optional[int] = None
    teacher_turnover_rate: Optional[float] = None
    graduation_rate: Optional[float] = None
    university_acceptance_rate: Optional[float] = None
    year_over_year_change: Optional[float] = None
    data_source: Optional[str] = None

    class Config:
        from_attributes = True


class PerformanceTrend(BaseModel):
    """Performance trend analysis"""
    school_id: int
    school_name: str
    trend_direction: str  # "improving", "stable", "declining"
    years_of_data: int
    total_change: float
    average_annual_change: float
    badge: Optional[str] = None  # "rising_star", "consistent_excellence", etc.
    performance_history: List[AcademicPerformanceResponse]


# Shareable Comparison Models
class ShareableComparisonCreate(BaseModel):
    """Create a shareable comparison"""
    school_ids: List[int] = Field(..., min_items=2, max_items=5)
    filters_applied: Optional[Dict[str, Any]] = None


class ShareableComparisonResponse(BaseModel):
    """Shareable comparison response"""
    id: int
    share_id: str
    school_ids: List[int]
    filters_applied: Optional[Dict[str, Any]] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    view_count: int

    class Config:
        from_attributes = True


# Extended School Response
class ExtendedSchoolResponse(BaseModel):
    """Extended school information with all features"""
    # Basic school info (from original SchoolResponse)
    id: int
    name: str
    brin_code: Optional[str] = None
    city: str
    postal_code: Optional[str] = None
    address: Optional[str] = None
    school_type: Optional[str] = None
    education_structure: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    inspection_rating: Optional[str] = None
    inspection_score: Optional[float] = None
    cito_score: Optional[float] = None
    is_bilingual: bool
    is_international: bool
    offers_english: bool
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    denomination: Optional[str] = None
    student_count: Optional[int] = None
    description: Optional[str] = None

    # Extended features
    transportation: Optional[List[TransportationRouteResponse]] = None
    admission_timeline: Optional[AdmissionTimelineResponse] = None
    upcoming_events: Optional[List[SchoolEventResponse]] = None
    after_school_care: Optional[List[AfterSchoolCareResponse]] = None
    special_needs_support: Optional[SpecialNeedsSupportResponse] = None
    performance_history: Optional[List[AcademicPerformanceResponse]] = None
    performance_trend: Optional[str] = None  # "improving", "stable", "declining"

    class Config:
        from_attributes = True
