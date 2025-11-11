import { useTranslation } from 'react-i18next';
import './Header.css';
import LanguageSwitcher from './LanguageSwitcher';

const Header = () => {
  const { t } = useTranslation();

  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <span className="logo-icon">🏫</span>
          <h1>{t('header.title')}</h1>
        </div>
        <p className="tagline">
          {t('header.tagline')}
        </p>
      </div>
      <div className="header-info">
        <LanguageSwitcher />
        <span className="info-badge">👨‍👩‍👧‍👦 {t('header.expatFriendly')}</span>
      </div>
    </header>
  );
};

export default Header;
