"""
LRK & RBK Childcare Data Ingestion Script

Data Sources:
1. LRK (Landelijk Register Kinderopvang) - Domestic childcare
   URL: https://www.landelijkregisterkinderopvang.nl/opendata/export_opendata_lrk.csv
   License: CC-0 (1.0) - Public Domain
   Update Frequency: Twice per week (Monday & Friday)
   Coverage: ~10,000+ childcare locations in the Netherlands

2. RBK (Register Buitenlandse Kinderopvang) - Foreign childcare
   URL: https://data.overheid.nl/dataset/gegevens-kinderopvanglocaties-rbk
   License: CC-0 (1.0) - Public Domain

This script downloads and ingests REAL childcare data from the official
Dutch government registries maintained by DUO/Ministry of Social Affairs.

Usage:
    python -m scripts.ingest_childcare_official --source lrk
    python -m scripts.ingest_childcare_official --source rbk
    python -m scripts.ingest_childcare_official --source all
    python -m scripts.ingest_childcare_official --dry-run
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
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.education_institution import EducationInstitution, InstitutionType
from app.geocoding import geocode_address


# Official data source URLs
LRK_CSV_URL = "https://www.landelijkregisterkinderopvang.nl/opendata/export_opendata_lrk.csv"
RBK_CSV_URL = "https://www.landelijkregisterkinderopvang.nl/opendata/export_opendata_rbk.csv"  # Pattern guess

USER_AGENT = "DutchEducationNavigator/1.0 (Educational Research)"


def download_childcare_csv(source: str = "lrk") -> str:
    """
    Download childcare CSV from official government source

    Args:
        source: 'lrk' (domestic) or 'rbk' (foreign)

    Returns:
        CSV content as string
    """
    url = LRK_CSV_URL if source == "lrk" else RBK_CSV_URL

    print(f"\n📥 Downloading {source.upper()} childcare data...")
    print(f"   URL: {url}")
    print(f"   Updated: Twice per week (Monday & Friday)")

    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=60)
        response.raise_for_status()

        print(f"   ✓ Downloaded {len(response.content)} bytes")

        return response.text

    except requests.RequestException as e:
        print(f"   ❌ Download failed: {e}")
        if source == "rbk":
            print(f"   Note: RBK URL may need to be confirmed on data.overheid.nl")
        raise


def parse_childcare_csv(csv_content: str, source: str) -> List[Dict]:
    """
    Parse LRK/RBK CSV data

    Expected columns (LRK):
    - LRK_ID (unique identifier)
    - NAAM_KINDEROPVANG (childcare name)
    - STRAATNAAM
    - HUISNUMMER
    - HUISNUMMER_TOEVOEGING
    - POSTCODE
    - PLAATSNAAM
    - TELEFOONNUMMER
    - EMAIL
    - WEBSITE
    - HOUDER (owner/operator)
    - REGISTRATIEDATUM (registration date)
    - SOORT_KINDEROPVANG (type: dagopvang, BSO, gastouderopvang, etc.)
    - CAPACITEIT (capacity)
    """
    print(f"\n📊 Parsing {source.upper()} CSV data...")

    # Detect delimiter (usually ; for Dutch CSV files)
    csv_file = io.StringIO(csv_content)
    sample = csv_file.read(1024)
    csv_file.seek(0)

    delimiter = ';' if ';' in sample else ','

    reader = csv.DictReader(csv_file, delimiter=delimiter)

    centers = []
    skipped = 0

    for row in reader:
        try:
            # Handle different possible column names (case-insensitive)
            row_upper = {k.upper(): v for k, v in row.items()}

            # Extract LRK ID (unique identifier)
            lrk_id = (
                row_upper.get('LRK_ID') or
                row_upper.get('LRK-ID') or
                row_upper.get('LRKID') or
                ''
            ).strip()

            if not lrk_id:
                skipped += 1
                continue

            # Extract name
            name = (
                row_upper.get('NAAM_KINDEROPVANG') or
                row_upper.get('NAAM') or
                row_upper.get('BEDRIJFSNAAM') or
                ''
            ).strip()

            if not name:
                skipped += 1
                continue

            # Extract address components
            street = row_upper.get('STRAATNAAM', '').strip()
            house_number = row_upper.get('HUISNUMMER', '').strip()
            house_addition = row_upper.get('HUISNUMMER_TOEVOEGING', '').strip()
            postal_code = row_upper.get('POSTCODE', '').strip()
            city = (
                row_upper.get('PLAATSNAAM') or
                row_upper.get('PLAATS') or
                row_upper.get('WOONPLAATS') or
                ''
            ).strip()

            if not city:
                skipped += 1
                continue

            # Build full address
            address_parts = [street]
            if house_number:
                address_parts.append(house_number)
            if house_addition:
                address_parts.append(house_addition)

            address = ' '.join(address_parts) if address_parts[0] else None

            # Extract contact info
            phone = row_upper.get('TELEFOONNUMMER', '').strip()
            email = row_upper.get('EMAIL', '').strip()
            website = row_upper.get('WEBSITE', '').strip()

            # Extract type
            care_type = (
                row_upper.get('SOORT_KINDEROPVANG') or
                row_upper.get('TYPE') or
                row_upper.get('SOORT') or
                ''
            ).strip()

            # Extract capacity
            capacity_str = row_upper.get('CAPACITEIT', '').strip()
            capacity = None
            if capacity_str:
                try:
                    capacity = int(capacity_str)
                except ValueError:
                    pass

            # Extract owner/operator
            owner = (
                row_upper.get('HOUDER') or
                row_upper.get('HOUDER_NAAM') or
                row_upper.get('BEDRIJF') or
                ''
            ).strip()

            # Extract registration date
            registration_date = (
                row_upper.get('REGISTRATIEDATUM') or
                row_upper.get('DATUM_REGISTRATIE') or
                ''
            ).strip()

            center = {
                'lrk_id': lrk_id,
                'name': name,
                'street': street,
                'house_number': house_number,
                'house_addition': house_addition,
                'address': address,
                'postal_code': postal_code,
                'city': city,
                'phone': phone,
                'email': email,
                'website': website,
                'type': care_type,
                'capacity': capacity,
                'owner': owner,
                'registration_date': registration_date,
                'source': source,
            }

            centers.append(center)

        except Exception as e:
            print(f"   ⚠️  Error parsing row: {e}")
            skipped += 1
            continue

    print(f"   ✓ Parsed {len(centers)} childcare centers")
    if skipped > 0:
        print(f"   ⏭️  Skipped {skipped} invalid entries")

    return centers


def store_childcare_in_db(db: Session, centers: List[Dict], geocode: bool = True):
    """
    Store childcare centers in the database

    Args:
        db: Database session
        centers: List of childcare center dictionaries
        geocode: Whether to geocode addresses
    """
    print(f"\n💾 Storing {len(centers)} childcare centers in database...")

    added_count = 0
    updated_count = 0
    error_count = 0

    for center in centers:
        try:
            # Check if already exists (by LRK ID)
            existing = db.query(EducationInstitution).filter(
                EducationInstitution.institution_type == InstitutionType.CHILDCARE,
                EducationInstitution.details['lrk_id'].astext == center['lrk_id']
            ).first()

            # Geocode address if needed
            latitude = None
            longitude = None
            if geocode and center.get('address') and center.get('city'):
                coords = geocode_address(center['address'], center['city'])
                if coords:
                    latitude, longitude = coords
                time.sleep(1)  # Rate limit for geocoding

            # Prepare details JSON
            details = {
                'lrk_id': center['lrk_id'],
                'type': center['type'],
                'capacity': center['capacity'],
                'owner': center['owner'],
                'registration_date': center['registration_date'],
                'source': center['source'],
            }

            if existing:
                # Update existing record
                existing.name = center['name']
                existing.address = center['address']
                existing.postal_code = center['postal_code']
                existing.city = center['city']
                existing.phone = center['phone']
                existing.email = center['email']
                existing.website = center['website']

                if latitude and longitude:
                    existing.latitude = latitude
                    existing.longitude = longitude

                existing.details = details
                updated_count += 1
            else:
                # Create new institution
                institution = EducationInstitution(
                    institution_type=InstitutionType.CHILDCARE,
                    name=center['name'],
                    city=center['city'],
                    address=center['address'],
                    postal_code=center['postal_code'],
                    latitude=latitude,
                    longitude=longitude,
                    phone=center['phone'],
                    email=center['email'],
                    website=center['website'],
                    rating_source='GGD/LRK',
                    details=details
                )

                db.add(institution)
                added_count += 1

        except Exception as e:
            print(f"   ❌ Error storing {center.get('name', 'unknown')}: {e}")
            error_count += 1

    db.commit()

    print(f"\n✅ Database update complete")
    print(f"   Added: {added_count}")
    print(f"   Updated: {updated_count}")
    print(f"   Errors: {error_count}")


def main():
    """Main entry point for childcare data ingestion"""
    import argparse

    parser = argparse.ArgumentParser(description='Ingest childcare data from official LRK/RBK registries')
    parser.add_argument('--source', type=str, choices=['lrk', 'rbk', 'all'], default='lrk',
                        help='Data source: lrk (domestic), rbk (foreign), or all')
    parser.add_argument('--no-geocode', action='store_true', help='Skip geocoding')
    parser.add_argument('--dry-run', action='store_true', help='Fetch but do not store')
    parser.add_argument('--limit', type=int, help='Limit number of records (for testing)')
    args = parser.parse_args()

    print("=" * 70)
    print("CHILDCARE DATA INGESTION - Official LRK/RBK Registries")
    print("=" * 70)
    print("\nData Sources:")
    print("  LRK: https://www.landelijkregisterkinderopvang.nl/opendata/")
    print("  License: CC-0 (1.0) - Public Domain")
    print("  Update: Twice per week (Monday & Friday)")
    print()

    sources = ['lrk', 'rbk'] if args.source == 'all' else [args.source]

    all_centers = []

    for source in sources:
        try:
            # Download CSV
            csv_content = download_childcare_csv(source)

            # Parse CSV
            centers = parse_childcare_csv(csv_content, source)

            # Apply limit if specified
            if args.limit:
                centers = centers[:args.limit]

            all_centers.extend(centers)

            print(f"\n📊 {source.upper()} Summary: Found {len(centers)} childcare centers")

        except Exception as e:
            print(f"\n❌ Error processing {source.upper()}: {e}")
            if source == 'rbk':
                print("   Note: RBK data may require different URL or format")
            continue

    if args.dry_run:
        print("\n🔍 DRY RUN - Data preview (first 10):")
        for i, center in enumerate(all_centers[:10], 1):
            print(f"\n   {i}. {center['name']}")
            print(f"      City: {center['city']}")
            print(f"      Address: {center['address']}")
            print(f"      LRK ID: {center['lrk_id']}")
            print(f"      Type: {center['type']}")
            if center['capacity']:
                print(f"      Capacity: {center['capacity']}")

        print(f"\n   Total: {len(all_centers)} centers")
        print("\n💡 Run without --dry-run to store in database")
    else:
        # Store in database
        db = SessionLocal()
        try:
            store_childcare_in_db(db, all_centers, geocode=not args.no_geocode)
        finally:
            db.close()

        print("\n✨ All done! Childcare data is now available in the application.")
        print("   Data will be refreshed twice per week by DUO.")


if __name__ == "__main__":
    main()
