import { useEffect, useState } from 'react';
import { School } from '../types';
import { schoolAPI } from '../api';
import { useTranslation } from 'react-i18next';
import './ComparisonTable.css';

interface ComparisonTableProps {
  schoolIds: number[];
  onClose: () => void;
}

const ComparisonTable = ({ schoolIds, onClose }: ComparisonTableProps) => {
  const { t } = useTranslation();
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSchools = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await schoolAPI.compareSchools(schoolIds);
        setSchools(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Failed to load schools');
      } finally {
        setLoading(false);
      }
    };

    if (schoolIds.length >= 2) {
      fetchSchools();
    }
  }, [schoolIds]);

  if (loading) {
    return (
      <div className="comparison-overlay">
        <div className="comparison-container">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>{t('comparison.loading')}</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="comparison-overlay">
        <div className="comparison-container">
          <button className="close-button" onClick={onClose}>
            ✕
          </button>
          <div className="error-state">
            <h2>{t('comparison.error')}</h2>
            <p>{error}</p>
            <button className="primary-button" onClick={onClose}>
              {t('comparison.goBack')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const comparisonRows = [
    {
      label: t('comparison.schoolName'),
      getValue: (school: School) => school.name,
      className: 'school-name-cell',
    },
    {
      label: t('comparison.city'),
      getValue: (school: School) => school.city,
      icon: '📍',
    },
    {
      label: t('comparison.schoolType'),
      getValue: (school: School) => school.school_type || '-',
    },
    {
      label: t('comparison.rating'),
      getValue: (school: School) =>
        school.inspection_score ? `${school.inspection_score}/10` : t('comparison.notAvailable'),
      className: 'rating-cell',
      highlight: true,
    },
    {
      label: t('comparison.students'),
      getValue: (school: School) => school.student_count?.toString() || '-',
      icon: '👥',
    },
    {
      label: t('comparison.denomination'),
      getValue: (school: School) => school.denomination || '-',
    },
    {
      label: t('comparison.structure'),
      getValue: (school: School) => school.education_structure || '-',
    },
    {
      label: t('comparison.bilingual'),
      getValue: (school: School) => (school.is_bilingual ? '✓ Yes' : '✗ No'),
      className: school => (school.is_bilingual ? 'positive' : 'neutral'),
    },
    {
      label: t('comparison.international'),
      getValue: (school: School) => (school.is_international ? '✓ Yes' : '✗ No'),
      className: school => (school.is_international ? 'positive' : 'neutral'),
    },
    {
      label: t('comparison.englishProgram'),
      getValue: (school: School) => (school.offers_english ? '✓ Yes' : '✗ No'),
      className: school => (school.offers_english ? 'positive' : 'neutral'),
    },
    {
      label: t('comparison.address'),
      getValue: (school: School) => `${school.address || '-'}, ${school.postal_code || ''}`,
      icon: '🏠',
    },
    {
      label: t('comparison.phone'),
      getValue: (school: School) => school.phone || '-',
      icon: '📞',
    },
    {
      label: t('comparison.email'),
      getValue: (school: School) => school.email || '-',
      icon: '📧',
    },
    {
      label: t('comparison.website'),
      getValue: (school: School) =>
        school.website ? (
          <a href={school.website} target="_blank" rel="noopener noreferrer" className="website-link">
            {t('comparison.visitWebsite')} →
          </a>
        ) : (
          '-'
        ),
    },
  ];

  return (
    <div className="comparison-overlay">
      <div className="comparison-container">
        <div className="comparison-header-bar">
          <h2>{t('comparison.title')}</h2>
          <button className="close-button" onClick={onClose} title={t('comparison.close')}>
            ✕
          </button>
        </div>

        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th className="row-label-header"></th>
                {schools.map((school) => (
                  <th key={school.id} className="school-header">
                    <div className="school-header-content">
                      <div className="school-header-name">{school.name}</div>
                      <div className="school-header-location">📍 {school.city}</div>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparisonRows.map((row, idx) => (
                <tr key={idx} className={row.highlight ? 'highlight-row' : ''}>
                  <td className="row-label">
                    {row.icon && <span className="row-icon">{row.icon}</span>}
                    {row.label}
                  </td>
                  {schools.map((school) => {
                    const value = row.getValue(school);
                    const cellClassName =
                      typeof row.className === 'function'
                        ? row.className(school)
                        : row.className || '';
                    return (
                      <td key={school.id} className={cellClassName}>
                        {value}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="comparison-footer">
          <button className="secondary-button" onClick={onClose}>
            {t('comparison.goBack')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ComparisonTable;
