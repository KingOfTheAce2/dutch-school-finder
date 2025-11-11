import { useTranslation } from 'react-i18next';
import './LanguageSwitcher.css';

const LanguageSwitcher = () => {
  const { i18n } = useTranslation();

  const languages = [
    { code: 'en', name: 'English', flag: '🇬🇧' },
    { code: 'nl', name: 'Nederlands', flag: '🇳🇱' },
  ];

  const changeLanguage = (langCode: string) => {
    i18n.changeLanguage(langCode);
    localStorage.setItem('language', langCode);
  };

  return (
    <div className="language-switcher">
      {languages.map((lang) => (
        <button
          key={lang.code}
          className={`lang-button ${i18n.language === lang.code ? 'active' : ''}`}
          onClick={() => changeLanguage(lang.code)}
          title={lang.name}
        >
          <span className="flag">{lang.flag}</span>
          <span className="lang-name">{lang.name}</span>
        </button>
      ))}
    </div>
  );
};

export default LanguageSwitcher;
