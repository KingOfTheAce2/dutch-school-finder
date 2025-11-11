"""
CRUD operations for extended features
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import List, Optional
from datetime import datetime, timedelta
import secrets
import json

from .database import (
    TransportationRoute,
    AdmissionTimeline,
    ApplicationStatus,
    SchoolEvent,
    AfterSchoolCare,
    SpecialNeedsSupport,
    AcademicPerformance,
    ShareableComparison,
    School
)
from .extended_models import (
    TransportationRouteResponse,
    AdmissionTimelineResponse,
    ApplicationStatusRequest,
    ApplicationStatusResponse,
    SchoolEventResponse,
    SchoolEventCreate,
    AfterSchoolCareResponse,
    SpecialNeedsSupportResponse,
    AcademicPerformanceResponse,
    PerformanceTrend,
    ShareableComparisonCreate,
    ShareableComparisonResponse
)


# Transportation CRUD
def get_transportation_routes(
    db: Session,
    school_id: int,
    from_address: Optional[str] = None
) -> List[TransportationRoute]:
    """Get transportation routes for a school"""
    query = db.query(TransportationRoute).filter(
        TransportationRoute.school_id == school_id
    )

    if from_address:
        query = query.filter(TransportationRoute.from_address == from_address)

    return query.all()


def create_transportation_route(
    db: Session,
    route_data: dict
) -> TransportationRoute:
    """Create a new transportation route"""
    route = TransportationRoute(**route_data)
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


def delete_old_cached_routes(db: Session, days_old: int = 7):
    """Delete transportation routes older than specified days"""
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    db.query(TransportationRoute).filter(
        TransportationRoute.cached_at < cutoff_date
    ).delete()
    db.commit()


# Admission Timeline CRUD
def get_admission_timeline(
    db: Session,
    school_id: int,
    academic_year: Optional[str] = None
) -> Optional[AdmissionTimeline]:
    """Get admission timeline for a school"""
    query = db.query(AdmissionTimeline).filter(
        AdmissionTimeline.school_id == school_id
    )

    if academic_year:
        query = query.filter(AdmissionTimeline.academic_year == academic_year)
    else:
        # Get the most recent year
        query = query.order_by(desc(AdmissionTimeline.academic_year))

    return query.first()


def get_upcoming_deadlines(
    db: Session,
    days_ahead: int = 30,
    municipality: Optional[str] = None
) -> List[AdmissionTimeline]:
    """Get upcoming enrollment deadlines"""
    cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)

    query = db.query(AdmissionTimeline).filter(
        and_(
            AdmissionTimeline.enrollment_deadline.isnot(None),
            AdmissionTimeline.enrollment_deadline <= cutoff_date,
            AdmissionTimeline.enrollment_deadline >= datetime.utcnow()
        )
    )

    if municipality:
        query = query.filter(AdmissionTimeline.municipality == municipality)

    return query.order_by(asc(AdmissionTimeline.enrollment_deadline)).all()


def create_admission_timeline(
    db: Session,
    timeline_data: dict
) -> AdmissionTimeline:
    """Create admission timeline"""
    timeline = AdmissionTimeline(**timeline_data)
    db.add(timeline)
    db.commit()
    db.refresh(timeline)
    return timeline


# Application Status CRUD
def get_application_status(
    db: Session,
    user_email: str,
    school_id: Optional[int] = None
) -> List[ApplicationStatus]:
    """Get application statuses for a user"""
    query = db.query(ApplicationStatus).filter(
        ApplicationStatus.user_email == user_email
    )

    if school_id:
        query = query.filter(ApplicationStatus.school_id == school_id)

    return query.all()


def create_or_update_application_status(
    db: Session,
    status_data: ApplicationStatusRequest
) -> ApplicationStatus:
    """Create or update application status"""
    # Check if exists
    existing = db.query(ApplicationStatus).filter(
        and_(
            ApplicationStatus.user_email == status_data.user_email,
            ApplicationStatus.school_id == status_data.school_id
        )
    ).first()

    if existing:
        # Update
        existing.status = status_data.status
        existing.waiting_list_position = status_data.waiting_list_position
        existing.notes = status_data.notes
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        new_status = ApplicationStatus(
            school_id=status_data.school_id,
            user_email=status_data.user_email,
            status=status_data.status,
            applied_date=datetime.utcnow(),
            waiting_list_position=status_data.waiting_list_position,
            notes=status_data.notes
        )
        db.add(new_status)
        db.commit()
        db.refresh(new_status)
        return new_status


# School Events CRUD
def get_school_events(
    db: Session,
    school_id: Optional[int] = None,
    event_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    city: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 100
) -> List[SchoolEvent]:
    """Get school events with filters"""
    query = db.query(SchoolEvent).filter(SchoolEvent.is_active == True)

    if school_id:
        query = query.filter(SchoolEvent.school_id == school_id)

    if event_type:
        query = query.filter(SchoolEvent.event_type == event_type)

    if language:
        query = query.filter(
            or_(
                SchoolEvent.language == language,
                SchoolEvent.language == "Both"
            )
        )

    if start_date:
        query = query.filter(SchoolEvent.start_datetime >= start_date)
    else:
        # Default: only future events
        query = query.filter(SchoolEvent.start_datetime >= datetime.utcnow())

    if end_date:
        query = query.filter(SchoolEvent.start_datetime <= end_date)

    # Filter by city if provided
    if city:
        query = query.join(School).filter(School.city == city)

    return query.order_by(asc(SchoolEvent.start_datetime)).limit(limit).all()


def create_school_event(
    db: Session,
    event_data: SchoolEventCreate
) -> SchoolEvent:
    """Create a new school event"""
    event = SchoolEvent(**event_data.dict())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


# After-School Care CRUD
def get_after_school_care(
    db: Session,
    school_id: int
) -> List[AfterSchoolCare]:
    """Get after-school care options for a school"""
    return db.query(AfterSchoolCare).filter(
        AfterSchoolCare.school_id == school_id
    ).all()


def search_after_school_care(
    db: Session,
    max_cost: Optional[float] = None,
    offers_homework_help: Optional[bool] = None,
    subsidy_eligible: Optional[bool] = None,
    no_waiting_list: Optional[bool] = None
) -> List[AfterSchoolCare]:
    """Search after-school care with filters"""
    query = db.query(AfterSchoolCare)

    if max_cost:
        query = query.filter(
            or_(
                AfterSchoolCare.monthly_cost_euros <= max_cost,
                AfterSchoolCare.monthly_cost_euros.is_(None)
            )
        )

    if offers_homework_help:
        query = query.filter(AfterSchoolCare.offers_homework_help == True)

    if subsidy_eligible:
        query = query.filter(AfterSchoolCare.subsidy_eligible == True)

    if no_waiting_list:
        query = query.filter(AfterSchoolCare.has_waiting_list == False)

    return query.all()


def create_after_school_care(
    db: Session,
    bso_data: dict
) -> AfterSchoolCare:
    """Create after-school care entry"""
    bso = AfterSchoolCare(**bso_data)
    db.add(bso)
    db.commit()
    db.refresh(bso)
    return bso


# Special Needs Support CRUD
def get_special_needs_support(
    db: Session,
    school_id: int
) -> Optional[SpecialNeedsSupport]:
    """Get special needs support info for a school"""
    return db.query(SpecialNeedsSupport).filter(
        SpecialNeedsSupport.school_id == school_id
    ).first()


def search_schools_with_special_needs(
    db: Session,
    dyslexia: bool = False,
    adhd: bool = False,
    autism: bool = False,
    gifted: bool = False,
    wheelchair_accessible: bool = False,
    offers_speech_therapy: bool = False,
    city: Optional[str] = None
) -> List[int]:
    """
    Search schools that offer specific special needs support
    Returns list of school IDs
    """
    query = db.query(SpecialNeedsSupport.school_id)

    filters = []
    if dyslexia:
        filters.append(SpecialNeedsSupport.supports_dyslexia == True)
    if adhd:
        filters.append(SpecialNeedsSupport.supports_adhd == True)
    if autism:
        filters.append(SpecialNeedsSupport.supports_autism == True)
    if gifted:
        filters.append(SpecialNeedsSupport.supports_gifted == True)
    if wheelchair_accessible:
        filters.append(SpecialNeedsSupport.wheelchair_accessible == True)
    if offers_speech_therapy:
        filters.append(SpecialNeedsSupport.offers_speech_therapy == True)

    if filters:
        query = query.filter(or_(*filters))

    # Filter by city if provided
    if city:
        query = query.join(School).filter(School.city == city)

    return [result[0] for result in query.all()]


def create_special_needs_support(
    db: Session,
    support_data: dict
) -> SpecialNeedsSupport:
    """Create special needs support entry"""
    support = SpecialNeedsSupport(**support_data)
    db.add(support)
    db.commit()
    db.refresh(support)
    return support


# Academic Performance CRUD
def get_performance_history(
    db: Session,
    school_id: int,
    years: int = 5
) -> List[AcademicPerformance]:
    """Get performance history for a school"""
    return db.query(AcademicPerformance).filter(
        AcademicPerformance.school_id == school_id
    ).order_by(desc(AcademicPerformance.year_start)).limit(years).all()


def calculate_performance_trend(
    db: Session,
    school_id: int
) -> Optional[PerformanceTrend]:
    """Calculate performance trend for a school"""
    history = get_performance_history(db, school_id, years=5)

    if len(history) < 2:
        return None

    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        return None

    # Calculate trend
    history_sorted = sorted(history, key=lambda x: x.year_start)
    oldest = history_sorted[0]
    newest = history_sorted[-1]

    # Use CITO score for trend if available
    if oldest.cito_score and newest.cito_score:
        total_change = newest.cito_score - oldest.cito_score
        years_span = newest.year_start - oldest.year_start
        avg_annual_change = total_change / years_span if years_span > 0 else 0

        # Determine trend direction
        if total_change > 5:
            trend_direction = "improving"
            badge = "rising_star" if total_change > 10 else None
        elif total_change < -5:
            trend_direction = "declining"
            badge = "needs_attention"
        else:
            trend_direction = "stable"
            # Check if consistently high
            if all(h.cito_score and h.cito_score >= 540 for h in history if h.cito_score):
                badge = "consistent_excellence"
            else:
                badge = None

        return PerformanceTrend(
            school_id=school_id,
            school_name=school.name,
            trend_direction=trend_direction,
            years_of_data=len(history),
            total_change=total_change,
            average_annual_change=avg_annual_change,
            badge=badge,
            performance_history=[AcademicPerformanceResponse.from_orm(h) for h in history_sorted]
        )

    return None


def create_performance_record(
    db: Session,
    performance_data: dict
) -> AcademicPerformance:
    """Create performance record"""
    performance = AcademicPerformance(**performance_data)
    db.add(performance)
    db.commit()
    db.refresh(performance)
    return performance


# Shareable Comparison CRUD
def create_shareable_comparison(
    db: Session,
    comparison_data: ShareableComparisonCreate
) -> ShareableComparison:
    """Create a shareable comparison link"""
    # Generate unique share ID
    share_id = secrets.token_urlsafe(16)

    # Set expiration (30 days)
    expires_at = datetime.utcnow() + timedelta(days=30)

    comparison = ShareableComparison(
        share_id=share_id,
        school_ids=comparison_data.school_ids,
        filters_applied=comparison_data.filters_applied or {},
        expires_at=expires_at
    )

    db.add(comparison)
    db.commit()
    db.refresh(comparison)
    return comparison


def get_shareable_comparison(
    db: Session,
    share_id: str
) -> Optional[ShareableComparison]:
    """Get a shareable comparison by ID"""
    comparison = db.query(ShareableComparison).filter(
        ShareableComparison.share_id == share_id
    ).first()

    if not comparison:
        return None

    # Check if expired
    if comparison.expires_at and comparison.expires_at < datetime.utcnow():
        return None

    # Increment view count
    comparison.view_count += 1
    db.commit()

    return comparison


def cleanup_expired_comparisons(db: Session):
    """Delete expired shareable comparisons"""
    db.query(ShareableComparison).filter(
        ShareableComparison.expires_at < datetime.utcnow()
    ).delete()
    db.commit()
