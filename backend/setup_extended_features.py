#!/usr/bin/env python3
"""
Setup script for extended features
Initializes database and generates sample data
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db, SessionLocal
from app.data_fetcher import fetch_and_store_schools
from app.sample_data_generator import generate_all_sample_data
import asyncio

def main():
    print("\n" + "="*70)
    print("DUTCH SCHOOL FINDER - EXTENDED FEATURES SETUP")
    print("="*70 + "\n")

    # Initialize database
    print("Step 1: Initializing database schema...")
    init_db()
    print("✓ Database schema initialized\n")

    # Check if schools exist
    db = SessionLocal()
    try:
        from app.crud import get_school_count
        count = get_school_count(db)

        if count == 0:
            print("Step 2: Fetching and storing school data...")
            print("This may take a few minutes...\n")
            asyncio.run(fetch_and_store_schools())
            print("✓ School data loaded\n")
        else:
            print(f"Step 2: School data already exists ({count} schools)\n")

    finally:
        db.close()

    # Generate sample data for extended features
    print("Step 3: Generating sample data for extended features...")
    generate_all_sample_data()

    print("\n" + "="*70)
    print("✓ SETUP COMPLETE!")
    print("="*70)
    print("\nYou can now start the API server:")
    print("  cd backend")
    print("  uvicorn app.main:app --reload")
    print("\nAPI Documentation: http://localhost:8000/docs")
    print("Extended Features: http://localhost:8000/api/*")
    print("\n")

if __name__ == "__main__":
    main()
