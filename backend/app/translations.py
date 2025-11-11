"""
Translation utilities for Dutch school terminology to English
Helps expat families understand the Dutch education system
"""

# School type translations
SCHOOL_TYPE_TRANSLATIONS = {
    "Basisschool": "Primary School",
    "Voortgezet onderwijs": "Secondary Education",
    "Speciaal onderwijs": "Special Education",
    "Speciaal basisonderwijs": "Special Primary Education",
    "VMBO": "Pre-vocational Secondary Education",
    "HAVO": "Senior General Secondary Education",
    "VWO": "Pre-university Education",
    "Gymnasium": "Grammar School (Classical)",
    "Atheneum": "Grammar School (Modern)"
}

# Education structure translations with explanations
EDUCATION_STRUCTURE_INFO = {
    "VMBO": {
        "name": "Pre-vocational Secondary Education",
        "description": "4-year program preparing students for vocational training (MBO)",
        "duration": "4 years",
        "age_range": "12-16"
    },
    "HAVO": {
        "name": "Senior General Secondary Education",
        "description": "5-year program preparing students for higher professional education (HBO)",
        "duration": "5 years",
        "age_range": "12-17"
    },
    "VWO": {
        "name": "Pre-university Education",
        "description": "6-year program preparing students for university (WO)",
        "duration": "6 years",
        "age_range": "12-18"
    },
    "VMBO-HAVO": {
        "name": "Combined VMBO-HAVO",
        "description": "School offering both VMBO and HAVO tracks",
        "duration": "4-5 years",
        "age_range": "12-17"
    },
    "HAVO-VWO": {
        "name": "Combined HAVO-VWO",
        "description": "School offering both HAVO and VWO tracks",
        "duration": "5-6 years",
        "age_range": "12-18"
    },
    "VMBO-HAVO-VWO": {
        "name": "Comprehensive Secondary School",
        "description": "School offering all three educational levels",
        "duration": "4-6 years",
        "age_range": "12-18"
    }
}

# Denomination translations
DENOMINATION_TRANSLATIONS = {
    "Openbaar": "Public (Non-denominational)",
    "Rooms-Katholiek": "Roman Catholic",
    "Protestants-Christelijk": "Protestant Christian",
    "Gereformeerd": "Reformed",
    "Islamitisch": "Islamic",
    "Joods": "Jewish",
    "Hindoeïstisch": "Hindu",
    "Antroposofisch": "Anthroposophical (Waldorf/Steiner)",
    "Montessori": "Montessori",
    "Dalton": "Dalton",
    "Jenaplan": "Jenaplan",
    "Vrije School": "Free School (Steiner)"
}

# Inspection rating translations
INSPECTION_RATINGS = {
    "Zeer goed": "Excellent",
    "Goed": "Good",
    "Voldoende": "Satisfactory",
    "Onvoldoende": "Inadequate",
    "Zeer zwak": "Very Weak"
}


def translate_school_type(dutch_type: str) -> str:
    """Translate Dutch school type to English"""
    return SCHOOL_TYPE_TRANSLATIONS.get(dutch_type, dutch_type)


def translate_denomination(dutch_denomination: str) -> str:
    """Translate Dutch denomination to English"""
    return DENOMINATION_TRANSLATIONS.get(dutch_denomination, dutch_denomination)


def translate_inspection_rating(dutch_rating: str) -> str:
    """Translate Dutch inspection rating to English"""
    return INSPECTION_RATINGS.get(dutch_rating, dutch_rating)


def get_education_structure_info(structure: str) -> dict:
    """Get detailed information about an education structure"""
    return EDUCATION_STRUCTURE_INFO.get(structure, {
        "name": structure,
        "description": "Educational program",
        "duration": "Varies",
        "age_range": "Varies"
    })


def determine_education_features(school_data: dict) -> dict:
    """
    Analyze school data to determine expat-friendly features
    Returns dict with is_bilingual, is_international, offers_english flags
    """
    name = school_data.get("name", "").lower()

    # Check for international school indicators
    is_international = any(keyword in name for keyword in [
        "international", "european", "british", "american", "ib"
    ])

    # Check for bilingual indicators
    is_bilingual = any(keyword in name for keyword in [
        "bilingual", "tweetalig", "bilinguaal"
    ])

    # Assume international schools offer English
    offers_english = is_international or is_bilingual

    return {
        "is_bilingual": is_bilingual,
        "is_international": is_international,
        "offers_english": offers_english
    }


def get_education_system_guide() -> dict:
    """
    Provide a comprehensive guide to the Dutch education system for expats
    """
    return {
        "primary_education": {
            "name": "Primary Education (Basisonderwijs)",
            "age_range": "4-12 years",
            "duration": "8 years",
            "description": "All children in the Netherlands attend primary school from age 4 to 12. The final year includes a CITO test that helps determine secondary school placement."
        },
        "secondary_education": {
            "name": "Secondary Education (Voortgezet Onderwijs)",
            "age_range": "12-16/18 years",
            "tracks": [
                {
                    "name": "VMBO (Pre-vocational)",
                    "duration": "4 years",
                    "description": "Prepares students for vocational training (MBO)"
                },
                {
                    "name": "HAVO (Higher General)",
                    "duration": "5 years",
                    "description": "Prepares students for professional higher education (HBO)"
                },
                {
                    "name": "VWO (Pre-university)",
                    "duration": "6 years",
                    "description": "Prepares students for university (WO)"
                }
            ]
        },
        "special_programs": {
            "international_schools": "English-language schools following international curricula (IB, British, American)",
            "bilingual_schools": "Dutch schools offering bilingual Dutch-English programs",
            "special_education": "Schools for children with special educational needs"
        }
    }
