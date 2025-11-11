import { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import SearchPanel from './components/SearchPanel';
import SchoolMap from './components/SchoolMap';
import SchoolList from './components/SchoolList';
import SchoolDetail from './components/SchoolDetail';
import ComparisonBar from './components/ComparisonBar';
import ComparisonTable from './components/ComparisonTable';
import { School, SearchFilters } from './types';
import { schoolAPI } from './api';

function App() {
  const [schools, setSchools] = useState<School[]>([]);
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
  const [filters, setFilters] = useState<SearchFilters>({});

  // Comparison state
  const [selectedForComparison, setSelectedForComparison] = useState<number[]>([]);
  const [showComparison, setShowComparison] = useState(false);

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

  // Comparison handlers
  const handleToggleComparison = (schoolId: number) => {
    setSelectedForComparison((prev) => {
      if (prev.includes(schoolId)) {
        // Remove from comparison
        return prev.filter((id) => id !== schoolId);
      } else {
        // Add to comparison (max 5)
        if (prev.length >= 5) {
          alert('You can compare a maximum of 5 schools');
          return prev;
        }
        return [...prev, schoolId];
      }
    });
  };

  const handleRemoveFromComparison = (schoolId: number) => {
    setSelectedForComparison((prev) => prev.filter((id) => id !== schoolId));
  };

  const handleClearComparison = () => {
    setSelectedForComparison([]);
    setShowComparison(false);
  };

  const handleShowComparison = () => {
    if (selectedForComparison.length >= 2) {
      setShowComparison(true);
    }
  };

  const handleCloseComparison = () => {
    setShowComparison(false);
  };

  // Get selected schools for comparison bar
  const getSelectedSchools = (): School[] => {
    return schools.filter((school) => selectedForComparison.includes(school.id));
  };

  // Load selected schools from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('comparison');
    if (saved) {
      try {
        const ids = JSON.parse(saved);
        if (Array.isArray(ids)) {
          setSelectedForComparison(ids);
        }
      } catch (e) {
        console.error('Failed to load comparison from localStorage', e);
      }
    }
  }, []);

  // Save selected schools to localStorage
  useEffect(() => {
    localStorage.setItem('comparison', JSON.stringify(selectedForComparison));
  }, [selectedForComparison]);

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
                  selectedForComparison={selectedForComparison}
                  onToggleComparison={handleToggleComparison}
                />
              )}
            </>
          )}
        </div>
      </div>

      {/* School Detail Modal */}
      {selectedSchool && (
        <SchoolDetail
          school={selectedSchool}
          onClose={handleCloseDetail}
        />
      )}

      {/* Comparison Bar */}
      <ComparisonBar
        selectedSchools={getSelectedSchools()}
        onRemove={handleRemoveFromComparison}
        onCompare={handleShowComparison}
        onClear={handleClearComparison}
      />

      {/* Comparison Table Modal */}
      {showComparison && (
        <ComparisonTable
          schoolIds={selectedForComparison}
          onClose={handleCloseComparison}
        />
      )}
    </div>
  );
}

export default App;
