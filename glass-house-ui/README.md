# Elite Trading System - Glass House UI

**Production-ready Next.js frontend with 100% real backend integration**

## Overview

This is the frontend dashboard for the Elite Trading System. It connects to the backend services running at `http://localhost:8000` and displays:

- **Real-time market prices** from `database/query_engine.py`
- **Trading signals** from `signal_generation/` modules (compression, ignition)
- **ML predictions** from `prediction_engine/` modules (1h, 1d, 1w)
- **Technical indicators** from `data_collection/technical_calculator.py`
- **Live WebSocket updates** from `ws://localhost:8000/ws`

## Key Features

✅ **100% Real Backend Integration** - No mock data anywhere
✅ **Real-time WebSocket** - Live updates from signal engines
✅ **Type-Safe** - Full TypeScript with strict mode
✅ **Zustand State Management** - Backend-fed state only
✅ **Dark Trading Theme** - Professional UI with Tailwind CSS
✅ **Responsive Design** - Works on desktop, tablet, mobile

## Architecture


## Prerequisites

- **Node.js** >= 18.0.0
- **npm** >= 9.0.0
- **Backend running** at `http://localhost:8000`
- **WebSocket enabled** at `ws://localhost:8000/ws`

## Installation

### 1. Install Dependencies


### 2. Configure Backend Connection

Edit `.env.local`:


### 3. Start Backend (if not already running)

In another terminal:


Verify backend is online: http://localhost:8000/docs

### 4. Start Frontend Development Server


The app will be available at: [**http://localhost:3000**](http://localhost:3000)

## Available Scripts

- `npm run dev` - Start development server (port 3000)
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - TypeScript type checking

## Backend Integration

### API Client (`lib/api/client.ts`)

All API calls go through the centralized client:


### WebSocket Manager (`lib/api/websocket.ts`)

Real-time updates from backend:


### Store (`lib/store/index.ts`)

Zustand store for state management:


## Data Flow


## Troubleshooting

### Backend Connection Failed


**Solution:**
1. Check if backend is running: `python -m uvicorn backend.main:app --port 8000`
2. Verify backend is accessible: http://localhost:8000/docs
3. Check firewall settings
4. Ensure port 8000 is not in use

### WebSocket Connection Failed


**Solution:**
1. Backend must support WebSocket at `ws://localhost:8000/ws`
2. Check backend logs for WebSocket errors
3. Verify `NEXT_PUBLIC_WS_URL` in `.env.local`

### No Data Displayed

**Solution:**
1. Check if signals are being generated: Run signal scanner
2. Verify database has data: Check `database/trading.db`
3. Check backend logs for errors
4. Ensure symbols in `.env.local` match your data

### Type Errors


Ensure all TypeScript types match backend responses.

## Environment Variables

Create `.env.local`:


Open http://localhost:3000

## Performance Tips

- WebSocket auto-reconnects on disconnect
- Message queue prevents data loss while offline
- Zustand optimizes re-renders
- Next.js code splitting for fast page loads
- Recharts lazy-loads chart data

## Security Notes

- `.env.local` is in `.gitignore` - never commit credentials
- API calls validate backend responses
- WebSocket auto-disconnects on page unload
- CORS configured in backend

## Project Structure

- **`lib/api/`** - Backend communication (HTTP + WebSocket)
- **`lib/store/`** - State management with Zustand
- **`lib/types/`** - TypeScript type definitions
- **`app/`** - Next.js pages and layouts
- **`components/`** - Reusable UI components
- **`public/`** - Static assets
- **`.env.local`** - Environment configuration

## Technologies Used

- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Zustand** - State management
- **Axios** - HTTP client
- **Recharts** - Charting library
- **Tailwind CSS** - Styling
- **Lucide React** - Icons

## Support

For issues or questions:

1. Check backend logs
2. Check browser console (F12)
3. Verify `.env.local` configuration
4. Ensure backend is running and healthy

## License

Proprietary - Elite Trading System

---

**Status:** Production Ready ✅

**Last Updated:** December 6, 2025
