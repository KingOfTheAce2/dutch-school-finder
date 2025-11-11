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

    if (city) filters.city = city;
    if (schoolType) filters.school_type = schoolType;
    if (name) filters.name = name;
    if (minRating) filters.min_rating = parseFloat(minRating);
    if (bilingual) filters.bilingual = true;
    if (international) filters.international = true;

    onSearch(filters);
  };

  const handleReset = () => {
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
            disabled={loading}
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
        <h3>💡 Tip for Expat Families</h3>
        <p>
          Looking for English-language education? Use the "International" or "Bilingual" filters
          to find schools that offer instruction in English.
        </p>
        <ul>
          <li><strong>International:</strong> Full English curriculum</li>
          <li><strong>Bilingual:</strong> Dutch + English programs</li>
        </ul>
      </div>
    </div>
  );
};

export default SearchPanel;
