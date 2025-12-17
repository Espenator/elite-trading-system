# 🚀 Elite Trading System - Installation Guide

## Prerequisites

- Node.js 18+ installed
- npm or yarn package manager
- Terminal/Command Prompt access

## Step-by-Step Installation

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Install All Dependencies

```bash
npm install
```

This will install:
- React 18.3.0
- React Router DOM 6.23.0
- Font Awesome 6.5.1 (all packages)
- Tailwind CSS 3.4.0
- Vite 5.1.0
- lightweight-charts 5.0.9
- And all other dependencies

**Expected time**: 2-3 minutes

### 3. Start Development Server

```bash
npm run dev
```

**Output should show:**
```
VITE v5.1.0  ready in XXX ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
```

### 4. Open in Browser

Navigate to: `http://localhost:3000`

You should see the **Dashboard** page with:
- Collapsible sidebar on the left
- Market overview cards
- Live trading signals table
- Active positions table
- Risk summary

## 🧪 Testing the Application

### Test 1: Navigation
- ✅ Click each menu item in sidebar
- ✅ Verify all 12 pages load
- ✅ Check that 4 pages are fully implemented
- ✅ Check that 8 pages show "Coming Soon"

### Test 2: Theme Toggle
- ✅ Click sun/moon icon in top-right header
- ✅ Verify theme switches between light and dark
- ✅ Refresh page - theme should persist
- ✅ Check localStorage has 'theme' key

### Test 3: Sidebar
- ✅ Click collapse button at bottom of sidebar
- ✅ Sidebar should shrink to icons only
- ✅ Click again to expand
- ✅ Hover over items when collapsed shows tooltip

### Test 4: Responsive Design
- ✅ Resize browser window to mobile size (< 768px)
- ✅ Sidebar should adapt
- ✅ Tables should scroll horizontally
- ✅ Cards should stack vertically

### Test 5: Dashboard Features
- ✅ Market stats cards display correctly
- ✅ Live signals table is readable
- ✅ Active positions table shows data
- ✅ Risk summary displays properly
- ✅ ML insights section visible

### Test 6: Trade Execution Page
- ✅ Navigate to `/trade`
- ✅ Chart placeholder displays
- ✅ Order entry form works
- ✅ Buy/Sell buttons are styled correctly
- ✅ Recent orders table displays
- ✅ Execution logs table displays

### Test 7: Settings Page
- ✅ Navigate to `/settings`
- ✅ All sections expand/collapse
- ✅ Toggle switches work
- ✅ Input fields are editable
- ✅ API keys table displays
- ✅ Danger zone is styled in red

## 📱 Browser Testing

Test in multiple browsers:
- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari (if on Mac)

## 🐛 Troubleshooting

### Issue: `npm install` fails

**Solution:**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

### Issue: Port 3000 already in use

**Solution:**
```bash
# Kill process on port 3000 (Windows)
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Or use different port
npm run dev -- --port 3001
```

### Issue: Styles not loading

**Solution:**
```bash
# Rebuild Tailwind
npm run build

# Restart dev server
npm run dev
```

### Issue: Icons not showing

**Solution:**
```bash
# Reinstall Font Awesome packages
npm uninstall @fortawesome/fontawesome-svg-core @fortawesome/free-solid-svg-icons @fortawesome/react-fontawesome
npm install @fortawesome/fontawesome-svg-core @fortawesome/free-solid-svg-icons @fortawesome/free-regular-svg-icons @fortawesome/free-brands-svg-icons @fortawesome/react-fontawesome
```

### Issue: Dark mode not working

**Solution:**
1. Check browser console for errors
2. Verify `tailwind.config.js` has `darkMode: 'class'`
3. Clear localStorage: `localStorage.clear()`
4. Refresh page

## 🔧 Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code (if configured)
npm run lint
```

## 📊 Expected File Sizes

After `npm install`:
- `node_modules/`: ~400-500 MB
- Total project: ~450-550 MB

After `npm run build`:
- `dist/`: ~500 KB - 2 MB (optimized)

## 🎯 Success Checklist

Before considering installation complete:

- [ ] `npm install` completed without errors
- [ ] Dev server starts on port 3000
- [ ] All 12 pages are accessible
- [ ] Dark/light theme toggle works
- [ ] Sidebar collapses/expands
- [ ] No console errors in browser
- [ ] Dashboard displays correctly
- [ ] Trade Execution page displays correctly
- [ ] Settings page displays correctly
- [ ] Responsive design works on mobile
- [ ] Theme persists after refresh

## 🚀 Next Steps After Installation

1. **Connect to Backend**
   - Update API URLs in `src/services/api.service.js`
   - Test API connectivity

2. **Implement Real Data**
   - Connect WebSocket for live signals
   - Fetch real market data
   - Implement user authentication

3. **Build Remaining Pages**
   - Complete the 8 "Coming Soon" pages
   - Add real functionality

4. **Deploy**
   - Build production version: `npm run build`
   - Deploy `dist/` folder to hosting

## 📚 Additional Resources

- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Font Awesome React](https://fontawesome.com/docs/web/use-with/react/)

## 💬 Support

If you encounter issues:
1. Check browser console for errors
2. Check terminal for build errors
3. Verify Node.js version: `node --version` (should be 18+)
4. Verify npm version: `npm --version`

---

**Installation complete! Happy trading! 📈**

