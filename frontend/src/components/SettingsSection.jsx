import React from 'react';

export default function SettingsSection({ 
  title, 
  description, 
  icon, 
  children, 
  className = '' 
}) {
  return (
    <div className={`settings-section ${className}`}>
      <div className="settings-section-header">
        {icon && <span className="settings-section-icon">{icon}</span>}
        <div>
          <h3 className="settings-section-title">{title}</h3>
          {description && <p className="settings-section-description">{description}</p>}
        </div>
      </div>
      <div className="settings-section-content">
        {children}
      </div>
    </div>
  );
}
