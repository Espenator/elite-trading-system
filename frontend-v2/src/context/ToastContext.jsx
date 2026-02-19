import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
} from "react";
import clsx from "clsx";
import { CheckCircle, XCircle, Info, X } from "lucide-react";

const ToastContext = createContext(null);

const TOAST_TTL_MS = 4000;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const add = useCallback((type, message, id = Date.now() + Math.random()) => {
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, TOAST_TTL_MS);
  }, []);

  const remove = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useMemo(
    () => ({
      success: (msg) => add("success", msg),
      error: (msg) => add("error", msg),
      info: (msg) => add("info", msg),
    }),
    [add],
  );

  return (
    <ToastContext.Provider value={{ toast, add, remove }}>
      {children}
      <div
        className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none"
        aria-live="polite"
      >
        <div className="flex flex-col gap-2 pointer-events-auto">
          {toasts.map((t) => (
            <ToastItem key={t.id} {...t} onDismiss={() => remove(t.id)} />
          ))}
        </div>
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ id, type, message, onDismiss }) {
  const icons = {
    success: CheckCircle,
    error: XCircle,
    info: Info,
  };
  const Icon = icons[type] || Info;
  const styles = {
    success: "border-emerald-500/50 bg-emerald-500/15 text-emerald-300",
    error: "border-red-500/50 bg-red-500/15 text-red-300",
    info: "border-cyan-500/50 bg-cyan-500/15 text-cyan-300",
  };

  return (
    <div
      role="alert"
      className={clsx(
        "flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg min-w-[280px] max-w-[420px]",
        styles[type] || styles.info,
      )}
    >
      <Icon className="w-5 h-5 flex-shrink-0" />
      <p className="text-sm font-medium flex-1">{message}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="p-1 rounded hover:bg-white/10 transition-colors"
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx.toast;
}
