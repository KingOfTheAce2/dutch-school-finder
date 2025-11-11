# 🏫 Dutch School Finder

**Find the perfect school for your family in the Netherlands**

Dutch School Finder helps expat families discover, compare, and evaluate schools using open data from DUO and the Dutch Inspectorate of Education — all presented in English with an intuitive interface.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![React](https://img.shields.io/badge/react-18.2-blue.svg)
![TypeScript](https://img.shields.io/badge/typescript-5.0-blue.svg)

---

## ✨ Features

### For Expat Families
- 🌍 **English Interface** - Everything translated and explained for non-Dutch speakers
- 🎓 **International & Bilingual Schools** - Special filters to find English-language programs
- 📊 **Quality Ratings** - Understand Dutch inspection scores and CITO results
- 🗺️ **Interactive Map** - Visualize schools and explore by location
- 🔍 **Smart Search** - Filter by city, type, rating, language programs, and more

### Technical Features
- ⚡ **Fast & Responsive** - Modern React frontend with Vite
- 🔌 **RESTful API** - FastAPI backend with automatic documentation
- 🗄️ **Flexible Database** - SQLite for development, PostgreSQL for production
- 📱 **Mobile-Friendly** - Responsive design works on all devices
- 🚀 **Easy Deployment** - Ready for Vercel, Heroku, Railway, and more

---

## 🚀 Quick Start

### Prerequisites

- **Backend:** Python 3.9+, pip
- **Frontend:** Node.js 18+, npm
- **Database:** SQLite (included) or PostgreSQL (optional)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/dutch-school-finder.git
cd dutch-school-finder
```

### 2. Start the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at: http://localhost:8000
API docs: http://localhost:8000/docs

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:3000

### 4. Open in Browser

Navigate to http://localhost:3000 and start exploring schools!

---

## 📚 Documentation

- **[Backend README](backend/README.md)** - API documentation, database schema, development guide
- **[Frontend README](frontend/README.md)** - Component structure, styling, deployment
- **[Deployment Guide](DEPLOYMENT.md)** - Complete production deployment instructions
- **[Architecture Overview](ARCHITECTURE.md)** - System design and technical decisions

---

## 🏗️ Project Structure

```
dutch-school-finder/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI application & routes
│   │   ├── database.py     # SQLAlchemy models
│   │   ├── models.py       # Pydantic schemas
│   │   ├── crud.py         # Database operations
│   │   ├── data_fetcher.py # Data import logic
│   │   └── translations.py # Dutch-English translations
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/               # React + TypeScript frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── api.ts         # API client
│   │   ├── types.ts       # TypeScript definitions
│   │   └── App.tsx        # Main application
│   ├── package.json
│   ├── vite.config.ts
│   └── README.md
│
├── DEPLOYMENT.md          # Deployment guide
├── ARCHITECTURE.md        # Technical architecture
└── README.md             # This file
```

---

## 🎯 Use Cases

### For Expat Families
> "We just moved to Amsterdam with our two kids. Which schools offer English programs near our neighborhood?"

- Filter by city (Amsterdam)
- Enable "Bilingual" or "International" filter
- View on map to see proximity
- Compare quality ratings

### For School Research
> "I want to understand the Dutch education system and find the best primary school in Utrecht."

- Read education system explanations
- Filter for Primary schools in Utrecht
- Sort by inspection ratings
- View detailed information including CITO scores

### For Housing Decisions
> "We're deciding between The Hague and Rotterdam. Which city has better international schools?"

- Compare schools in both cities
- Filter for international schools
- View quality indicators
- Plan visits based on locations

---

## 🔌 API Endpoints

### Schools

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/schools` | List all schools (paginated) |
| GET | `/schools/{id}` | Get specific school details |
| GET | `/schools/search` | Search with filters |
| GET | `/cities` | List all cities |
| GET | `/types` | List school types |
| POST | `/admin/refresh-data` | Refresh school data |

**Example Request:**
```bash
curl "http://localhost:8000/schools/search?city=Amsterdam&bilingual=true&min_rating=7.5"
```

Full API documentation: http://localhost:8000/docs

---

## 🗄️ Database Schema

### School Model

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| name | String | School name |
| brin_code | String | Dutch school identifier (unique) |
| city | String | City location |
| school_type | String | Primary, Secondary, Special Education |
| education_structure | String | VMBO, HAVO, VWO, etc. |
| latitude, longitude | Float | Geographic coordinates |
| inspection_rating | String | Good, Excellent, etc. |
| inspection_score | Float | Numerical score (0-10) |
| cito_score | Float | CITO test score (primary schools) |
| is_bilingual | Boolean | Offers bilingual program |
| is_international | Boolean | International school |
| offers_english | Boolean | English instruction available |
| denomination | String | Religious affiliation |
| student_count | Integer | Number of students |

See [backend/README.md](backend/README.md) for complete schema.

---

## 🧪 Development

### Running Tests

**Backend:**
```bash
cd backend
pytest
```

**Frontend:**
```bash
cd frontend
npm test
```

### Code Quality

**Backend:**
```bash
black app/          # Format code
flake8 app/         # Lint code
mypy app/           # Type checking
```

**Frontend:**
```bash
npm run lint        # ESLint
npx tsc --noEmit    # Type checking
```

---

## 🌍 Data Sources

Dutch School Finder integrates with (or can integrate with):

1. **DUO Open Data** - Official Dutch education statistics
   - URL: https://opendata.duo.nl/
   - Contains: School registrations, basic info, student counts

2. **Scholen op de Kaart** - School quality and inspection data
   - URL: https://scholenopdekaart.nl/
   - Contains: Inspection ratings, quality indicators

3. **Dutch Inspectorate of Education** - Quality assessments
   - Official inspection reports and ratings

> **Note:** Current version uses generated sample data for demonstration.
> Production deployment should integrate real DUO/Inspectorate APIs.

---

## 📖 Understanding Dutch Education

### School Types

- **Primary (Basisschool)**: Ages 4-12, 8 years
- **Secondary (Voortgezet Onderwijs)**: Ages 12-16/18
  - **VMBO**: Pre-vocational (4 years)
  - **HAVO**: Higher general (5 years)
  - **VWO**: Pre-university (6 years)
- **Special Education**: For children with special needs

### Quality Indicators

- **Inspection Rating**: Excellent, Good, Satisfactory, Inadequate
- **Inspection Score**: 0-10 scale (7.5+ is good)
- **CITO Score**: National test for primary schools (~535 average)

### School Types for Expats

- **International Schools**: Full English curriculum (IB, British, American)
- **Bilingual Schools**: Dutch + English instruction
- **Public Schools**: May offer language support

See [translations.py](backend/app/translations.py) for complete terminology guide.

---

## 🚢 Deployment

### Quick Deploy Options

**Backend:**
- Heroku: `git push heroku main`
- Railway: Connect GitHub repo
- Render: Deploy from GitHub

**Frontend:**
- Vercel: `vercel --prod`
- Netlify: `netlify deploy --prod`
- GitHub Pages: Push to `gh-pages` branch

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

---

## 🛣️ Roadmap

### Phase 1: MVP (Current)
- [x] Backend API with school data
- [x] Frontend with map and list views
- [x] Search and filtering
- [x] Bilingual/International filters
- [x] Responsive design

### Phase 2: Enhanced Features
- [ ] Real-time DUO API integration
- [ ] User accounts and saved searches
- [ ] Favorite schools
- [ ] Share school via link
- [ ] Compare multiple schools side-by-side

### Phase 3: Advanced Features
- [ ] Housing integration (Funda, Pararius)
- [ ] Distance calculations from address
- [ ] Commute time estimates
- [ ] School reviews and ratings from parents
- [ ] Email alerts for new schools

### Phase 4: Expansion
- [ ] Mobile app (React Native)
- [ ] Dutch language version
- [ ] Expand to cover childcare (kinderopvang)
- [ ] University finder
- [ ] Integration with expatriate services

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Report Bugs**: Open an issue with details
2. **Suggest Features**: Describe your idea in an issue
3. **Submit PRs**: Fork, create branch, submit PR
4. **Improve Docs**: Help make documentation clearer
5. **Share Feedback**: Tell us how you're using the tool

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Code Style

- **Backend**: Follow PEP 8, use Black formatter
- **Frontend**: Follow Airbnb style guide, use ESLint
- **Commits**: Use conventional commits (feat:, fix:, docs:, etc.)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **DUO** - For providing open education data
- **Dutch Inspectorate** - For quality assessment data
- **OpenStreetMap** - For map tiles
- **Leaflet.js** - For mapping library
- **FastAPI** - For excellent API framework
- **React** - For powerful UI framework

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/dutch-school-finder/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/dutch-school-finder/discussions)
- **Email**: support@dutchschoolfinder.com (if applicable)

---

## 🌟 Star History

If you find this project useful, please consider giving it a star ⭐

---

**Built with ❤️ for expat families in the Netherlands**

*Making school choice clear, fast, and stress-free.*
