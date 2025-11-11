"""
Migration script: School → EducationInstitution

This script migrates existing school data to the new unified education_institutions table.

Usage:
    python -m scripts.migrate_to_unified_model

Options:
    --dry-run: Show what would be migrated without making changes
    --rollback: Delete education_institutions table and restore schools table
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base, School
from app.education_institution import EducationInstitution, InstitutionType


def migrate_schools_to_institutions(db: Session, dry_run: bool = False):
    """
    Migrate existing School data to EducationInstitution

    Args:
        db: Database session
        dry_run: If True, only print what would be done without committing
    """
    print("=" * 60)
    print("MIGRATION: School → EducationInstitution")
    print("=" * 60)

    # Count existing schools
    school_count = db.query(School).count()
    print(f"\n📊 Found {school_count} schools to migrate")

    if school_count == 0:
        print("❌ No schools found. Nothing to migrate.")
        return

    # Check if institutions table already has data
    institution_count = db.query(EducationInstitution).count()
    if institution_count > 0:
        print(f"⚠️  Warning: education_institutions table already contains {institution_count} records")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Migration cancelled")
            return

    # Fetch all schools
    schools = db.query(School).all()

    migrated_count = 0
    error_count = 0

    for school in schools:
        try:
            # Determine institution type
            institution_type = InstitutionType.PRIMARY
            if school.school_type:
                if 'Secondary' in school.school_type:
                    institution_type = InstitutionType.SECONDARY
                elif 'Primary' in school.school_type:
                    institution_type = InstitutionType.PRIMARY

            # Build details JSON
            details = {
                'brin_code': school.brin_code,
                'school_type': school.school_type,
                'education_structure': school.education_structure,
                'denomination': school.denomination,
                'student_count': school.student_count,
            }

            # Add CITO score if available
            if school.cito_score:
                details['cito_score'] = school.cito_score

            # Create new institution
            institution = EducationInstitution(
                institution_type=institution_type,
                name=school.name,
                city=school.city,
                address=school.address,
                postal_code=school.postal_code,
                latitude=school.latitude,
                longitude=school.longitude,
                phone=school.phone,
                email=school.email,
                website=school.website,
                rating=school.inspection_score,
                rating_source='Inspectorate of Education',
                rating_label=school.inspection_rating,
                is_bilingual=school.is_bilingual or False,
                is_international=school.is_international or False,
                offers_english=school.offers_english or False,
                details=details,
                description=school.description
            )

            if dry_run:
                print(f"  ✓ Would migrate: {school.name} ({school.city})")
            else:
                db.add(institution)
                migrated_count += 1

        except Exception as e:
            error_count += 1
            print(f"  ❌ Error migrating {school.name}: {e}")

    if not dry_run:
        db.commit()
        print(f"\n✅ Migration complete!")
        print(f"   Migrated: {migrated_count}")
        print(f"   Errors: {error_count}")
    else:
        print(f"\n🔍 DRY RUN - No changes made")
        print(f"   Would migrate: {migrated_count}")
        print(f"   Potential errors: {error_count}")


def create_institutions_table():
    """Create the education_institutions table"""
    print("\n📦 Creating education_institutions table...")
    from app.education_institution import EducationInstitution
    Base.metadata.create_all(bind=engine, tables=[EducationInstitution.__table__])
    print("✅ Table created successfully")


def rollback_migration(db: Session):
    """
    Rollback migration by dropping education_institutions table

    WARNING: This will delete all data in education_institutions table!
    """
    print("\n⚠️  ROLLBACK: This will DELETE the education_institutions table")
    print("   The schools table will remain unchanged")

    response = input("Are you sure? Type 'DELETE' to confirm: ")
    if response != 'DELETE':
        print("❌ Rollback cancelled")
        return

    # Drop the table
    EducationInstitution.__table__.drop(engine)
    print("✅ education_institutions table dropped")


def main():
    """Main migration entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate schools to unified education institution model')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without committing')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration (delete education_institutions)')
    args = parser.parse_args()

    db = SessionLocal()

    try:
        if args.rollback:
            rollback_migration(db)
        else:
            # Create table if it doesn't exist
            create_institutions_table()

            # Run migration
            migrate_schools_to_institutions(db, dry_run=args.dry_run)

            if not args.dry_run:
                print("\n📝 Next steps:")
                print("   1. Update API endpoints to use EducationInstitution model")
                print("   2. Update frontend TypeScript types")
                print("   3. Test the application thoroughly")
                print("   4. Once verified, you can safely drop the schools table")
                print("      (Keep it for now as a backup)")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
