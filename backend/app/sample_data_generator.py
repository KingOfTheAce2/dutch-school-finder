"""
Generate sample data for extended features
Populates the database with realistic test data for:
- Admission timelines
- School events
- After-school care (BSO)
- Special needs support
- Academic performance history
"""
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .database import (
    SessionLocal,
    School,
    AdmissionTimeline,
    SchoolEvent,
    AfterSchoolCare,
    SpecialNeedsSupport,
    AcademicPerformance
)


def generate_admission_timelines(db: Session):
    """Generate admission timelines for schools"""
    print("Generating admission timelines...")

    schools = db.query(School).all()
    current_year = datetime.now().year
    academic_year = f"{current_year}-{current_year + 1}"

    # Municipality-specific enrollment systems
    municipality_systems = {
        "Amsterdam": "Prewonen",
        "Rotterdam": "Rotterdam Enrollment Portal",
        "Utrecht": "Utrecht School Enrollment",
        "Den Haag": "Schoolwijzer",
        "Eindhoven": "Eindhoven School Registration"
    }

    for school in schools[:50]:  # Generate for first 50 schools
        # Skip if already exists
        existing = db.query(AdmissionTimeline).filter(
            AdmissionTimeline.school_id == school.id,
            AdmissionTimeline.academic_year == academic_year
        ).first()

        if existing:
            continue

        # Typical Dutch school enrollment timeline
        enrollment_opens = datetime(current_year - 1, 11, 1)  # November previous year
        enrollment_deadline = datetime(current_year, 1, 15)  # January 15
        acceptance_notification = datetime(current_year, 3, 15)  # March
        school_year_start = datetime(current_year, 8, 20)  # Late August

        required_docs = [
            "Birth certificate",
            "Proof of address",
            "Previous school report (if applicable)",
            "Immunization records"
        ]

        if school.school_type == "Secondary":
            required_docs.append("Primary school recommendation (CITO score)")

        timeline = AdmissionTimeline(
            school_id=school.id,
            academic_year=academic_year,
            enrollment_opens=enrollment_opens,
            enrollment_deadline=enrollment_deadline,
            acceptance_notification_date=acceptance_notification,
            school_year_start=school_year_start,
            required_documents=required_docs,
            municipality=school.city,
            enrollment_system=municipality_systems.get(school.city, "Standard Enrollment"),
            enrollment_url=f"https://enrollment.{school.city.lower()}.nl",
            notes="Early application recommended for popular schools."
        )

        db.add(timeline)

    db.commit()
    print(f"✓ Generated admission timelines")


def generate_school_events(db: Session):
    """Generate school events and open houses"""
    print("Generating school events...")

    schools = db.query(School).all()
    event_types = ["open_house", "info_evening", "tour", "application_period"]
    languages = ["Dutch", "English", "Both"]

    event_templates = {
        "open_house": [
            "Open House - Come Visit Our School!",
            "Open Day for Prospective Families",
            "School Open House Event"
        ],
        "info_evening": [
            "Information Evening for Parents",
            "Parent Information Session",
            "Q&A Evening with Principal"
        ],
        "tour": [
            "Guided School Tour",
            "Campus Visit and Tour",
            "Personal School Tour"
        ]
    }

    for school in schools[:40]:  # Generate events for first 40 schools
        # Generate 2-4 events per school
        num_events = random.randint(2, 4)

        for _ in range(num_events):
            event_type = random.choice(event_types)

            # Random date in next 3 months
            days_ahead = random.randint(7, 90)
            event_date = datetime.now() + timedelta(days=days_ahead)
            event_date = event_date.replace(hour=random.choice([10, 14, 19]), minute=0)

            # Duration
            duration = timedelta(hours=random.choice([1, 2, 3]))
            end_datetime = event_date + duration

            # Language - international schools more likely to have English
            if school.is_international:
                language = "English"
            elif school.is_bilingual:
                language = "Both"
            else:
                language = random.choice(["Dutch", "Both"])

            # Virtual or in-person
            is_virtual = random.random() < 0.2  # 20% virtual

            title = random.choice(event_templates.get(event_type, ["School Event"]))

            event = SchoolEvent(
                school_id=school.id,
                title=title,
                event_type=event_type,
                description=f"Join us to learn more about {school.name} and our educational programs.",
                start_datetime=event_date,
                end_datetime=end_datetime,
                location=school.address if not is_virtual else "Online",
                is_virtual=is_virtual,
                virtual_tour_url=f"https://tour.{school.name.lower().replace(' ', '')}.nl" if is_virtual else None,
                requires_booking=random.choice([True, False]),
                booking_url=f"https://{school.name.lower().replace(' ', '')}.nl/book" if random.random() < 0.5 else None,
                max_attendees=random.choice([20, 30, 50, None]),
                language=language,
                is_active=True
            )

            db.add(event)

    db.commit()
    print(f"✓ Generated school events")


def generate_after_school_care(db: Session):
    """Generate BSO (after-school care) data"""
    print("Generating after-school care (BSO) data...")

    schools = db.query(School).filter(
        School.school_type == "Primary"
    ).all()  # BSO is mainly for primary schools

    bso_providers = [
        "KidsFirst BSO",
        "Happy Kids Opvang",
        "Partou Buitenschoolse Opvang",
        "SKI Buitenschoolse Opvang",
        "Smallsteps BSO"
    ]

    activities_pool = [
        "Outdoor play",
        "Sports and games",
        "Arts and crafts",
        "Reading corner",
        "Music activities",
        "Science experiments",
        "Board games",
        "Cooking workshops"
    ]

    for school in schools[:60]:  # Generate BSO for 60 primary schools
        # Skip if already has BSO
        existing = db.query(AfterSchoolCare).filter(
            AfterSchoolCare.school_id == school.id
        ).first()

        if existing:
            continue

        # 70% of schools have BSO
        if random.random() < 0.7:
            provider = random.choice(bso_providers)
            same_location = random.random() < 0.8  # 80% at same location

            # Activities
            num_activities = random.randint(4, 8)
            activities = random.sample(activities_pool, num_activities)

            # Costs (average BSO in NL is €300-500/month)
            monthly_cost = round(random.uniform(280, 520), 2)
            hourly_cost = round(monthly_cost / 160, 2)  # Assuming ~40 hours/week

            bso = AfterSchoolCare(
                school_id=school.id,
                provider_name=provider,
                provider_website=f"https://{provider.lower().replace(' ', '')}.nl",
                provider_phone=f"020-{random.randint(1000000, 9999999)}",
                provider_email=f"info@{provider.lower().replace(' ', '')}.nl",
                same_location_as_school=same_location,
                address=school.address if same_location else f"{random.randint(1, 200)} Main Street, {school.city}",
                latitude=school.latitude if same_location else None,
                longitude=school.longitude if same_location else None,
                opening_time="15:00",
                closing_time=random.choice(["18:00", "18:30", "19:00"]),
                operates_school_holidays=random.choice([True, False]),
                activities=activities,
                offers_homework_help=random.choice([True, False]),
                offers_sports=random.choice([True, False]),
                offers_arts_crafts=random.choice([True, False]),
                offers_outdoor_play=True,  # Most BSOs offer this
                monthly_cost_euros=monthly_cost,
                hourly_cost_euros=hourly_cost,
                subsidy_eligible=True,  # Most BSOs are subsidy eligible
                capacity=random.randint(40, 120),
                current_occupancy=random.randint(20, 100),
                has_waiting_list=random.choice([True, False]),
                registration_url=f"https://{provider.lower().replace(' ', '')}.nl/register",
                inspection_rating=random.choice(["Excellent", "Good", "Satisfactory"]),
                staff_child_ratio="1:8"  # Common ratio in NL
            )

            db.add(bso)

    db.commit()
    print(f"✓ Generated after-school care data")


def generate_special_needs_support(db: Session):
    """Generate special needs support information"""
    print("Generating special needs support data...")

    schools = db.query(School).all()

    programs_pool = [
        "Individualized Education Plan (IEP)",
        "Small group instruction",
        "Sensory-friendly classroom",
        "Behavioral support",
        "Gifted and talented program",
        "Learning support center",
        "Assistive technology",
        "Modified curriculum"
    ]

    for school in schools[:50]:
        # Skip if already exists
        existing = db.query(SpecialNeedsSupport).filter(
            SpecialNeedsSupport.school_id == school.id
        ).first()

        if existing:
            continue

        # Determine support level (special education schools have more support)
        is_special_ed = school.school_type == "Special Education"

        # Generate programs
        num_programs = random.randint(3, 7) if is_special_ed else random.randint(1, 4)
        programs = random.sample(programs_pool, min(num_programs, len(programs_pool)))

        support = SpecialNeedsSupport(
            school_id=school.id,
            supports_dyslexia=random.random() < (0.8 if is_special_ed else 0.4),
            supports_adhd=random.random() < (0.7 if is_special_ed else 0.3),
            supports_autism=random.random() < (0.6 if is_special_ed else 0.25),
            supports_gifted=random.random() < 0.3,
            supports_physical_disability=random.random() < (0.7 if is_special_ed else 0.2),
            supports_visual_impairment=random.random() < (0.5 if is_special_ed else 0.15),
            supports_hearing_impairment=random.random() < (0.5 if is_special_ed else 0.15),
            offers_speech_therapy=random.random() < (0.8 if is_special_ed else 0.3),
            offers_occupational_therapy=random.random() < (0.6 if is_special_ed else 0.2),
            offers_special_education_classrooms=is_special_ed or (random.random() < 0.2),
            wheelchair_accessible=random.random() < 0.6,
            has_elevator=random.random() < 0.4,
            has_accessible_restrooms=random.random() < 0.7,
            special_education_staff_count=random.randint(2, 10) if is_special_ed else random.randint(0, 3),
            support_staff_ratio="1:20" if not is_special_ed else "1:5",
            programs_offered=programs,
            referral_process="Contact school for assessment and referral process.",
            funding_info="Funding available through municipality for qualified students.",
            notes="Please contact the school directly to discuss specific needs."
        )

        db.add(support)

    db.commit()
    print(f"✓ Generated special needs support data")


def generate_academic_performance_history(db: Session):
    """Generate historical academic performance data"""
    print("Generating academic performance history...")

    schools = db.query(School).all()
    current_year = datetime.now().year

    for school in schools[:50]:
        # Generate 5 years of historical data
        for year_offset in range(5):
            year = current_year - year_offset - 1
            academic_year = f"{year}-{year + 1}"

            # Skip if already exists
            existing = db.query(AcademicPerformance).filter(
                AcademicPerformance.school_id == school.id,
                AcademicPerformance.academic_year == academic_year
            ).first()

            if existing:
                continue

            # Generate performance with some trend
            # Create upward, downward, or stable trends
            base_cito = school.cito_score if school.cito_score else 535
            trend = random.choice(["improving", "stable", "declining"])

            if trend == "improving":
                variation = year_offset * random.uniform(1.5, 3.0)
                cito_score = base_cito - variation
            elif trend == "declining":
                variation = year_offset * random.uniform(1.5, 3.0)
                cito_score = base_cito + variation
            else:  # stable
                cito_score = base_cito + random.uniform(-2, 2)

            cito_score = round(cito_score, 1)

            # Inspection score correlation with CITO
            if school.cito_score:
                inspection_score = round((cito_score - 530) / 2 + 7.0, 1)
                inspection_score = max(5.0, min(10.0, inspection_score))
            else:
                inspection_score = school.inspection_score

            # Student count with slight variation
            student_count = school.student_count
            if student_count:
                student_count = int(student_count * random.uniform(0.95, 1.05))

            performance = AcademicPerformance(
                school_id=school.id,
                academic_year=academic_year,
                year_start=year,
                cito_score=cito_score if school.school_type == "Primary" else None,
                inspection_rating=school.inspection_rating,
                inspection_score=inspection_score,
                student_count=student_count,
                teacher_count=int(student_count / 25) if student_count else None,
                teacher_turnover_rate=round(random.uniform(5, 20), 1),
                graduation_rate=round(random.uniform(85, 99), 1) if school.school_type == "Secondary" else None,
                university_acceptance_rate=round(random.uniform(60, 95), 1) if school.education_structure in ["VWO", "HAVO"] else None,
                data_source="Generated Sample Data"
            )

            db.add(performance)

    db.commit()
    print(f"✓ Generated academic performance history")


def generate_all_sample_data():
    """Generate all sample data for extended features"""
    print("\n" + "="*60)
    print("GENERATING SAMPLE DATA FOR EXTENDED FEATURES")
    print("="*60 + "\n")

    db = SessionLocal()

    try:
        generate_admission_timelines(db)
        generate_school_events(db)
        generate_after_school_care(db)
        generate_special_needs_support(db)
        generate_academic_performance_history(db)

        print("\n" + "="*60)
        print("✓ ALL SAMPLE DATA GENERATED SUCCESSFULLY!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n✗ Error generating sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    generate_all_sample_data()
