import './Header.css';

const Header = () => {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <span className="logo-icon">🏫</span>
          <h1>Dutch School Finder</h1>
        </div>
        <p className="tagline">
          Find the perfect school for your family in the Netherlands
        </p>
      </div>
      <div className="header-info">
        <span className="info-badge">🌍 English</span>
        <span className="info-badge">👨‍👩‍👧‍👦 Expat-Friendly</span>
      </div>
    </header>
  );
};

export default Header;
