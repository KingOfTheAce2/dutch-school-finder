import { useState, useEffect } from 'react';
import './SearchPanel.css';
import { SearchFilters } from '../types';
import { schoolAPI } from '../api';

interface SearchPanelProps {
  onSearch: (filters: SearchFilters) => void;
  loading: boolean;
  viewMode: 'map' | 'list';
  onViewModeChange: (mode: 'map' | 'list') => void;
}

const SearchPanel = ({ onSearch, loading, viewMode, onViewModeChange }: SearchPanelProps) => {
  // Proximity search
  const [address, setAddress] = useState('');
  const [radiusKm, setRadiusKm] = useState(5);
  const [useProximity, setUseProximity] = useState(false);

  // Regular search filters
  const [city, setCity] = useState('');
  const [schoolType, setSchoolType] = useState('');
  const [name, setName] = useState('');
  const [minRating, setMinRating] = useState<string>('');
  const [bilingual, setBilingual] = useState(false);
  const [international, setInternational] = useState(false);

  const [cities, setCities] = useState<string[]>([]);
  const [schoolTypes, setSchoolTypes] = useState<string[]>([]);

  useEffect(() => {
    loadFilterOptions();
  }, []);

  const loadFilterOptions = async () => {
    try {
      const [citiesData, typesData] = await Promise.all([
        schoolAPI.getCities(),
        schoolAPI.getSchoolTypes(),
      ]);
      setCities(citiesData);
      setSchoolTypes(typesData);
    } catch (err) {
      console.error('Error loading filter options:', err);
    }
  };

  const handleSearch = () => {
    const filters: SearchFilters = {};

    // Proximity search takes priority
    if (useProximity && address) {
      filters.address = address;
      filters.radius_km = radiusKm;
    } else {
      // Regular filters
      if (city) filters.city = city;
      if (name) filters.name = name;
    }

    // Common filters (work with both modes)
    if (schoolType) filters.school_type = schoolType;
    if (minRating) filters.min_rating = parseFloat(minRating);
    if (bilingual) filters.bilingual = true;
    if (international) filters.international = true;

    onSearch(filters);
  };

  const handleReset = () => {
    setAddress('');
    setRadiusKm(5);
    setUseProximity(false);
    setCity('');
    setSchoolType('');
    setName('');
    setMinRating('');
    setBilingual(false);
    setInternational(false);
    onSearch({});
  };

  return (
    <div className="search-panel">
      <div className="search-header">
        <h2>Search Schools</h2>
        <div className="view-toggle">
          <button
            className={viewMode === 'map' ? 'active' : ''}
            onClick={() => onViewModeChange('map')}
            title="Map View"
          >
            🗺️ Map
          </button>
          <button
            className={viewMode === 'list' ? 'active' : ''}
            onClick={() => onViewModeChange('list')}
            title="List View"
          >
            📋 List
          </button>
        </div>
      </div>

      <div className="search-form">
        {/* Search Mode Toggle */}
        <div className="form-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={useProximity}
              onChange={(e) => setUseProximity(e.target.checked)}
            />
            <span>📍 Search by Address (Proximity)</span>
          </label>
        </div>

        {/* Proximity Search */}
        {useProximity ? (
          <>
            <div className="form-group">
              <label htmlFor="address">Your Address</label>
              <input
                id="address"
                type="text"
                placeholder="e.g., Dam 1, Amsterdam"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
              />
              <small style={{ color: '#6b7280', fontSize: '12px', marginTop: '4px', display: 'block' }}>
                Enter address as: "Street, City" or just "City"
              </small>
            </div>

            <div className="form-group">
              <label htmlFor="radius">
                Search Radius: {radiusKm} km
              </label>
              <input
                id="radius"
                type="range"
                min="1"
                max="25"
                step="1"
                value={radiusKm}
                onChange={(e) => setRadiusKm(parseInt(e.target.value))}
                style={{ width: '100%' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#9ca3af' }}>
                <span>1 km</span>
                <span>25 km</span>
              </div>
            </div>
          </>
        ) : (
          <>
            {/* School Name */}
            <div className="form-group">
              <label htmlFor="name">School Name</label>
              <input
                id="name"
                type="text"
                placeholder="Search by name..."
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            {/* City Selection */}
            <div className="form-group">
              <label htmlFor="city">City</label>
              <select
                id="city"
                value={city}
                onChange={(e) => setCity(e.target.value)}
              >
                <option value="">All Cities</option>
                {cities.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </>
        )}

        {/* Common filters for both modes */}

        {/* School Type */}
        <div className="form-group">
          <label htmlFor="schoolType">School Type</label>
          <select
            id="schoolType"
            value={schoolType}
            onChange={(e) => setSchoolType(e.target.value)}
          >
            <option value="">All Types</option>
            {schoolTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>

        {/* Minimum Rating */}
        <div className="form-group">
          <label htmlFor="minRating">Minimum Rating</label>
          <select
            id="minRating"
            value={minRating}
            onChange={(e) => setMinRating(e.target.value)}
          >
            <option value="">Any Rating</option>
            <option value="9.0">Excellent (9.0+)</option>
            <option value="7.5">Good (7.5+)</option>
            <option value="6.0">Satisfactory (6.0+)</option>
            <option value="5.0">Adequate (5.0+)</option>
          </select>
        </div>

        {/* Expat-Friendly Filters */}
        <div className="form-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={bilingual}
              onChange={(e) => setBilingual(e.target.checked)}
            />
            <span>🌐 Bilingual Schools Only</span>
          </label>
        </div>

        <div className="form-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={international}
              onChange={(e) => setInternational(e.target.checked)}
            />
            <span>🌍 International Schools Only</span>
          </label>
        </div>

        {/* Action Buttons */}
        <div className="button-group">
          <button
            className="btn-primary"
            onClick={handleSearch}
            disabled={loading || (useProximity && !address)}
          >
            {loading ? 'Searching...' : '🔍 Search'}
          </button>
          <button
            className="btn-secondary"
            onClick={handleReset}
            disabled={loading}
          >
            Reset
          </button>
        </div>
      </div>

      {/* Info Box */}
      <div className="info-box">
        <h3>💡 {useProximity ? 'Proximity Search' : 'Tip for Expat Families'}</h3>
        {useProximity ? (
          <p>
            Find schools near your home or work address. Schools are sorted by distance,
            showing the closest schools first. This helps you find convenient options for your family.
          </p>
        ) : (
          <>
            <p>
              Looking for English-language education? Use the "International" or "Bilingual" filters
              to find schools that offer instruction in English.
            </p>
            <ul>
              <li><strong>International:</strong> Full English curriculum</li>
              <li><strong>Bilingual:</strong> Dutch + English programs</li>
            </ul>
          </>
        )}
      </div>
    </div>
  );
};

export default SearchPanel;
