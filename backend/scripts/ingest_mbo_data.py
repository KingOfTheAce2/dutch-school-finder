"""
MBO (Middelbaar Beroepsonderwijs) Data Ingestion Script

Data Source: DUO (Dienst Uitvoering Onderwijs) Open Data
URL: https://www.duo.nl/open_onderwijsdata/databestanden/mbo/adressen/
License: CC-0 (1.0) - Public Domain
Format: CSV
Update Frequency: Monthly

This script downloads and ingests REAL MBO institution data from the official
Dutch government education database.

Usage:
    python -m scripts.ingest_mbo_data
    python -m scripts.ingest_mbo_data --dry-run
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
DUO_MBO_BASE_URL = "https://duo.nl/open_onderwijsdata/databestanden/mbo/adressen/"
# The actual file name pattern is typically: "01-adressen-instellingen-YYYYMM.csv"
# Example: "01-adressen-instellingen-202401.csv" for January 2024

USER_AGENT = "DutchEducationNavigator/1.0 (Educational Research)"


def get_latest_mbo_csv_url() -> str:
    """
    Construct URL for latest MBO address CSV

    NOTE: You may need to manually check the DUO website to confirm the latest file name.
    The pattern is typically: 01-adressen-instellingen-YYYYMM.csv
    """
    from datetime import datetime

    # Try current month and previous months
    current_date = datetime.now()

    for month_offset in range(6):  # Try current month and 5 previous months
        year_month = current_date.strftime("%Y%m") if month_offset == 0 else \
                     (current_date.replace(month=current_date.month - month_offset)).strftime("%Y%m")

        # Common file naming patterns
        possible_names = [
            f"01-adressen-instellingen-{year_month}.csv",
            f"01-Adressen-instellingen-{year_month}.csv",
            f"Adressen-instellingen-{year_month}.csv",
        ]

        for filename in possible_names:
            url = f"{DUO_MBO_BASE_URL}{filename}"
            print(f"   Trying: {url}")

            try:
                response = requests.head(url, timeout=10)
                if response.status_code == 200:
                    print(f"   ✓ Found: {url}")
                    return url
            except requests.RequestException:
                pass

    # Fallback: return a placeholder URL and let user specify
    print(f"\n   ⚠️  Could not auto-detect latest CSV file")
    print(f"   Please visit: {DUO_MBO_BASE_URL}")
    print(f"   And provide the filename manually")

    return None


def download_mbo_csv(url: str = None) -> str:
    """
    Download MBO address CSV from DUO

    Args:
        url: Optional explicit URL. If None, attempts to find latest.

    Returns:
        CSV content as string
    """
    if not url:
        url = get_latest_mbo_csv_url()

    if not url:
        raise ValueError("No CSV URL provided and could not auto-detect")

    print(f"\n📥 Downloading MBO data from DUO...")
    print(f"   URL: {url}")

    response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=60)
    response.raise_for_status()

    print(f"   ✓ Downloaded {len(response.content)} bytes")

    return response.text


def parse_mbo_csv(csv_content: str) -> List[Dict]:
    """
    Parse MBO CSV data

    Expected columns (may vary, check actual CSV):
    - INSTELLINGSNAAM
    - INSTELLINGSCODE (BRIN code)
    - STRAATNAAM
    - HUISNUMMER
    - HUISNUMMERTOEVOEGING
    - POSTCODE
    - PLAATSNAAM
    - GEMEENTENAAM
    - PROVINCIE
    - DENOMINATIE
    - BEVOEGD_GEZAG_NAAM
    - WEBSITE
    - TELEFOONNUMMER
    - E_MAIL
    """
    print(f"\n📊 Parsing MBO CSV data...")

    csv_file = io.StringIO(csv_content)
    reader = csv.DictReader(csv_file, delimiter=';')  # DUO typically uses ; as delimiter

    institutions = []
    for row in reader:
        try:
            # Extract and clean data
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

            institutions.append(institution)

        except Exception as e:
            print(f"   ⚠️  Error parsing row: {e}")
            continue

    print(f"   ✓ Parsed {len(institutions)} MBO institutions")

    return institutions


def store_mbo_in_db(db: Session, institutions: List[Dict], geocode: bool = True):
    """
    Store MBO institutions in the database

    Args:
        db: Database session
        institutions: List of MBO institution dictionaries
        geocode: Whether to geocode addresses
    """
    print(f"\n💾 Storing {len(institutions)} MBO institutions in database...")

    added_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0

    for inst in institutions:
        try:
            # Check if already exists (by BRIN code)
            existing = db.query(EducationInstitution).filter(
                EducationInstitution.institution_type == InstitutionType.MBO,
                EducationInstitution.details['brin_code'].astext == inst['brin_code']
            ).first()

            # Geocode address if needed
            latitude = None
            longitude = None
            if geocode and inst.get('address') and inst.get('city'):
                coords = geocode_address(inst['address'], inst['city'])
                if coords:
                    latitude, longitude = coords
                time.sleep(1)  # Rate limit for geocoding

            if existing:
                # Update existing record
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

                updated_count += 1
            else:
                # Create new institution
                institution = EducationInstitution(
                    institution_type=InstitutionType.MBO,
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
                added_count += 1

        except Exception as e:
            print(f"   ❌ Error storing {inst.get('name', 'unknown')}: {e}")
            error_count += 1

    db.commit()

    print(f"\n✅ Database update complete")
    print(f"   Added: {added_count}")
    print(f"   Updated: {updated_count}")
    print(f"   Errors: {error_count}")


def main():
    """Main entry point for MBO data ingestion"""
    import argparse

    parser = argparse.ArgumentParser(description='Ingest MBO data from DUO open data')
    parser.add_argument('--url', type=str, help='Explicit CSV URL (optional)')
    parser.add_argument('--no-geocode', action='store_true', help='Skip geocoding')
    parser.add_argument('--dry-run', action='store_true', help='Fetch data but do not store')
    args = parser.parse_args()

    print("=" * 70)
    print("MBO DATA INGESTION - DUO Open Data")
    print("=" * 70)
    print(f"\nData Source: {DUO_MBO_BASE_URL}")
    print("License: CC-0 (1.0) - Public Domain")
    print()

    try:
        # Download CSV
        csv_content = download_mbo_csv(args.url)

        # Parse CSV
        institutions = parse_mbo_csv(csv_content)

        print(f"\n📊 Summary: Found {len(institutions)} MBO institutions")

        if args.dry_run:
            print("\n🔍 DRY RUN - Data preview (first 10):")
            for i, inst in enumerate(institutions[:10], 1):
                print(f"\n   {i}. {inst['name']}")
                print(f"      City: {inst['city']}")
                print(f"      Address: {inst['address']}")
                print(f"      BRIN: {inst['brin_code']}")

            print("\n💡 Run without --dry-run to store in database")
        else:
            # Store in database
            db = SessionLocal()
            try:
                store_mbo_in_db(db, institutions, geocode=not args.no_geocode)
            finally:
                db.close()

            print("\n✨ All done! MBO data is now available in the application.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
