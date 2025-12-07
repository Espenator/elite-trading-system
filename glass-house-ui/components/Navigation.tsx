'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Navigation() {
  const pathname = usePathname();
  
  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: '📊' },
    { name: 'Signals', path: '/signals', icon: '⚡' },
    { name: 'Charts', path: '/charts', icon: '📈' },
    { name: 'System Health', path: '/health', icon: '🏥' },
  ];

  return (
    <nav style={{
      background: '#1e293b',
      borderRight: '1px solid #334155',
      width: '250px',
      height: '100vh',
      position: 'fixed',
      left: 0,
      top: 0,
      padding: '2rem 0',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{ padding: '0 1.5rem', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#fff' }}>
          🏛️ Glass House
        </h1>
        <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
          Elite Trading System
        </p>
      </div>

      <div style={{ flex: 1 }}>
        {navItems.map((item) => (
          <Link
            key={item.path}
            href={item.path}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '1rem 1.5rem',
              color: pathname === item.path ? '#3b82f6' : '#94a3b8',
              background: pathname === item.path ? '#1e3a8a' : 'transparent',
              borderLeft: pathname === item.path ? '4px solid #3b82f6' : '4px solid transparent',
              textDecoration: 'none',
              transition: 'all 0.2s',
              fontWeight: pathname === item.path ? 'bold' : 'normal'
            }}
            onMouseEnter={(e) => {
              if (pathname !== item.path) {
                e.currentTarget.style.background = '#334155';
              }
            }}
            onMouseLeave={(e) => {
              if (pathname !== item.path) {
                e.currentTarget.style.background = 'transparent';
              }
            }}
          >
            <span style={{ fontSize: '1.25rem', marginRight: '0.75rem' }}>{item.icon}</span>
            {item.name}
          </Link>
        ))}
      </div>

      <div style={{ 
        padding: '1rem 1.5rem',
        borderTop: '1px solid #334155',
        color: '#64748b',
        fontSize: '0.75rem'
      }}>
        <div>API: localhost:8000</div>
        <div style={{ marginTop: '0.25rem' }}>
          Status: <span style={{ color: '#10b981' }}>● Connected</span>
        </div>
      </div>
    </nav>
  );
}
