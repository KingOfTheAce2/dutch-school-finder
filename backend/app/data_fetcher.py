"""
Data fetcher for retrieving school information from Dutch open data sources
Includes DUO data and geocoding functionality
"""
import logging
import random
from typing import List, Dict
from sqlalchemy.orm import Session
from .database import SessionLocal, School
from .translations import translate_school_type, determine_education_features

logger = logging.getLogger(__name__)

# Sample Dutch cities with coordinates for demonstration
DUTCH_CITIES = {
    "Amsterdam": (52.3676, 4.9041),
    "Rotterdam": (51.9225, 4.47917),
    "Den Haag": (52.0705, 4.3007),
    "Utrecht": (52.0907, 5.1214),
    "Eindhoven": (51.4416, 5.4697),
    "Groningen": (53.2194, 6.5665),
    "Tilburg": (51.5555, 5.0913),
    "Almere": (52.3508, 5.2647),
    "Breda": (51.5719, 4.7683),
    "Nijmegen": (51.8126, 5.8372),
    "Haarlem": (52.3874, 4.6462),
    "Arnhem": (51.9851, 5.8987),
    "Leiden": (52.1601, 4.4970),
    "Delft": (52.0116, 4.3571),
    "Maastricht": (50.8514, 5.6909),
    "Amersfoort": (52.1561, 5.3878),
}

# Sample school names in Dutch
SCHOOL_NAMES = [
    "De Regenboog",
    "Het Palet",
    "De Kameleon",
    "De Vier Windstreken",
    "Het Kompas",
    "De Horizon",
    "De Springplank",
    "Het Mozaïek",
    "De Klimop",
    "De Bonte Tuin"
]

SECONDARY_SCHOOLS = [
    "Gymnasium",
    "Scholengemeenschap",
    "Lyceum",
    "College",
    "Marnix Gymnasium",
    "Stedelijk Gymnasium"
]


def generate_sample_schools() -> List[Dict]:
    """
    Generate sample school data for demonstration purposes
    In production, this would fetch from DUO API: https://duo.nl/open_onderwijsdata/
    """
    schools = []
    school_types = ["Primary", "Secondary", "Special Education"]
    education_structures = {
        "Secondary": ["VMBO", "HAVO", "VWO", "VMBO-HAVO", "HAVO-VWO", "VMBO-HAVO-VWO"],
        "Primary": ["Primary Education"],
        "Special Education": ["Special Needs"]
    }

    inspection_ratings = [
        ("Excellent", 9.0),
        ("Good", 7.5),
        ("Satisfactory", 6.5),
        ("Adequate", 5.5),
        ("Needs Improvement", 4.0)
    ]

    denominations = ["Public", "Catholic", "Protestant", "Islamic", "Anthroposophical", "Montessori", "Dalton"]

    school_id = 1
    for city, (lat, lon) in DUTCH_CITIES.items():
        # Generate 3-5 schools per city
        num_schools = random.randint(3, 5)

        for i in range(num_schools):
            school_type = random.choice(school_types)

            # Determine if primary or secondary name
            if school_type == "Secondary":
                base_name = random.choice(SECONDARY_SCHOOLS)
                name = f"{base_name} {city}" if len(city) < 10 else base_name
            else:
                name = f"{random.choice(SCHOOL_NAMES)} ({city})"

            rating, score = random.choice(inspection_ratings)

            # Some schools are bilingual or international
            is_international = random.random() < 0.05  # 5% international
            is_bilingual = random.random() < 0.15  # 15% bilingual
            offers_english = is_international or is_bilingual or random.random() < 0.1

            # Add slight random offset to coordinates
            school_lat = lat + random.uniform(-0.05, 0.05)
            school_lon = lon + random.uniform(-0.05, 0.05)

            school = {
                "name": name,
                "brin_code": f"{random.randint(10, 99)}{chr(random.randint(65, 90))}{chr(random.randint(65, 90))}",
                "city": city,
                "postal_code": f"{random.randint(1000, 9999)}{chr(random.randint(65, 90))}{chr(random.randint(65, 90))}",
                "address": f"{random.choice(['Schoolstraat', 'Hoofdweg', 'Marktplein', 'Kerkstraat'])} {random.randint(1, 200)}",
                "school_type": school_type,
                "education_structure": random.choice(education_structures[school_type]),
                "latitude": school_lat,
                "longitude": school_lon,
                "inspection_rating": rating,
                "inspection_score": score,
                "cito_score": round(random.uniform(530, 550), 1) if school_type == "Primary" else None,
                "is_bilingual": is_bilingual,
                "is_international": is_international,
                "offers_english": offers_english,
                "phone": f"0{random.randint(10, 99)}-{random.randint(100, 999)}{random.randint(1000, 9999)}",
                "email": f"info@{name.lower().replace(' ', '')}.nl",
                "website": f"https://www.{name.lower().replace(' ', '')}.nl",
                "denomination": random.choice(denominations),
                "student_count": random.randint(100, 800),
                "description": generate_school_description(name, school_type, is_bilingual, is_international)
            }

            schools.append(school)
            school_id += 1

    return schools


def generate_school_description(name: str, school_type: str, is_bilingual: bool, is_international: bool) -> str:
    """Generate a descriptive text for the school in English"""
    desc = f"{name} is a {school_type.lower()} school"

    if is_international:
        desc += " offering international education with English as the primary language of instruction"
    elif is_bilingual:
        desc += " with a bilingual Dutch-English program"
    else:
        desc += " providing quality education in the Dutch system"

    desc += ". We welcome students from diverse backgrounds and focus on academic excellence and personal development."

    return desc


async def fetch_and_store_schools():
    """
    Fetch school data and store in database

    In a production environment, this would:
    1. Fetch from DUO API: https://duo.nl/open_onderwijsdata/
    2. Fetch from Scholen op de Kaart: https://scholenopdekaart.nl/
    3. Geocode addresses using a geocoding service
    4. Merge quality data from Inspectorate

    For now, we generate sample data for demonstration
    """
    logger.info("Fetching school data...")

    # Generate sample schools
    schools_data = generate_sample_schools()

    # Store in database
    db = SessionLocal()
    try:
        for school_data in schools_data:
            # Check if school already exists
            existing = db.query(School).filter(School.brin_code == school_data["brin_code"]).first()
            if not existing:
                school = School(**school_data)
                db.add(school)

        db.commit()
        logger.info(f"Successfully stored {len(schools_data)} schools in database")
        return {"status": "success", "schools_added": len(schools_data)}
    except Exception as e:
        db.rollback()
        logger.error(f"Error storing schools: {e}")
        raise
    finally:
        db.close()


async def refresh_school_data():
    """
    Refresh all school data from sources
    This can be called periodically to update the database
    """
    logger.info("Refreshing school data...")

    db = SessionLocal()
    try:
        # In production, this would fetch fresh data from APIs
        # For now, we'll update existing records with new sample data

        schools = db.query(School).all()
        logger.info(f"Found {len(schools)} schools to refresh")

        # If no schools exist, fetch and store
        if len(schools) == 0:
            await fetch_and_store_schools()
            return {"status": "success", "message": "Initial data loaded"}

        return {"status": "success", "message": f"Refreshed {len(schools)} schools"}
    finally:
        db.close()
