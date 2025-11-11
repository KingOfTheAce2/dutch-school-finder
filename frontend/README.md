# Dutch School Finder - Frontend

React + TypeScript frontend application for finding and comparing schools in the Netherlands.

## Features

- 🗺️ **Interactive Map View** - Visualize schools on a map with Leaflet.js
- 📋 **List View** - Browse schools in a card-based layout
- 🔍 **Advanced Search** - Filter by city, type, rating, and language programs
- 🌍 **Expat-Friendly** - Special filters for bilingual and international schools
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile devices
- ⚡ **Fast & Modern** - Built with Vite for optimal performance

## Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type-safe development
- **Vite** - Build tool and dev server
- **React-Leaflet** - Interactive maps
- **Axios** - API communication
- **CSS3** - Styling with modern features

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running on http://localhost:8000

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env if needed
```

3. Start development server:
```bash
npm run dev
```

The application will open at http://localhost:3000

### Build for Production

```bash
npm run build
```

The build output will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── components/      # React components
│   │   ├── Header.tsx
│   │   ├── SearchPanel.tsx
│   │   ├── SchoolMap.tsx
│   │   ├── SchoolList.tsx
│   │   └── SchoolDetail.tsx
│   ├── api.ts          # API client
│   ├── types.ts        # TypeScript types
│   ├── App.tsx         # Main app component
│   ├── main.tsx        # Entry point
│   └── index.css       # Global styles
├── index.html
├── vite.config.ts
└── package.json
```

## Components

### Header
Top navigation bar with branding and info badges.

### SearchPanel
Sidebar with search filters:
- School name search
- City filter
- School type filter
- Minimum rating filter
- Bilingual/International toggles
- View mode toggle (Map/List)

### SchoolMap
Interactive Leaflet map showing:
- School markers (color-coded by type)
- Popup information on click
- Legend for school types
- Auto-fit bounds to show all schools

### SchoolList
Card-based list view with:
- School information cards
- Filtering and sorting
- Click to view details

### SchoolDetail
Sliding detail panel showing:
- Complete school information
- Quality indicators
- Contact information
- Links to maps and website

## API Integration

The frontend communicates with the backend API at `http://localhost:8000` (configurable via `VITE_API_URL`).

### Endpoints Used

- `GET /schools` - Fetch all schools
- `GET /schools/search` - Search with filters
- `GET /cities` - Get list of cities
- `GET /types` - Get school types

See `src/api.ts` for complete API client.

## Styling

Each component has its own CSS file using BEM-like naming conventions:
- Component styles are scoped to avoid conflicts
- Responsive breakpoints at 768px for mobile
- CSS variables could be added for theming

## Environment Variables

Create a `.env` file based on `.env.example`:

```env
VITE_API_URL=http://localhost:8000
```

## Development Tips

### Hot Module Replacement
Vite provides instant HMR - changes appear immediately without full reload.

### Type Checking
Run TypeScript compiler to check for type errors:
```bash
npx tsc --noEmit
```

### Debugging
- Use React DevTools browser extension
- Check Network tab for API calls
- Console logs in browser DevTools

## Deployment

### Vercel (Recommended)

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Deploy:
```bash
vercel
```

### Netlify

1. Build the project:
```bash
npm run build
```

2. Deploy `dist/` folder via Netlify CLI or UI

### Static Hosting

Build and upload the `dist/` folder to any static hosting service:
- GitHub Pages
- AWS S3 + CloudFront
- Azure Static Web Apps
- Google Cloud Storage

**Important:** Update `VITE_API_URL` to point to your production API.

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Troubleshooting

### Map not displaying
- Check that Leaflet CSS is loaded in index.html
- Verify schools have valid latitude/longitude coordinates

### API connection failed
- Ensure backend is running on correct port
- Check CORS settings in backend
- Verify API_URL in .env

### Build errors
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check Node.js version (18+)
- Update dependencies: `npm update`

## Future Enhancements

- [ ] Search by postal code or address
- [ ] Distance calculation from user location
- [ ] Save favorite schools (with local storage)
- [ ] Compare multiple schools side-by-side
- [ ] Share school via URL with query parameters
- [ ] Print-friendly school detail view
- [ ] Dark mode theme
- [ ] Multi-language support (Dutch, English, etc.)

## Contributing

1. Follow existing code style
2. Add types for all props and state
3. Keep components focused and reusable
4. Write meaningful commit messages
5. Test on different screen sizes

## License

Part of the Dutch School Finder project.
