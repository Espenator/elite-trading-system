import React from 'react';
import React, { createContext, useContext, useState, useCallback } from 'react';
import './ToastNotification.css';

interface Toast {
  id: number;
  type: 'critical' | 'warning' | 'info' | 'success';
  message: string;
  timestamp: Date;
}

interface ToastContextType {
  addToast: (type: Toast['type'], message: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((type: Toast['type'], message: string) => {
    const toast: Toast = {
      id: Date.now(),
      type,
      message,
      timestamp: new Date(),
    };

    setToasts((prev) => [...prev, toast]);

    // Play sound
    const soundMap = {
      critical: '/sounds/alert.mp3',
      warning: '/sounds/warning.mp3',
      info: '/sounds/notification.mp3',
      success: '/sounds/success.mp3',
    };
    
    try {
      new Audio(soundMap[type]).play().catch(() => {});
    } catch (e) {}

    // Desktop notification
    if (Notification.permission === 'granted') {
      new Notification('Elite Trader', {
        body: message,
        icon: '/favicon.ico',
      });
    }

    // Auto-dismiss non-critical
    if (type !== 'critical') {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== toast.id));
      }, 5000);
    }
  }, []);

  const removeToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.type}`}>
            <div className="toast-icon">
              {toast.type === 'critical' && '🚨'}
              {toast.type === 'warning' && '⚠️'}
              {toast.type === 'info' && 'ℹ️'}
              {toast.type === 'success' && '✅'}
            </div>
            <div className="toast-content">
              <div className="toast-message">{toast.message}</div>
              <div className="toast-time">{toast.timestamp.toLocaleTimeString()}</div>
            </div>
            <button className="toast-close" onClick={() => removeToast(toast.id)}>✕</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

