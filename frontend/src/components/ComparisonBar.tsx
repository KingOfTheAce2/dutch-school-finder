import { useEffect, useState } from 'react';
import { School } from '../types';
import { useTranslation } from 'react-i18next';
import './ComparisonBar.css';

interface ComparisonBarProps {
  selectedSchools: School[];
  onRemove: (schoolId: number) => void;
  onCompare: () => void;
  onClear: () => void;
}

const ComparisonBar = ({ selectedSchools, onRemove, onCompare, onClear }: ComparisonBarProps) => {
  const { t } = useTranslation();
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Show bar when schools are selected
    setIsVisible(selectedSchools.length > 0);
  }, [selectedSchools]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className="comparison-bar">
      <div className="comparison-bar-content">
        <div className="comparison-header">
          <h3>
            {t('comparison.selected', { count: selectedSchools.length })}
          </h3>
          <button
            className="clear-button"
            onClick={onClear}
            title={t('comparison.clearAll')}
          >
            ✕ {t('comparison.clearAll')}
          </button>
        </div>

        <div className="selected-schools">
          {selectedSchools.map((school) => (
            <div key={school.id} className="selected-school-card">
              <button
                className="remove-button"
                onClick={() => onRemove(school.id)}
                title={t('comparison.remove')}
              >
                ✕
              </button>
              <div className="school-info">
                <div className="school-name">{school.name}</div>
                <div className="school-city">{school.city}</div>
              </div>
            </div>
          ))}

          {/* Empty slots to show max capacity */}
          {[...Array(Math.max(0, 5 - selectedSchools.length))].map((_, idx) => (
            <div key={`empty-${idx}`} className="selected-school-card empty">
              <div className="empty-slot">+</div>
            </div>
          ))}
        </div>

        <div className="comparison-actions">
          <div className="comparison-hint">
            {selectedSchools.length < 2 ? (
              <span className="hint-text">
                {t('comparison.selectAtLeast', { count: 2 - selectedSchools.length })}
              </span>
            ) : (
              <span className="hint-text success">
                ✓ {t('comparison.readyToCompare')}
              </span>
            )}
          </div>
          <button
            className="compare-button"
            onClick={onCompare}
            disabled={selectedSchools.length < 2}
          >
            {t('comparison.compareButton')} ({selectedSchools.length})
          </button>
        </div>
      </div>
    </div>
  );
};

export default ComparisonBar;
