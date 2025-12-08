'use client';

interface NotificationProps {
  id: string;
  type: 'success' | 'warning' | 'error' | 'info';
  title: string;
  message: string;
  onClose: () => void;
}

export default function Notification({ id, type, title, message, onClose }: NotificationProps) {
  const colors = {
    success: 'border-green-500 bg-green-500/10',
    warning: 'border-yellow-500 bg-yellow-500/10',
    error: 'border-red-500 bg-red-500/10',
    info: 'border-cyan-500 bg-cyan-500/10',
  };

  const icons = {
    success: '?',
    warning: '?',
    error: '?',
    info: 'i',
  };

  return (
    <div 
      className={`notification-toast  border-l-4 p-4 mb-2 rounded-r animate-slide-in-right`}
    >
      <div className="flex items-start gap-3">
        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-bold `}>
          {icons[type]}
        </div>
        
        <div className="flex-1">
          <h4 className="text-sm font-bold text-white mb-1">{title}</h4>
          <p className="text-xs text-slate-300">{message}</p>
        </div>

        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white transition-colors"
        >
          ?
        </button>
      </div>
    </div>
  );
}
