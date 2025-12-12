# Elite Trading System - Frontend

A sleek, modern React-based trading terminal with real-time signal feeds, interactive charts, and comprehensive market intelligence. Built for professional traders who demand speed, precision, and reliability.

## 🚀 Features

- **Live Signal Feed**: Real-time trading signals via WebSocket with auto-reconnection
- **Tactical Chart**: Interactive price charts powered by lightweight-charts
- **Intelligence Radar**: Market overview and watchlist management
- **Execution Deck**: Quick trade execution interface
- **Command Bar**: System-wide command palette and status monitoring
- **Dark Theme**: Professional trading terminal aesthetic
- **Responsive Design**: Optimized for desktop trading workstations
- **WebSocket Resilience**: Auto-reconnect with connection status indicators
- **Modern UI**: Built with React 18 and Tailwind CSS

## 🛠️ Tech Stack

- **Framework**: React 18.3
- **Build Tool**: Vite 5.1
- **Styling**: Tailwind CSS 3.4
- **Charts**: lightweight-charts 5.0.9
- **Routing**: React Router DOM 6.23
- **Notifications**: SweetAlert2 11.26
- **Backend Integration**: Supabase JS (optional)
- **Type Safety**: PropTypes for runtime validation

## 📋 Prerequisites

- Node.js 18+ or higher
- npm or yarn package manager
- Elite Trading System Backend running on port 8000

## 🔧 Installation

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```

or with yarn:

```bash
yarn install
```

### 3. Configure Backend URL (Optional)

If your backend is not running on `http://localhost:8000`, update the API configuration:

**Edit `src/services/api.service.js`:**
```javascript
const API_BASE_URL = 'http://your-backend-url:8000';
const WS_BASE_URL = 'ws://your-backend-url:8000';
```

**Or edit `src/pages/Dashboard.jsx`:**
```javascript
ws = new WebSocket('ws://your-backend-url:8000/ws');
```

## 🚀 Running the Application

### Development Mode

```bash
npm run dev
```

The application will start on `http://localhost:3000`

- Hot Module Replacement (HMR) enabled
- Source maps for debugging
- Fast refresh on file changes

### Production Build

```bash
npm run build
```

This will create an optimized production build in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

Serves the production build locally for testing.

## 🌐 Deployment

### Static Hosting (Netlify, Vercel, etc.)

1. Build the project:
   ```bash
   npm run build
   ```

2. Deploy the `dist/` folder to your hosting provider

3. Configure environment variables for backend URL

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Backend Connection

Ensure your backend API is accessible:
- Development: `http://localhost:8000`
- Production: Update URLs in configuration files
- CORS: Backend must allow requests from your frontend domain

## 📁 Project Structure

```
frontend/
├── dist/                          # Production build output
├── public/
│   └── favicon.ico                # App favicon
├── src/
│   ├── assets/                    # Images, fonts, static files
│   ├── components/
│   │   ├── CommandBar.jsx         # Top command bar with status
│   │   ├── ExecutionDeck.jsx      # Trade execution panel
│   │   ├── IntelligenceRadar.jsx  # Market intelligence panel
│   │   ├── LiveSignalFeed.jsx     # Real-time signal feed
│   │   ├── TacticalChart.jsx      # Interactive price chart
│   │   ├── layout/
│   │   │   ├── Header.jsx         # App header
│   │   │   └── Layout.jsx         # Main layout wrapper
│   │   └── ui/
│   │       └── Button.jsx         # Reusable button component
│   ├── context/
│   │   └── ThemeContext.jsx       # Theme management
│   ├── hooks/                     # Custom React hooks
│   ├── pages/
│   │   ├── Dashboard.jsx          # Main trading dashboard
│   │   └── NotFound.jsx           # 404 page
│   ├── routes/
│   │   └── AppRoutes.jsx          # Route configuration
│   ├── services/
│   │   ├── api.service.js         # API client functions
│   │   └── auth.service.js        # Authentication service
│   ├── types/
│   │   ├── api.types.js           # API type definitions
│   │   ├── auth.types.js          # Auth type definitions
│   │   └── user.types.js          # User type definitions
│   ├── utils/
│   │   ├── constants.js           # App constants
│   │   ├── formatters.js          # Data formatting utilities
│   │   ├── helpers.js             # Helper functions
│   │   └── validators.js          # Input validation
│   ├── App.jsx                    # Root component
│   ├── main.jsx                   # Application entry point
│   └── index.css                  # Global styles
├── index.html                     # HTML template
├── package.json                   # Dependencies and scripts
├── postcss.config.js              # PostCSS configuration
├── tailwind.config.js             # Tailwind CSS configuration
├── vite.config.js                 # Vite configuration
└── README.md                      # This file
```

## 🎨 Key Components

### Dashboard (EliteTraderTerminal)

Main trading interface with 5 zones:

1. **Zone 0 - Command Bar**: System controls and connection status
2. **Zone 1 - Intelligence Radar**: Watchlist and market overview (left panel)
3. **Zone 2 - Tactical Chart**: Interactive price charts (center)
4. **Zone 3 - Execution Deck**: Trade management (right panel)
5. **Zone 4 - Live Signal Feed**: Real-time trading signals (bottom)

Features:
- WebSocket connection with auto-reconnect
- Symbol selection and switching
- Real-time connection status monitoring

### LiveSignalFeed

Real-time trading signal display:
- WebSocket integration for live updates
- Signal tier classification (T1/T2/T3)
- Color-coded by signal strength
- Click to select symbol
- Scrollable feed with latest signals

### TacticalChart

Interactive charting component:
- Powered by TradingView's lightweight-charts
- Multiple timeframes support
- Candlestick and line charts
- Volume bars
- Real-time price updates

### IntelligenceRadar

Market intelligence panel:
- Watchlist management
- Market movers
- Sector rotation tracking
- Quick symbol search

### ExecutionDeck

Trade execution interface:
- Quick order entry
- Position management
- P&L tracking
- Risk management tools

### CommandBar

Top control bar:
- Connection status indicator
- Active symbol display
- Quick actions
- System notifications

## 🎯 WebSocket Integration

### Connection Handling

The app automatically connects to the WebSocket server on mount:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('✅ WebSocket Connected');
  setWsConnected(true);
};

ws.onclose = () => {
  console.log('❌ WebSocket Disconnected');
  setWsConnected(false);
  // Auto-reconnect after 3 seconds
  setTimeout(() => connect(), 3000);
};
```

### Message Format

**Signals Update:**
```javascript
{
  type: "signals_update",
  signals: [
    {
      symbol: "AAPL",
      signal_type: "momentum",
      tier: "T1",
      score: 85.5,
      price: 178.50,
      change_pct: 2.5,
      volume_ratio: 2.3,
      catalyst: "Strong momentum +2.5% with 2.3x vol",
      timestamp: "2024-12-12T10:30:00"
    }
  ],
  timestamp: "2024-12-12T10:30:00"
}
```

## 🎨 Styling & Theming

### Tailwind CSS Configuration

Custom theme extends Tailwind with trading-specific colors:

```javascript
theme: {
  extend: {
    colors: {
      primary: '#00ff00',      // Success green
      danger: '#ff0000',       // Danger red
      warning: '#ffaa00',      // Warning amber
      accent: '#00ccff',       // Accent cyan
    }
  }
}
```

### Custom Fonts

Located in `public/fonts/`:
- **League Spartan**: Headers and emphasis
- **Lato**: Body text and UI elements

### Dark Theme

Optimized for low-light trading environments:
- Dark backgrounds (#0a0e1a, #111827)
- High contrast text
- Reduced eye strain
- Professional aesthetics

## 🔧 Configuration

### Vite Configuration

**vite.config.js:**
```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
});
```

### Tailwind Configuration

**tailwind.config.js:**
- Custom color palette
- Extended spacing
- Custom breakpoints for trading screens
- JIT mode for optimal bundle size

### PostCSS Configuration

**postcss.config.js:**
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

## 📱 Responsive Design

Optimized breakpoints:
- **Desktop (1920px+)**: Full multi-panel layout
- **Laptop (1440px)**: Optimized panel sizing
- **Tablet (1024px)**: Stacked panels
- **Mobile (768px-)**: Single column layout

## 🔍 Development Tools

### ESLint Configuration

Prettier integration for consistent code style:
```json
{
  "extends": ["eslint:recommended", "plugin:react/recommended", "prettier"]
}
```

### Hot Module Replacement

Vite provides instant updates without full page reload:
- Component updates preserve state
- CSS updates without reload
- Fast refresh for React components

## 🧪 Testing

### Recommended Testing Setup

```bash
# Install testing libraries
npm install --save-dev @testing-library/react @testing-library/jest-dom vitest
```

### Running Tests

```bash
npm run test
```

### Test Structure

```javascript
// Example test
import { render, screen } from '@testing-library/react';
import Dashboard from './pages/Dashboard';

test('renders dashboard', () => {
  render(<Dashboard />);
  expect(screen.getByText(/Elite Trading/i)).toBeInTheDocument();
});
```

## 🐛 Troubleshooting

### WebSocket Connection Failed

**Issue**: Unable to connect to WebSocket server

**Solutions**:
- Verify backend is running on port 8000
- Check WebSocket URL in Dashboard.jsx
- Ensure no firewall blocking WebSocket connections
- Check browser console for CORS errors

### Chart Not Rendering

**Issue**: TacticalChart component shows blank

**Solutions**:
- Ensure lightweight-charts is installed correctly
- Check browser console for errors
- Verify chart container has height set
- Check if symbol data is being received

### Build Errors

**Issue**: npm run build fails

**Solutions**:
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
npm run dev
```

### Styles Not Applying

**Issue**: Tailwind classes not working

**Solutions**:
- Verify tailwind.config.js content paths
- Check PostCSS configuration
- Restart dev server
- Clear browser cache

## 🔐 Security Best Practices

1. **Environment Variables**: Use `.env` for sensitive configuration
2. **API Keys**: Never commit API keys to version control
3. **HTTPS**: Use HTTPS in production
4. **Content Security Policy**: Implement CSP headers
5. **XSS Protection**: Sanitize user inputs
6. **CORS**: Configure proper CORS on backend

## 📊 Performance Optimization

### Current Optimizations

- **Code Splitting**: React.lazy() for route-based splitting
- **Tree Shaking**: Vite removes unused code
- **Asset Optimization**: Images and fonts optimized
- **Lazy Loading**: Components load on demand
- **Memoization**: React.memo for expensive components

### Recommended Enhancements

```javascript
// Lazy load components
const TacticalChart = React.lazy(() => import('./components/TacticalChart'));

// Memoize expensive calculations
const memoizedValue = useMemo(() => computeExpensiveValue(a, b), [a, b]);

// Debounce WebSocket messages
const debouncedHandler = debounce(handleSignalUpdate, 100);
```

## 📚 Additional Resources

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [lightweight-charts Documentation](https://tradingview.github.io/lightweight-charts/)
- [React Router Documentation](https://reactrouter.com/)

## 🚀 Future Enhancements

- [ ] User authentication and profiles
- [ ] Portfolio tracking and P&L
- [ ] Advanced charting indicators
- [ ] Alert configuration
- [ ] Trade history and analytics
- [ ] Mobile application
- [ ] Multi-monitor support
- [ ] Custom dashboard layouts
- [ ] Advanced order types
- [ ] Paper trading mode

## 🤝 Contributing

1. Follow React best practices
2. Use functional components with hooks
3. Add PropTypes for all components
4. Write meaningful commit messages
5. Test on multiple browsers
6. Update README for new features

## 📄 License

This project is part of the Elite Trading System suite.

## 💬 Support

For issues, questions, or contributions, please refer to the main project repository.

---

**Built with React** ⚛️ | **Styled with Tailwind** 🎨 | **Elite Trading System** 🎯
