# ActuallyOpenSnow Frontend

Vue.js web application for viewing mountain weather forecasts.

## Overview

A modern, responsive single-page application built with:
- Vue 3 with Composition API
- Vite for fast development
- Pinia for state management
- Tailwind CSS for styling
- Chart.js for data visualization

## Requirements

- Node.js 18+
- npm 9+

## Installation

```bash
npm install
```

## Development

```bash
# Start dev server with hot reload
npm run dev

# Type checking
npm run build:typecheck

# Linting
npm run lint
```

The dev server runs at http://localhost:5173 with API proxy to backend.

## Building

```bash
# Production build
npm run build

# Preview production build
npm run preview
```

Build output goes to `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── assets/          # CSS and static assets
│   ├── components/      # Vue components
│   │   ├── common/      # Shared components
│   │   └── forecast/    # Forecast-specific components
│   ├── pages/           # Page components
│   ├── stores/          # Pinia stores
│   ├── router/          # Vue Router config
│   ├── types/           # TypeScript types
│   ├── utils/           # Utility functions
│   ├── App.vue          # Root component
│   └── main.ts          # Entry point
├── public/              # Static files
├── index.html
├── vite.config.ts
├── tailwind.config.js
└── package.json
```

## Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | HomePage | Featured resorts, powder alerts |
| `/resort/:slug` | ResortPage | Detailed resort forecast |
| `/custom` | CustomLocationsPage | Manage custom locations |
| `/custom/:id` | CustomLocationPage | Custom location forecast |
| `/favorites` | FavoritesPage | Saved favorite resorts |
| `/compare` | ComparePage | Model comparison |
| `/settings` | SettingsPage | User preferences |

## Components

### Common
- `AppHeader.vue` - Navigation header with search
- `AppSidebar.vue` - Resort list sidebar
- `LoadingSpinner.vue` - Loading indicator
- `ErrorAlert.vue` - Error display

### Forecast
- `SnowfallCard.vue` - Snowfall summary card
- `SnowGraph.vue` - Interactive snowfall chart
- `DailyBreakdown.vue` - Daily forecast table
- `WeatherStats.vue` - Current conditions
- `ModelSelector.vue` - Weather model picker

## Stores

### `settings.ts`
User preferences (units, theme) persisted to localStorage.

### `resorts.ts`
Resort data and favorites management.

### `forecast.ts`
Forecast data with caching.

### `customLocations.ts`
User-defined custom locations.

## API Integration

API calls are centralized in `utils/api.ts`:

```typescript
// Fetch resort forecast
const forecast = await fetchResortForecast('jackson-hole', 'blend')

// Batch fetch multiple resorts
const forecasts = await fetchBatchForecasts(['alta', 'snowbird'], 'blend')

// Fetch custom coordinates
const forecast = await fetchForecast(40.5, -111.6, 'gfs', 3000)
```

## Unit Conversion

Utilities in `utils/units.ts` handle conversions:

```typescript
// Temperature
convertTemperature(0, 'C', 'F')  // → 32

// Precipitation
convertPrecipitation(10, 'cm', 'in')  // → 3.94

// Elevation
convertElevation(3000, 'm', 'ft')  // → 9843
```

## Styling

Uses Tailwind CSS with custom theme:

```javascript
// tailwind.config.js
colors: {
  mountain: { /* dark grays */ },
  snow: { /* light blues */ },
}
```

Custom CSS classes in `assets/main.css`:
- `.glass-card` - Frosted glass effect
- `.btn-primary` - Primary button style
- `.stat-number` - Large stat display

## Environment Variables

Create `.env` for local development:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Docker

```bash
# Build production image
docker build -t actuallyopensnow-frontend .

# Run (serves on port 80)
docker run -p 80:80 actuallyopensnow-frontend
```

The production image uses Nginx to:
- Serve static files
- Proxy `/api/*` requests to backend
- Handle client-side routing

## Browser Support

- Chrome 90+
- Firefox 90+
- Safari 14+
- Edge 90+

## Performance

- Code splitting via Vue Router lazy loading
- Client-side forecast caching (30 min TTL)
- Batch API requests for homepage
- Efficient Chart.js rendering

