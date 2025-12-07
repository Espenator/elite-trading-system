import React from 'react';
import React, { useState, useEffect } from 'react';
import { themes, applyTheme } from '../../utils/themes';
import './ThemeSwitcher.css';

const ThemeSwitcher = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentTheme, setCurrentTheme] = useState('elite-dark');

  useEffect(() => {
    const saved = localStorage.getItem('elite-theme') as keyof typeof themes;
    if (saved && themes[saved]) {
      setCurrentTheme(saved);
      applyTheme(saved);
    }
  }, []);

  const handleThemeChange = (themeName: keyof typeof themes) => {
    setCurrentTheme(themeName);
    applyTheme(themeName);
    setIsOpen(false);
  };

  return (
    <div className="theme-switcher">
      <button className="theme-toggle" onClick={() => setIsOpen(!isOpen)}>
        🎨
      </button>
      
      {isOpen && (
        <div className="theme-dropdown">
          {Object.entries(themes).map(([key, theme]) => (
            <button
              key={key}
              className={`theme-option ${currentTheme === key ? 'active' : ''}`}
              onClick={() => handleThemeChange(key as keyof typeof themes)}
            >
              <div 
                className="theme-preview" 
                style={{ 
                  background: `linear-gradient(135deg, ${theme.background}, ${theme.surface})`,
                  border: `2px solid ${theme.accent}`
                }}
              ></div>
              <span>{theme.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default ThemeSwitcher;

