import { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import SearchPanel from './components/SearchPanel';
import SchoolMap from './components/SchoolMap';
import SchoolList from './components/SchoolList';
import SchoolDetail from './components/SchoolDetail';
import { School, SearchFilters } from './types';
import { schoolAPI } from './api';

function App() {
  const [schools, setSchools] = useState<School[]>([]);
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
  const [filters, setFilters] = useState<SearchFilters>({});

  // Load initial schools
  useEffect(() => {
    loadSchools();
  }, []);

  const loadSchools = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await schoolAPI.getSchools(500); // Load more schools for better map view
      setSchools(data);
    } catch (err) {
      console.error('Error loading schools:', err);
      setError('Failed to load schools. Please make sure the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (newFilters: SearchFilters) => {
    try {
      setLoading(true);
      setError(null);
      setFilters(newFilters);

      // If no filters, load all schools
      const hasFilters = Object.values(newFilters).some(v => v !== undefined && v !== '');

      if (!hasFilters) {
        await loadSchools();
        return;
      }

      // Check if this is a proximity search
      if (newFilters.address && newFilters.radius_km) {
        const data = await schoolAPI.searchNearbySchools(
          newFilters.address,
          newFilters.radius_km,
          newFilters
        );
        setSchools(data);
      } else {
        // Regular search
        const data = await schoolAPI.searchSchools(newFilters);
        setSchools(data);
      }
    } catch (err: any) {
      console.error('Error searching schools:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to search schools. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSchool = (school: School) => {
    setSelectedSchool(school);
  };

  const handleCloseDetail = () => {
    setSelectedSchool(null);
  };

  return (
    <div className="app">
      <Header />

      <div className="main-content">
        <SearchPanel
          onSearch={handleSearch}
          loading={loading}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />

        <div className="content-area">
          {error && (
            <div className="error-banner">
              <p>{error}</p>
              <button onClick={loadSchools}>Retry</button>
            </div>
          )}

          {loading && !error && (
            <div className="loading-overlay">
              <div className="loading-spinner"></div>
              <p>Loading schools...</p>
            </div>
          )}

          {!loading && !error && (
            <>
              {viewMode === 'map' ? (
                <SchoolMap
                  schools={schools}
                  selectedSchool={selectedSchool}
                  onSelectSchool={handleSelectSchool}
                />
              ) : (
                <SchoolList
                  schools={schools}
                  onSelectSchool={handleSelectSchool}
                />
              )}
            </>
          )}
        </div>
      </div>

      {selectedSchool && (
        <SchoolDetail
          school={selectedSchool}
          onClose={handleCloseDetail}
        />
      )}
    </div>
  );
}

export default App;
