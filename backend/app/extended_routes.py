"""
Extended API routes for new features
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from .database import get_db, School
from .extended_models import (
    TransportationRouteResponse,
    TransportationRequest,
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
    ShareableComparisonResponse,
    ExtendedSchoolResponse
)
from .extended_crud import (
    get_transportation_routes,
    create_transportation_route,
    get_admission_timeline,
    get_upcoming_deadlines,
    get_application_status,
    create_or_update_application_status,
    get_school_events,
    create_school_event,
    get_after_school_care,
    search_after_school_care,
    get_special_needs_support,
    search_schools_with_special_needs,
    get_performance_history,
    calculate_performance_trend,
    create_shareable_comparison,
    get_shareable_comparison,
    cleanup_expired_comparisons
)
from .transportation_service import get_transportation_for_school
from .geocoding import geocode_address, geocode_city
from .models import SchoolResponse
from .crud import get_school_by_id, search_schools

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# TRANSPORTATION ROUTES
# ============================================================================

@router.get("/transportation/{school_id}", response_model=List[TransportationRouteResponse])
async def get_school_transportation(
    school_id: int,
    from_address: str = Query(..., description="Address to calculate routes from"),
    db: Session = Depends(get_db)
):
    """
    Get transportation options to a school from a specific address

    Calculates and returns:
    - Walking time and distance
    - Cycling time (common in NL!)
    - Public transit options
    - Driving time
    - School bus information (if available)
    """
    try:
        # Get school
        school = get_school_by_id(db, school_id)
        if not school:
            raise HTTPException(status_code=404, detail="School not found")

        if not school.latitude or not school.longitude:
            raise HTTPException(
                status_code=400,
                detail="School location not available"
            )

        # Geocode the from_address
        parts = from_address.split(',')
        if len(parts) >= 2:
            street = parts[0].strip()
            city = parts[1].strip()
            coords = geocode_address(street, city)
        else:
            coords = geocode_city(from_address)

        if not coords:
            raise HTTPException(
                status_code=404,
                detail=f"Could not geocode address: '{from_address}'"
            )

        from_lat, from_lon = coords

        # Check for cached routes (optional optimization)
        # For now, calculate fresh every time

        # Calculate all routes
        routes = await get_transportation_for_school(
            school.latitude,
            school.longitude,
            from_lat,
            from_lon,
            include_school_bus=False  # TODO: Get from database
        )

        # Cache the results (optional)
        for route in routes:
            route_data = {
                "school_id": school_id,
                "from_address": from_address,
                "mode": route["mode"],
                "duration_minutes": route.get("duration_minutes"),
                "distance_km": route.get("distance_km"),
                "transit_details": route.get("details"),
                "bus_route_name": route.get("bus_route_name"),
                "bus_pickup_time": route.get("bus_pickup_time"),
                "bus_pickup_location": route.get("bus_pickup_location")
            }
            # Don't cache in DB for now to avoid clutter
            # create_transportation_route(db, route_data)

        # Convert to response models
        response = []
        for route in routes:
            response.append(TransportationRouteResponse(
                id=0,  # Not stored in DB
                school_id=school_id,
                mode=route["mode"],
                duration_minutes=route.get("duration_minutes"),
                distance_km=route.get("distance_km"),
                transit_details=route.get("details"),
                bus_route_name=route.get("bus_route_name"),
                bus_pickup_time=route.get("bus_pickup_time"),
                bus_pickup_location=route.get("bus_pickup_location"),
                from_address=from_address
            ))

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating transportation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating transportation: {str(e)}"
        )


# ============================================================================
# ADMISSION TIMELINE ROUTES
# ============================================================================

@router.get("/admission-timeline/{school_id}", response_model=AdmissionTimelineResponse)
def get_school_admission_timeline(
    school_id: int,
    academic_year: Optional[str] = Query(None, description="Academic year (e.g., '2024-2025')"),
    db: Session = Depends(get_db)
):
    """Get admission timeline for a school"""
    timeline = get_admission_timeline(db, school_id, academic_year)

    if not timeline:
        raise HTTPException(
            status_code=404,
            detail="Admission timeline not found for this school"
        )

    return timeline


@router.get("/admission-deadlines", response_model=List[AdmissionTimelineResponse])
def get_admission_deadlines(
    days_ahead: int = Query(30, ge=1, le=365, description="Days to look ahead"),
    municipality: Optional[str] = Query(None, description="Filter by municipality"),
    db: Session = Depends(get_db)
):
    """
    Get upcoming admission deadlines

    Useful for calendar exports and deadline tracking
    """
    deadlines = get_upcoming_deadlines(db, days_ahead, municipality)
    return deadlines


@router.get("/application-status", response_model=List[ApplicationStatusResponse])
def get_my_application_status(
    user_email: str = Query(..., description="User email address"),
    db: Session = Depends(get_db)
):
    """Get application status for all schools (for a user)"""
    statuses = get_application_status(db, user_email)
    return statuses


@router.post("/application-status", response_model=ApplicationStatusResponse)
def update_application_status(
    status_data: ApplicationStatusRequest,
    db: Session = Depends(get_db)
):
    """Create or update application status"""
    status = create_or_update_application_status(db, status_data)
    return status


# ============================================================================
# SCHOOL EVENTS ROUTES
# ============================================================================

@router.get("/events", response_model=List[SchoolEventResponse])
def get_events(
    school_id: Optional[int] = Query(None, description="Filter by school ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    city: Optional[str] = Query(None, description="Filter by city"),
    language: Optional[str] = Query(None, description="Filter by language"),
    start_date: Optional[datetime] = Query(None, description="Events after this date"),
    end_date: Optional[datetime] = Query(None, description="Events before this date"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get school events with filters

    Event types: open_house, info_evening, tour, application_period, other
    """
    events = get_school_events(
        db,
        school_id=school_id,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        city=city,
        language=language,
        limit=limit
    )
    return events


@router.post("/events", response_model=SchoolEventResponse)
def create_event(
    event_data: SchoolEventCreate,
    db: Session = Depends(get_db)
):
    """Create a new school event (for schools/admins)"""
    event = create_school_event(db, event_data)
    return event


@router.get("/events/calendar/ical")
def export_events_ical(
    school_id: Optional[int] = Query(None),
    city: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Export events to iCal format for calendar integration

    Returns .ics file compatible with Google Calendar, Outlook, etc.
    """
    events = get_school_events(db, school_id=school_id, city=city, limit=500)

    # Generate iCal format
    ical_content = "BEGIN:VCALENDAR\n"
    ical_content += "VERSION:2.0\n"
    ical_content += "PRODID:-//Dutch School Finder//Events//EN\n"
    ical_content += "CALSCALE:GREGORIAN\n"

    for event in events:
        ical_content += "BEGIN:VEVENT\n"
        ical_content += f"UID:{event.id}@dutchschoolfinder.com\n"
        ical_content += f"SUMMARY:{event.title}\n"

        if event.description:
            ical_content += f"DESCRIPTION:{event.description}\n"

        if event.location:
            ical_content += f"LOCATION:{event.location}\n"

        # Format datetime
        start_dt = event.start_datetime.strftime("%Y%m%dT%H%M%S")
        ical_content += f"DTSTART:{start_dt}\n"

        if event.end_datetime:
            end_dt = event.end_datetime.strftime("%Y%m%dT%H%M%S")
            ical_content += f"DTEND:{end_dt}\n"

        if event.booking_url:
            ical_content += f"URL:{event.booking_url}\n"

        ical_content += "END:VEVENT\n"

    ical_content += "END:VCALENDAR\n"

    from fastapi.responses import Response
    return Response(
        content=ical_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": "attachment; filename=school-events.ics"
        }
    )


# ============================================================================
# AFTER-SCHOOL CARE (BSO) ROUTES
# ============================================================================

@router.get("/after-school-care/{school_id}", response_model=List[AfterSchoolCareResponse])
def get_school_bso(
    school_id: int,
    db: Session = Depends(get_db)
):
    """Get after-school care (BSO) options for a school"""
    bso_options = get_after_school_care(db, school_id)
    return bso_options


@router.get("/after-school-care/search", response_model=List[AfterSchoolCareResponse])
def search_bso(
    max_cost: Optional[float] = Query(None, description="Maximum monthly cost"),
    offers_homework_help: Optional[bool] = Query(None),
    subsidy_eligible: Optional[bool] = Query(None),
    no_waiting_list: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """Search for after-school care with filters"""
    results = search_after_school_care(
        db,
        max_cost=max_cost,
        offers_homework_help=offers_homework_help,
        subsidy_eligible=subsidy_eligible,
        no_waiting_list=no_waiting_list
    )
    return results


# ============================================================================
# SPECIAL NEEDS SUPPORT ROUTES
# ============================================================================

@router.get("/special-needs/{school_id}", response_model=SpecialNeedsSupportResponse)
def get_school_special_needs(
    school_id: int,
    db: Session = Depends(get_db)
):
    """Get special needs support information for a school"""
    support = get_special_needs_support(db, school_id)

    if not support:
        raise HTTPException(
            status_code=404,
            detail="Special needs information not available for this school"
        )

    return support


@router.get("/schools/special-needs", response_model=List[SchoolResponse])
def search_special_needs_schools(
    dyslexia: bool = Query(False),
    adhd: bool = Query(False),
    autism: bool = Query(False),
    gifted: bool = Query(False),
    wheelchair_accessible: bool = Query(False),
    offers_speech_therapy: bool = Query(False),
    city: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Search for schools with specific special needs support

    Returns schools that match ANY of the selected criteria
    """
    # Get school IDs that match criteria
    school_ids = search_schools_with_special_needs(
        db,
        dyslexia=dyslexia,
        adhd=adhd,
        autism=autism,
        gifted=gifted,
        wheelchair_accessible=wheelchair_accessible,
        offers_speech_therapy=offers_speech_therapy,
        city=city
    )

    if not school_ids:
        return []

    # Get full school details
    schools = db.query(School).filter(School.id.in_(school_ids)).all()
    return schools


# ============================================================================
# ACADEMIC PERFORMANCE & TRENDS ROUTES
# ============================================================================

@router.get("/performance/{school_id}", response_model=List[AcademicPerformanceResponse])
def get_school_performance_history(
    school_id: int,
    years: int = Query(5, ge=1, le=10, description="Number of years of history"),
    db: Session = Depends(get_db)
):
    """Get historical academic performance data for a school"""
    history = get_performance_history(db, school_id, years)
    return history


@router.get("/performance/{school_id}/trend", response_model=PerformanceTrend)
def get_school_performance_trend(
    school_id: int,
    db: Session = Depends(get_db)
):
    """
    Get performance trend analysis for a school

    Includes:
    - Trend direction (improving, stable, declining)
    - Year-over-year changes
    - Badges (Rising Star, Consistent Excellence, etc.)
    """
    trend = calculate_performance_trend(db, school_id)

    if not trend:
        raise HTTPException(
            status_code=404,
            detail="Insufficient performance data for trend analysis"
        )

    return trend


# ============================================================================
# EXPORT & SHARE ROUTES
# ============================================================================

@router.post("/share/comparison", response_model=ShareableComparisonResponse)
def create_comparison_share_link(
    comparison_data: ShareableComparisonCreate,
    db: Session = Depends(get_db)
):
    """
    Create a shareable comparison link

    Returns a unique URL that can be shared with others
    Link expires after 30 days
    """
    # Validate that schools exist
    for school_id in comparison_data.school_ids:
        school = get_school_by_id(db, school_id)
        if not school:
            raise HTTPException(
                status_code=404,
                detail=f"School with ID {school_id} not found"
            )

    comparison = create_shareable_comparison(db, comparison_data)
    return comparison


@router.get("/share/{share_id}", response_model=ShareableComparisonResponse)
def get_shared_comparison(
    share_id: str,
    db: Session = Depends(get_db)
):
    """Get a shared comparison by ID"""
    comparison = get_shareable_comparison(db, share_id)

    if not comparison:
        raise HTTPException(
            status_code=404,
            detail="Shared comparison not found or expired"
        )

    return comparison


@router.get("/share/{share_id}/schools", response_model=List[SchoolResponse])
def get_shared_comparison_schools(
    share_id: str,
    db: Session = Depends(get_db)
):
    """Get the schools in a shared comparison"""
    comparison = get_shareable_comparison(db, share_id)

    if not comparison:
        raise HTTPException(
            status_code=404,
            detail="Shared comparison not found or expired"
        )

    # Get schools
    schools = []
    for school_id in comparison.school_ids:
        school = get_school_by_id(db, school_id)
        if school:
            schools.append(school)

    return schools


@router.get("/export/schools/csv")
async def export_schools_csv(
    ids: str = Query(..., description="Comma-separated school IDs"),
    db: Session = Depends(get_db)
):
    """
    Export schools to CSV format

    Example: /export/schools/csv?ids=1,2,3
    """
    try:
        school_ids = [int(id.strip()) for id in ids.split(',')]

        schools = []
        for school_id in school_ids:
            school = get_school_by_id(db, school_id)
            if school:
                schools.append(school)

        if not schools:
            raise HTTPException(status_code=404, detail="No schools found")

        # Generate CSV
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Name", "City", "Type", "Address", "Postal Code",
            "Inspection Rating", "Inspection Score", "CITO Score",
            "Bilingual", "International", "Phone", "Email", "Website"
        ])

        # Data
        for school in schools:
            writer.writerow([
                school.name,
                school.city,
                school.school_type,
                school.address or "",
                school.postal_code or "",
                school.inspection_rating or "",
                school.inspection_score or "",
                school.cito_score or "",
                "Yes" if school.is_bilingual else "No",
                "Yes" if school.is_international else "No",
                school.phone or "",
                school.email or "",
                school.website or ""
            ])

        csv_content = output.getvalue()

        from fastapi.responses import Response
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=schools-export.csv"
            }
        )

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid ID format. Use comma-separated numbers."
        )
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EXTENDED SCHOOL DETAILS (ALL FEATURES)
# ============================================================================

@router.get("/schools/{school_id}/extended", response_model=ExtendedSchoolResponse)
async def get_extended_school_details(
    school_id: int,
    include_transportation: bool = Query(False),
    from_address: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get complete school information including all extended features

    - Basic school info
    - Transportation options (if requested)
    - Admission timeline
    - Upcoming events
    - After-school care (BSO)
    - Special needs support
    - Performance history and trends
    """
    school = get_school_by_id(db, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    # Build extended response
    extended_data = {
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
        "description": school.description
    }

    # Add transportation if requested
    if include_transportation and from_address:
        try:
            transportation_response = await get_school_transportation(
                school_id, from_address, db
            )
            extended_data["transportation"] = transportation_response
        except:
            extended_data["transportation"] = None

    # Add admission timeline
    timeline = get_admission_timeline(db, school_id)
    extended_data["admission_timeline"] = timeline

    # Add upcoming events
    events = get_school_events(db, school_id=school_id, limit=10)
    extended_data["upcoming_events"] = events

    # Add after-school care
    bso = get_after_school_care(db, school_id)
    extended_data["after_school_care"] = bso

    # Add special needs support
    special_needs = get_special_needs_support(db, school_id)
    extended_data["special_needs_support"] = special_needs

    # Add performance history
    performance = get_performance_history(db, school_id, years=5)
    extended_data["performance_history"] = performance

    # Add performance trend
    trend = calculate_performance_trend(db, school_id)
    extended_data["performance_trend"] = trend.trend_direction if trend else None

    return ExtendedSchoolResponse(**extended_data)
