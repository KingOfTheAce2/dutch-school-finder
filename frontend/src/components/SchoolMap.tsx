import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { useEffect } from 'react';
import L from 'leaflet';
import './SchoolMap.css';
import { School } from '../types';

// Fix for default marker icons in React-Leaflet
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
import iconRetina from 'leaflet/dist/images/marker-icon-2x.png';

// @ts-ignore
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: iconRetina,
  iconUrl: icon,
  shadowUrl: iconShadow,
});

// Custom icons for different school types
const createCustomIcon = (school: School) => {
  let color = '#2563eb'; // Default blue

  if (school.is_international) {
    color = '#10b981'; // Green for international
  } else if (school.is_bilingual) {
    color = '#f59e0b'; // Orange for bilingual
  }

  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="background-color: ${color}; width: 25px; height: 25px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
    iconSize: [25, 25],
    iconAnchor: [12, 12],
  });
};

interface SchoolMapProps {
  schools: School[];
  selectedSchool: School | null;
  onSelectSchool: (school: School) => void;
}

// Component to handle map centering
const MapController = ({ schools, selectedSchool }: { schools: School[], selectedSchool: School | null }) => {
  const map = useMap();

  useEffect(() => {
    if (selectedSchool && selectedSchool.latitude && selectedSchool.longitude) {
      map.flyTo([selectedSchool.latitude, selectedSchool.longitude], 13);
    } else if (schools.length > 0) {
      // Fit bounds to show all schools
      const validSchools = schools.filter(s => s.latitude && s.longitude);
      if (validSchools.length > 0) {
        const bounds = L.latLngBounds(
          validSchools.map(s => [s.latitude!, s.longitude!])
        );
        map.fitBounds(bounds, { padding: [50, 50] });
      }
    }
  }, [schools, selectedSchool, map]);

  return null;
};

const SchoolMap = ({ schools, selectedSchool, onSelectSchool }: SchoolMapProps) => {
  const defaultCenter: [number, number] = [52.3676, 4.9041]; // Amsterdam
  const defaultZoom = 8;

  // Filter schools with valid coordinates
  const validSchools = schools.filter(
    (school) => school.latitude && school.longitude
  );

  const getRatingColor = (score?: number) => {
    if (!score) return '#gray';
    if (score >= 9) return '#10b981'; // Green
    if (score >= 7.5) return '#3b82f6'; // Blue
    if (score >= 6) return '#f59e0b'; // Orange
    return '#ef4444'; // Red
  };

  const getRatingLabel = (score?: number) => {
    if (!score) return 'Not Rated';
    if (score >= 9) return 'Excellent';
    if (score >= 7.5) return 'Good';
    if (score >= 6) return 'Satisfactory';
    return 'Needs Improvement';
  };

  return (
    <div className="school-map-container">
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        className="school-map"
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapController schools={validSchools} selectedSchool={selectedSchool} />

        {validSchools.map((school) => (
          <Marker
            key={school.id}
            position={[school.latitude!, school.longitude!]}
            icon={createCustomIcon(school)}
            eventHandlers={{
              click: () => onSelectSchool(school),
            }}
          >
            <Popup>
              <div className="map-popup">
                <h3>{school.name}</h3>
                <p className="popup-city">📍 {school.city}</p>

                {school.school_type && (
                  <p className="popup-type">
                    <strong>Type:</strong> {school.school_type}
                  </p>
                )}

                {school.inspection_score && (
                  <p className="popup-rating">
                    <strong>Rating:</strong>{' '}
                    <span style={{ color: getRatingColor(school.inspection_score) }}>
                      {getRatingLabel(school.inspection_score)} ({school.inspection_score.toFixed(1)})
                    </span>
                  </p>
                )}

                <div className="popup-badges">
                  {school.is_international && (
                    <span className="badge badge-international">🌍 International</span>
                  )}
                  {school.is_bilingual && (
                    <span className="badge badge-bilingual">🌐 Bilingual</span>
                  )}
                </div>

                <button
                  className="popup-button"
                  onClick={() => onSelectSchool(school)}
                >
                  View Details
                </button>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Legend */}
      <div className="map-legend">
        <h4>School Types</h4>
        <div className="legend-item">
          <div className="legend-marker" style={{ backgroundColor: '#10b981' }}></div>
          <span>International</span>
        </div>
        <div className="legend-item">
          <div className="legend-marker" style={{ backgroundColor: '#f59e0b' }}></div>
          <span>Bilingual</span>
        </div>
        <div className="legend-item">
          <div className="legend-marker" style={{ backgroundColor: '#2563eb' }}></div>
          <span>Dutch</span>
        </div>
      </div>

      {schools.length === 0 && (
        <div className="map-overlay-message">
          <p>No schools found. Try adjusting your filters.</p>
        </div>
      )}
    </div>
  );
};

export default SchoolMap;
