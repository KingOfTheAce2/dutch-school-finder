import './SchoolDetail.css';
import { School } from '../types';

interface SchoolDetailProps {
  school: School;
  onClose: () => void;
}

const SchoolDetail = ({ school, onClose }: SchoolDetailProps) => {
  const getRatingColor = (score?: number) => {
    if (!score) return '#gray';
    if (score >= 9) return '#10b981';
    if (score >= 7.5) return '#3b82f6';
    if (score >= 6) return '#f59e0b';
    return '#ef4444';
  };

  const getRatingLabel = (score?: number) => {
    if (!score) return 'Not Rated';
    if (score >= 9) return 'Excellent';
    if (score >= 7.5) return 'Good';
    if (score >= 6) return 'Satisfactory';
    return 'Needs Improvement';
  };

  return (
    <>
      <div className="school-detail-overlay" onClick={onClose} />
      <div className="school-detail-panel">
        <button className="close-button" onClick={onClose}>
          ✕
        </button>

        <div className="school-detail-content">
          {/* Header */}
          <div className="detail-header">
            <h2>{school.name}</h2>
            {school.inspection_score && (
              <div
                className="detail-rating"
                style={{ backgroundColor: getRatingColor(school.inspection_score) }}
              >
                <div className="rating-score">{school.inspection_score.toFixed(1)}</div>
                <div className="rating-label">{getRatingLabel(school.inspection_score)}</div>
              </div>
            )}
          </div>

          {/* Badges */}
          <div className="detail-badges">
            {school.is_international && (
              <span className="badge badge-international">🌍 International School</span>
            )}
            {school.is_bilingual && (
              <span className="badge badge-bilingual">🌐 Bilingual Program</span>
            )}
            {school.offers_english && !school.is_international && !school.is_bilingual && (
              <span className="badge badge-english">🇬🇧 English Available</span>
            )}
          </div>

          {/* Description */}
          {school.description && (
            <div className="detail-section">
              <p className="description-text">{school.description}</p>
            </div>
          )}

          {/* Basic Information */}
          <div className="detail-section">
            <h3>📍 Location</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">City:</span>
                <span className="info-value">{school.city}</span>
              </div>
              {school.address && (
                <div className="info-item">
                  <span className="info-label">Address:</span>
                  <span className="info-value">{school.address}</span>
                </div>
              )}
              {school.postal_code && (
                <div className="info-item">
                  <span className="info-label">Postal Code:</span>
                  <span className="info-value">{school.postal_code}</span>
                </div>
              )}
            </div>
          </div>

          {/* School Information */}
          <div className="detail-section">
            <h3>🏫 School Information</h3>
            <div className="info-grid">
              {school.school_type && (
                <div className="info-item">
                  <span className="info-label">Type:</span>
                  <span className="info-value">{school.school_type}</span>
                </div>
              )}
              {school.education_structure && (
                <div className="info-item">
                  <span className="info-label">Education Level:</span>
                  <span className="info-value">{school.education_structure}</span>
                </div>
              )}
              {school.denomination && (
                <div className="info-item">
                  <span className="info-label">Denomination:</span>
                  <span className="info-value">{school.denomination}</span>
                </div>
              )}
              {school.student_count && (
                <div className="info-item">
                  <span className="info-label">Number of Students:</span>
                  <span className="info-value">{school.student_count}</span>
                </div>
              )}
              {school.brin_code && (
                <div className="info-item">
                  <span className="info-label">BRIN Code:</span>
                  <span className="info-value">{school.brin_code}</span>
                </div>
              )}
            </div>
          </div>

          {/* Quality Indicators */}
          <div className="detail-section">
            <h3>⭐ Quality Indicators</h3>
            <div className="info-grid">
              {school.inspection_rating && (
                <div className="info-item">
                  <span className="info-label">Inspection Rating:</span>
                  <span className="info-value">{school.inspection_rating}</span>
                </div>
              )}
              {school.inspection_score && (
                <div className="info-item">
                  <span className="info-label">Inspection Score:</span>
                  <span
                    className="info-value"
                    style={{ color: getRatingColor(school.inspection_score), fontWeight: 600 }}
                  >
                    {school.inspection_score.toFixed(1)} / 10
                  </span>
                </div>
              )}
              {school.cito_score && (
                <div className="info-item">
                  <span className="info-label">CITO Score:</span>
                  <span className="info-value">{school.cito_score}</span>
                </div>
              )}
            </div>

            {school.school_type === 'Primary' && school.cito_score && (
              <div className="info-note">
                <strong>About CITO:</strong> The CITO test is taken by Dutch primary school students
                in their final year. Average score is around 535. Higher scores indicate better
                academic performance.
              </div>
            )}
          </div>

          {/* Contact Information */}
          <div className="detail-section">
            <h3>📞 Contact Information</h3>
            <div className="info-grid">
              {school.phone && (
                <div className="info-item">
                  <span className="info-label">Phone:</span>
                  <a href={`tel:${school.phone}`} className="info-link">
                    {school.phone}
                  </a>
                </div>
              )}
              {school.email && (
                <div className="info-item">
                  <span className="info-label">Email:</span>
                  <a href={`mailto:${school.email}`} className="info-link">
                    {school.email}
                  </a>
                </div>
              )}
              {school.website && (
                <div className="info-item">
                  <span className="info-label">Website:</span>
                  <a
                    href={school.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="info-link"
                  >
                    Visit Website →
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="detail-actions">
            {school.latitude && school.longitude && (
              <a
                href={`https://www.google.com/maps/search/?api=1&query=${school.latitude},${school.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="action-button primary"
              >
                🗺️ View on Google Maps
              </a>
            )}
            {school.website && (
              <a
                href={school.website}
                target="_blank"
                rel="noopener noreferrer"
                className="action-button secondary"
              >
                🌐 Visit School Website
              </a>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default SchoolDetail;
