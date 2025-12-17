# Elite Trading System - Frontend Setup

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

This will install all required packages including:
- React 18.3
- React Router DOM 6.23
- Font Awesome icons
- Tailwind CSS 3.4
- Vite 5.1
- lightweight-charts 5.0.9

### 2. Run Development Server

```bash
npm run dev
```

The application will start on `http://localhost:3000`

### 3. Build for Production

```bash
npm run build
```

Output will be in the `dist/` directory.

## 📄 Pages Overview

The application includes 12 pages:

1. **Dashboard** (`/dashboard`) - Market overview with live signals and positions
2. **Trade Execution** (`/trade`) - Order entry and execution interface
3. **Portfolio Heatmap** (`/portfolio`) - Portfolio visualization (Coming Soon)
4. **Model Training** (`/model-training`) - ML model management (Coming Soon)
5. **Performance Analytics** (`/performance`) - Trading performance metrics (Coming Soon)
6. **Screener Results** (`/screener`) - Stock screening (Coming Soon)
7. **Order History** (`/order-history`) - Historical orders and backtesting (Coming Soon)
8. **Settings** (`/settings`) - System configuration
9. **Account Settings** (`/account-settings`) - User account management (Coming Soon)
10. **Risk Configuration** (`/risk-config`) - Risk management settings (Coming Soon)
11. **Strategy Settings** (`/strategy`) - Trading strategy configuration (Coming Soon)
12. **Account** (`/account`) - User profile page

## 🎨 Features

### Dark/Light Theme
- Toggle between dark and light modes
- Theme preference saved to localStorage
- Smooth transitions between themes

### Responsive Design
- Mobile-friendly sidebar that collapses
- Responsive grid layouts
- Touch-friendly controls

### Font Awesome Icons
- 1000+ professional icons
- Consistent visual language
- Scalable vector graphics

### Modern UI Components
- Clean, professional design
- Smooth animations
- Accessible controls

## 🛠️ Tech Stack

- **React 18.3** - UI framework
- **Vite 5.1** - Build tool (fast HMR)
- **Tailwind CSS 3.4** - Utility-first CSS
- **React Router DOM 6.23** - Client-side routing
- **Font Awesome 6.5** - Icon library
- **lightweight-charts 5.0.9** - TradingView charts

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── layout/
│   │       └── MainLayout.jsx       # Main app layout with sidebar
│   ├── context/
│   │   └── ThemeContext.jsx         # Dark/light theme provider
│   ├── pages/
│   │   ├── Dashboard.jsx            # ✅ Complete
│   │   ├── TradeExecution.jsx       # ✅ Complete
│   │   ├── Settings.jsx             # ✅ Complete
│   │   ├── Account.jsx              # ✅ Complete
│   │   └── [8 more pages]           # 🔄 Coming Soon placeholders
│   ├── routes/
│   │   └── AppRoutes.jsx            # Route configuration
│   ├── App.jsx                      # Root component
│   ├── main.jsx                     # Entry point
│   └── index.css                    # Global styles
├── package.json
├── tailwind.config.js
├── vite.config.js
└── SETUP.md                         # This file
```

## 🎯 Next Steps

1. **Install dependencies**: `npm install`
2. **Run dev server**: `npm run dev`
3. **Connect to backend**: Update API URLs in service files
4. **Implement remaining pages**: Build out the "Coming Soon" pages
5. **Add real data**: Connect to WebSocket and REST APIs

## 🔧 Configuration

### Backend API URL
Update in `src/services/api.service.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000';
```

### Theme
Default theme is set to 'dark'. Users can toggle in the UI.

### Sidebar
Collapsible sidebar with 11 menu items + account section.

## 📚 Documentation

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Font Awesome React](https://fontawesome.com/docs/web/use-with/react/)
- [React Router](https://reactrouter.com/)

## 💡 Tips

- Use `Ctrl+Shift+D` to toggle dark mode (via UI button)
- Sidebar auto-collapses on mobile
- All pages are lazy-loaded for performance
- Theme preference persists across sessions

---

**Built with ❤️ for Elite Trading System**

