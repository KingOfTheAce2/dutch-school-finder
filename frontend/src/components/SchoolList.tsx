import './SchoolList.css';
import { School } from '../types';

interface SchoolListProps {
  schools: School[];
  onSelectSchool: (school: School) => void;
}

const SchoolList = ({ schools, onSelectSchool }: SchoolListProps) => {
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

  if (schools.length === 0) {
    return (
      <div className="school-list-empty">
        <div className="empty-state">
          <span className="empty-icon">🏫</span>
          <h3>No schools found</h3>
          <p>Try adjusting your search filters to find more schools.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="school-list">
      <div className="school-list-header">
        <h2>Found {schools.length} school{schools.length !== 1 ? 's' : ''}</h2>
      </div>

      <div className="school-list-content">
        {schools.map((school) => (
          <div
            key={school.id}
            className="school-card"
            onClick={() => onSelectSchool(school)}
          >
            <div className="school-card-header">
              <h3>{school.name}</h3>
              {school.inspection_score && (
                <div
                  className="rating-badge"
                  style={{ backgroundColor: getRatingColor(school.inspection_score) }}
                >
                  {school.inspection_score.toFixed(1)}
                </div>
              )}
            </div>

            <div className="school-card-info">
              <p className="school-location">
                📍 {school.city}
                {school.address && `, ${school.address}`}
              </p>

              {school.school_type && (
                <p className="school-type">
                  <strong>Type:</strong> {school.school_type}
                  {school.education_structure && ` (${school.education_structure})`}
                </p>
              )}

              {school.inspection_score && (
                <p className="school-rating">
                  <strong>Quality:</strong>{' '}
                  <span style={{ color: getRatingColor(school.inspection_score) }}>
                    {getRatingLabel(school.inspection_score)}
                  </span>
                </p>
              )}

              {school.student_count && (
                <p className="school-students">
                  <strong>Students:</strong> {school.student_count}
                </p>
              )}
            </div>

            <div className="school-card-badges">
              {school.is_international && (
                <span className="badge badge-international">🌍 International</span>
              )}
              {school.is_bilingual && (
                <span className="badge badge-bilingual">🌐 Bilingual</span>
              )}
              {school.offers_english && !school.is_international && !school.is_bilingual && (
                <span className="badge badge-english">🇬🇧 English Available</span>
              )}
            </div>

            {school.description && (
              <p className="school-description">{school.description}</p>
            )}

            <button className="view-details-btn">
              View Full Details →
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SchoolList;
