# ActuallyOpenSnow ❄️

An open-source mountain weather forecasting application that provides accurate snow predictions using multi-model blending. Think OpenSnow, but actually open source.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- **Multi-Model Blend**: Weighted average of GFS, IFS, AIFS, ICON, and JMA weather models for more accurate predictions
- **70+ Ski Resorts**: Complete coverage of Ikon and Epic pass resorts across North America
- **Custom Locations**: Add your own coordinates for backcountry forecasts
- **Detailed Forecasts**: Hourly snowfall, temperature, wind, and freezing level data
- **Interactive Charts**: Visualize snowfall predictions over customizable time ranges
- **Unit Preferences**: Toggle between Imperial (°F/inches) and Metric (°C/cm)
- **Responsive Design**: Works on desktop, tablet, and mobile

## Architecture

```
ActuallyOpenSnow/
├── weather/          # Python weather API library
├── backend/          # FastAPI REST API server
├── frontend/         # Vue.js web application
├── docker-compose.yaml
└── README.md
```

## Quick Start

### Using Docker (Recommended)

```bash
# Production
docker compose up -d

# Development (with hot reload)
docker compose -f docker-compose.dev.yaml up -d
```

The application will be available at:
- Frontend: http://localhost (production) or http://localhost:5173 (dev)
- Backend API: http://localhost:8000

### Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

### Blend Model Weights

The blend model weights can be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `BLEND_WEIGHT_GFS` | 2.0 | NOAA GFS weight |
| `BLEND_WEIGHT_IFS` | 2.0 | ECMWF IFS weight |
| `BLEND_WEIGHT_AIFS` | 2.0 | ECMWF AIFS weight |
| `BLEND_WEIGHT_ICON` | 1.0 | DWD ICON weight |
| `BLEND_WEIGHT_JMA` | 1.0 | JMA weight |

Set a weight to `0` to exclude that model from the blend.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/resorts` | List all ski resorts |
| `GET /api/resorts/{slug}/forecast` | Get forecast for a resort |
| `GET /api/forecast?lat=&lon=` | Get forecast for coordinates |
| `GET /api/models` | List available weather models |
| `GET /api/blend/config` | View blend configuration |

## Tech Stack

- **Frontend**: Vue 3, Vite, Pinia, Tailwind CSS, Chart.js
- **Backend**: FastAPI, Python 3.11+
- **Weather Data**: Open-Meteo API
- **Deployment**: Docker, Nginx

## Data Sources

Weather data is sourced from [Open-Meteo](https://open-meteo.com/), which provides free access to:
- NOAA GFS (Global Forecast System)
- ECMWF IFS (Integrated Forecast System)
- ECMWF AIFS (AI-enhanced Forecast System)
- DWD ICON (Icosahedral Nonhydrostatic)
- JMA (Japan Meteorological Agency)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [Open-Meteo](https://open-meteo.com/) for providing free weather API access
- Inspired by [OpenSnow](https://opensnow.com/)

