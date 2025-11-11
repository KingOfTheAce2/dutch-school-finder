"""
HBO and University (Hoger Onderwijs) Data Ingestion Script

Data Source: DUO (Dienst Uitvoering Onderwijs) Open Data
URL: https://www.duo.nl/open_onderwijsdata/databestanden/ho/adressen/
License: CC-0 (1.0) - Public Domain
Format: CSV
Update Frequency: Monthly

This script downloads and ingests REAL HBO and university data from the official
Dutch government education database.

HBO (Hogeschool) = Universities of Applied Sciences
WO (Wetenschappelijk Onderwijs) = Research Universities

Usage:
    python -m scripts.ingest_hbo_university_data
    python -m scripts.ingest_hbo_university_data --dry-run
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import csv
import io
import time
from typing import List, Dict
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.education_institution import EducationInstitution, InstitutionType
from app.geocoding import geocode_address


# DUO Open Data URLs
DUO_HO_BASE_URL = "https://duo.nl/open_onderwijsdata/databestanden/ho/adressen/"
# File pattern: typically "01-adressen-instellingen-YYYYMM.csv"

USER_AGENT = "DutchEducationNavigator/1.0 (Educational Research)"


def get_latest_ho_csv_url() -> str:
    """
    Construct URL for latest higher education address CSV

    NOTE: You may need to manually check the DUO website to confirm the latest file name.
    """
    from datetime import datetime

    current_date = datetime.now()

    for month_offset in range(6):  # Try current month and 5 previous months
        year_month = current_date.strftime("%Y%m") if month_offset == 0 else \
                     (current_date.replace(month=current_date.month - month_offset)).strftime("%Y%m")

        possible_names = [
            f"01-adressen-instellingen-{year_month}.csv",
            f"01-Adressen-instellingen-{year_month}.csv",
            f"Adressen-instellingen-{year_month}.csv",
        ]

        for filename in possible_names:
            url = f"{DUO_HO_BASE_URL}{filename}"
            print(f"   Trying: {url}")

            try:
                response = requests.head(url, timeout=10)
                if response.status_code == 200:
                    print(f"   ✓ Found: {url}")
                    return url
            except requests.RequestException:
                pass

    print(f"\n   ⚠️  Could not auto-detect latest CSV file")
    print(f"   Please visit: {DUO_HO_BASE_URL}")

    return None


def download_ho_csv(url: str = None) -> str:
    """Download higher education address CSV from DUO"""
    if not url:
        url = get_latest_ho_csv_url()

    if not url:
        raise ValueError("No CSV URL provided and could not auto-detect")

    print(f"\n📥 Downloading Higher Education data from DUO...")
    print(f"   URL: {url}")

    response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=60)
    response.raise_for_status()

    print(f"   ✓ Downloaded {len(response.content)} bytes")

    return response.text


def parse_ho_csv(csv_content: str) -> Dict[str, List[Dict]]:
    """
    Parse higher education CSV data

    Returns:
        Dictionary with 'hbo' and 'university' keys, each containing a list of institutions
    """
    print(f"\n📊 Parsing Higher Education CSV data...")

    csv_file = io.StringIO(csv_content)
    reader = csv.DictReader(csv_file, delimiter=';')

    hbo_institutions = []
    university_institutions = []

    for row in reader:
        try:
            # Determine if HBO or University based on institution type field
            # Field name might be: SOORT_INSTELLING, TYPE_INSTELLING, or similar
            inst_type_raw = row.get('SOORT_INSTELLING', row.get('TYPE_INSTELLING', '')).upper()

            # Categorize
            is_university = 'WO' in inst_type_raw or 'UNIVERSIT' in inst_type_raw
            is_hbo = 'HBO' in inst_type_raw or 'HOGESCHOOL' in inst_type_raw

            if not is_university and not is_hbo:
                # Try to infer from name
                name = row.get('INSTELLINGSNAAM', '').upper()
                if 'UNIVERSIT' in name:
                    is_university = True
                elif 'HOGESCHOOL' in name or 'HBO' in name:
                    is_hbo = True
                else:
                    continue  # Skip if we can't determine type

            # Extract data
            institution = {
                'name': row.get('INSTELLINGSNAAM', '').strip(),
                'brin_code': row.get('INSTELLINGSCODE', '').strip(),
                'street': row.get('STRAATNAAM', '').strip(),
                'house_number': row.get('HUISNUMMER', '').strip(),
                'house_number_addition': row.get('HUISNUMMERTOEVOEGING', '').strip(),
                'postal_code': row.get('POSTCODE', '').strip(),
                'city': row.get('PLAATSNAAM', '').strip(),
                'municipality': row.get('GEMEENTENAAM', '').strip(),
                'province': row.get('PROVINCIE', '').strip(),
                'denomination': row.get('DENOMINATIE', '').strip(),
                'board': row.get('BEVOEGD_GEZAG_NAAM', '').strip(),
                'website': row.get('WEBSITE', '').strip(),
                'phone': row.get('TELEFOONNUMMER', '').strip(),
                'email': row.get('E_MAIL', '').strip(),
            }

            # Build full address
            address_parts = [institution['street']]
            if institution['house_number']:
                address_parts.append(institution['house_number'])
            if institution['house_number_addition']:
                address_parts.append(institution['house_number_addition'])

            institution['address'] = ' '.join(address_parts) if address_parts[0] else None

            # Skip entries without name or city
            if not institution['name'] or not institution['city']:
                continue

            # Add to appropriate list
            if is_university:
                university_institutions.append(institution)
            else:
                hbo_institutions.append(institution)

        except Exception as e:
            print(f"   ⚠️  Error parsing row: {e}")
            continue

    print(f"   ✓ Parsed {len(hbo_institutions)} HBO institutions")
    print(f"   ✓ Parsed {len(university_institutions)} universities")

    return {
        'hbo': hbo_institutions,
        'university': university_institutions
    }


def store_ho_in_db(db: Session, institutions: Dict[str, List[Dict]], geocode: bool = True):
    """
    Store HBO and university institutions in the database
    """
    print(f"\n💾 Storing higher education institutions in database...")

    stats = {
        'hbo': {'added': 0, 'updated': 0, 'errors': 0},
        'university': {'added': 0, 'updated': 0, 'errors': 0}
    }

    for inst_type_key, inst_type_enum in [('hbo', InstitutionType.HBO), ('university', InstitutionType.UNIVERSITY)]:
        print(f"\n   Processing {inst_type_key.upper()} institutions...")

        for inst in institutions[inst_type_key]:
            try:
                # Check if already exists
                existing = db.query(EducationInstitution).filter(
                    EducationInstitution.institution_type == inst_type_enum,
                    EducationInstitution.details['brin_code'].astext == inst['brin_code']
                ).first()

                # Geocode address if needed
                latitude = None
                longitude = None
                if geocode and inst.get('address') and inst.get('city'):
                    coords = geocode_address(inst['address'], inst['city'])
                    if coords:
                        latitude, longitude = coords
                    time.sleep(1)  # Rate limit

                if existing:
                    # Update existing
                    existing.name = inst['name']
                    existing.address = inst['address']
                    existing.postal_code = inst['postal_code']
                    existing.city = inst['city']
                    existing.phone = inst['phone']
                    existing.email = inst['email']
                    existing.website = inst['website']

                    if latitude and longitude:
                        existing.latitude = latitude
                        existing.longitude = longitude

                    existing.details = {
                        'brin_code': inst['brin_code'],
                        'denomination': inst['denomination'],
                        'board': inst['board'],
                        'municipality': inst['municipality'],
                        'province': inst['province'],
                    }

                    stats[inst_type_key]['updated'] += 1
                else:
                    # Create new
                    institution = EducationInstitution(
                        institution_type=inst_type_enum,
                        name=inst['name'],
                        city=inst['city'],
                        address=inst['address'],
                        postal_code=inst['postal_code'],
                        latitude=latitude,
                        longitude=longitude,
                        phone=inst['phone'],
                        email=inst['email'],
                        website=inst['website'],
                        rating_source='DUO',
                        details={
                            'brin_code': inst['brin_code'],
                            'denomination': inst['denomination'],
                            'board': inst['board'],
                            'municipality': inst['municipality'],
                            'province': inst['province'],
                        }
                    )

                    db.add(institution)
                    stats[inst_type_key]['added'] += 1

            except Exception as e:
                print(f"      ❌ Error storing {inst.get('name', 'unknown')}: {e}")
                stats[inst_type_key]['errors'] += 1

    db.commit()

    print(f"\n✅ Database update complete")
    for inst_type in ['hbo', 'university']:
        print(f"\n   {inst_type.upper()}:")
        print(f"      Added: {stats[inst_type]['added']}")
        print(f"      Updated: {stats[inst_type]['updated']}")
        print(f"      Errors: {stats[inst_type]['errors']}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Ingest HBO and university data from DUO')
    parser.add_argument('--url', type=str, help='Explicit CSV URL')
    parser.add_argument('--no-geocode', action='store_true', help='Skip geocoding')
    parser.add_argument('--dry-run', action='store_true', help='Fetch but do not store')
    args = parser.parse_args()

    print("=" * 70)
    print("HBO & UNIVERSITY DATA INGESTION - DUO Open Data")
    print("=" * 70)
    print(f"\nData Source: {DUO_HO_BASE_URL}")
    print("License: CC-0 (1.0) - Public Domain")
    print()

    try:
        # Download CSV
        csv_content = download_ho_csv(args.url)

        # Parse CSV
        institutions = parse_ho_csv(csv_content)

        total = len(institutions['hbo']) + len(institutions['university'])
        print(f"\n📊 Summary: Found {total} higher education institutions")
        print(f"   HBO: {len(institutions['hbo'])}")
        print(f"   Universities: {len(institutions['university'])}")

        if args.dry_run:
            print("\n🔍 DRY RUN - Data preview:")
            print("\n   HBO Institutions (first 5):")
            for i, inst in enumerate(institutions['hbo'][:5], 1):
                print(f"      {i}. {inst['name']} - {inst['city']}")

            print("\n   Universities (first 5):")
            for i, inst in enumerate(institutions['university'][:5], 1):
                print(f"      {i}. {inst['name']} - {inst['city']}")

            print("\n💡 Run without --dry-run to store in database")
        else:
            # Store in database
            db = SessionLocal()
            try:
                store_ho_in_db(db, institutions, geocode=not args.no_geocode)
            finally:
                db.close()

            print("\n✨ All done! HBO and university data is now available.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
