# Data Ingestion Scripts

This directory contains scripts for ingesting REAL education data from official Dutch government sources.

## 🎯 Overview

All scripts use **official open data** from DUO (Dienst Uitvoering Onderwijs) and other government sources:

- **License**: CC-0 (1.0) - Public Domain
- **Update Frequency**: Monthly
- **Coverage**: Complete Netherlands

## 📥 Available Scripts

### 1. Primary & Secondary Schools (COMPLETE)
**Script**: `ingest_duo_data.py`
**Data Source**: Existing DUO data
**Coverage**: ~7,150 schools across 20 major cities
**Status**: ✅ Already implemented and populated

```bash
python -m scripts.ingest_duo_data
```

### 2. MBO (Vocational Education)
**Script**: `ingest_mbo_data.py`
**Data Source**: https://www.duo.nl/open_onderwijsdata/databestanden/mbo/adressen/
**Coverage**: ~70 MBO institutions nationwide
**Status**: ✅ Script ready

```bash
# Dry run (preview data)
python -m scripts.ingest_mbo_data --dry-run

# Full ingestion with geocoding
python -m scripts.ingest_mbo_data

# Without geocoding (faster)
python -m scripts.ingest_mbo_data --no-geocode

# Explicit URL
python -m scripts.ingest_mbo_data --url "https://duo.nl/..."
```

### 3. HBO & Universities (Higher Education)
**Script**: `ingest_hbo_university_data.py`
**Data Source**: https://www.duo.nl/open_onderwijsdata/databestanden/ho/adressen/
**Coverage**: ~37 HBO + 14 universities
**Status**: ✅ Script ready

```bash
# Dry run
python -m scripts.ingest_hbo_university_data --dry-run

# Full ingestion
python -m scripts.ingest_hbo_university_data

# Without geocoding
python -m scripts.ingest_hbo_university_data --no-geocode
```

### 4. Childcare (Kinderopvang)
**Script**: `ingest_childcare_lrk.py`
**Data Source**: LRK (Landelijk Register Kinderopvang)
**Coverage**: ~10,000 childcare centers
**Status**: ⚠️ Template - requires website analysis

```bash
# IMPORTANT: Read the script comments first!
# This is a template that needs to be customized

python -m scripts.ingest_childcare_lrk --city Amsterdam --max-results 100 --dry-run
```

**Note**: The LRK registry requires web scraping. Before running:
1. Visit https://www.landelijkregisterkinderopvang.nl/
2. Analyze the search interface and HTML structure
3. Update the parsing logic in the script
4. Check robots.txt and respect rate limits

## 🔄 Database Migration

### Migrate to Unified Model
**Script**: `migrate_to_unified_model.py`
**Purpose**: Migrate existing School table to new EducationInstitution model

```bash
# Dry run (see what would be migrated)
python -m scripts.migrate_to_unified_model --dry-run

# Run migration
python -m scripts.migrate_to_unified_model

# Rollback (delete education_institutions table)
python -m scripts.migrate_to_unified_model --rollback
```

**⚠️ Important**: This creates a new `education_institutions` table. The old `schools` table is kept as backup.

## 🗂️ Data Model

All education data is stored in the unified `EducationInstitution` model:

```python
{
    "institution_type": "childcare" | "primary" | "secondary" | "mbo" | "hbo" | "university",
    "name": str,
    "city": str,
    "address": str,
    "postal_code": str,
    "latitude": float,
    "longitude": float,
    "phone": str,
    "email": str,
    "website": str,
    "rating": float,  # 0-10 scale
    "rating_source": str,  # "Inspectorate", "GGD", "DUO"
    "is_bilingual": bool,
    "is_international": bool,
    "offers_english": bool,
    "details": {
        # Type-specific fields in JSON
        # For schools: brin_code, cito_score, denomination, etc.
        # For MBO: programs, levels
        # For HBO/Uni: programs, english_programs, student_count
        # For childcare: lrk_number, capacity, age_group, type
    }
}
```

## 🚀 Recommended Workflow

### Initial Setup
```bash
# 1. Migrate existing schools (if not done already)
python -m scripts.migrate_to_unified_model

# 2. Ingest MBO data
python -m scripts.ingest_mbo_data

# 3. Ingest HBO and university data
python -m scripts.ingest_hbo_university_data

# 4. Ingest childcare data (after customizing the script)
python -m scripts.ingest_childcare_lrk --city Amsterdam --max-results 400
```

### Monthly Updates
DUO data is updated monthly. Re-run ingestion scripts monthly to keep data fresh:

```bash
# Update MBO
python -m scripts.ingest_mbo_data

# Update HBO/Universities
python -m scripts.ingest_hbo_university_data
```

## 📊 Expected Data Volumes

| Type | Count | Source |
|------|-------|--------|
| Primary Schools | ~6,800 | DUO (existing) |
| Secondary Schools | ~350 | DUO (existing) |
| MBO Institutions | ~70 | DUO Open Data |
| HBO Institutions | ~37 | DUO Open Data |
| Universities | ~14 | DUO Open Data |
| Childcare Centers | ~10,000 | LRK Registry |
| **Total** | **~17,271** | **Official sources** |

## 🔍 Data Quality

### Geocoding
- All scripts support optional geocoding (lat/lon for map view)
- Uses OpenStreetMap Nominatim (free, no API key required)
- Rate limited to 1 request/second
- Can skip geocoding with `--no-geocode` flag (faster)

### Validation
- Duplicate detection by BRIN code or LRK number
- Skips entries without required fields (name, city)
- Error handling with detailed logging

### Updates
- Existing records are updated (not duplicated)
- New records are added
- Timestamps track creation and updates

## 📖 Data Sources Documentation

### DUO Open Data
- **Portal**: https://duo.nl/open_onderwijsdata/
- **License**: CC-0 (public domain)
- **Format**: CSV (semicolon-delimited)
- **Encoding**: UTF-8
- **Update**: Monthly

### LRK Registry
- **Website**: https://www.landelijkregisterkinderopvang.nl/
- **Authority**: GGD (Municipal Health Service)
- **Purpose**: Legal registry for all childcare providers
- **Access**: Public search interface (requires scraping)

## ⚠️ Legal & Ethical Considerations

### ✅ Compliant
- Public data only
- Proper attribution
- Respects robots.txt
- Rate limiting
- Non-commercial educational use

### ❌ Not Allowed
- Personal data collection
- Login bypass
- Rate limit violations
- Commercial resale

## 🛠️ Troubleshooting

### "Could not auto-detect latest CSV"
- Visit the DUO data portal manually
- Find the latest CSV file name
- Use `--url` flag with explicit URL

### "Geocoding failed"
- Check internet connection
- Nominatim might be rate limiting (wait and retry)
- Use `--no-geocode` to skip geocoding

### "Duplicate key error"
- Data already exists in database
- Script will skip duplicates automatically
- Use `--dry-run` to preview without storing

## 📞 Support

For issues or questions:
1. Check script comments for detailed instructions
2. Review the IMPLEMENTATION_PLAN.md for strategy
3. Consult DUO documentation: https://duo.nl/open_onderwijsdata/

## 🎉 Next Steps

After ingestion:
1. Update API endpoints to support all institution types
2. Update frontend filters (add MBO, HBO, University options)
3. Test proximity search with new data
4. Verify data quality on production

---

**Last Updated**: 2025-11-11
**Status**: MBO/HBO/University ready | Childcare template | Schools complete
