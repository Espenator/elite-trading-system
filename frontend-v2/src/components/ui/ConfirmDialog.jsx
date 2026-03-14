import { useState, useEffect, useRef, useCallback } from "react";

/**
 * Reusable confirmation modal for dangerous/destructive actions.
 *
 * Props:
 *   open        – boolean, controls visibility
 *   onConfirm   – called when user clicks Confirm
 *   onCancel    – called when user clicks Cancel or presses Escape
 *   title       – modal heading text
 *   description – body text explaining the consequences
 *   confirmText – label for the confirm button (default "Confirm")
 *   variant     – "danger" (red confirm) or "warning" (amber confirm), default "danger"
 *   requireType – if set, user must type this exact string to enable the confirm button
 */
export default function ConfirmDialog({
  open,
  onConfirm,
  onCancel,
  title = "Are you sure?",
  description = "",
  confirmText = "Confirm",
  variant = "danger",
  requireType = "",
}) {
  const [typedConfirm, setTypedConfirm] = useState("");
  const cancelRef = useRef(null);
  const dialogRef = useRef(null);

  // Reset typed confirmation when dialog opens/closes
  useEffect(() => {
    if (open) setTypedConfirm("");
  }, [open]);

  // Auto-focus Cancel button when dialog opens (safety: default action is cancel)
  useEffect(() => {
    if (open) {
      // Small delay to ensure DOM is ready
      const id = setTimeout(() => cancelRef.current?.focus(), 50);
      return () => clearTimeout(id);
    }
  }, [open]);

  // Close on Escape key
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onCancel?.();
      }
      // Focus trap: Tab within the dialog
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    },
    [onCancel]
  );

  useEffect(() => {
    if (!open) return;
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, handleKeyDown]);

  if (!open) return null;

  const confirmColors =
    variant === "warning"
      ? "bg-amber-600 hover:bg-amber-500 focus:ring-amber-500/50 text-white"
      : "bg-red-600 hover:bg-red-500 focus:ring-red-500/50 text-white";

  return (
    <div
      className="fixed inset-0 z-[9998] flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
    >
      {/* Dark overlay backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Modal */}
      <div
        ref={dialogRef}
        className="relative z-10 w-full max-w-md mx-4 rounded-lg border border-[#1e293b] bg-[#111827] shadow-2xl shadow-black/50"
      >
        {/* Header */}
        <div className="px-5 pt-5 pb-2">
          <h2
            id="confirm-dialog-title"
            className="text-base font-bold text-white font-mono tracking-wide"
          >
            {title}
          </h2>
        </div>

        {/* Body */}
        {description && (
          <div className="px-5 pb-4">
            <p className="text-sm text-[#94a3b8] leading-relaxed">
              {description}
            </p>
          </div>
        )}

        {/* Typed confirmation */}
        {requireType && (
          <div className="px-5 pb-4">
            <label className="text-sm text-[#94a3b8]">
              Type "<span className="text-white font-bold">{requireType}</span>" to confirm:
            </label>
            <input
              type="text"
              value={typedConfirm}
              onChange={(e) => setTypedConfirm(e.target.value)}
              className="mt-1 w-full px-3 py-2 bg-[#0B0E14] border border-[#374151] rounded text-white text-sm font-mono focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500/50"
              placeholder={requireType}
              autoComplete="off"
              spellCheck={false}
            />
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-[#1e293b] bg-[#0B0E14]/50 rounded-b-lg">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-[#94a3b8] bg-[#1e293b] hover:bg-[#374151] border border-[#374151] rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-[#64748b]/50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={!!requireType && typedConfirm !== requireType}
            className={`px-4 py-2 text-sm font-bold rounded-md transition-colors focus:outline-none focus:ring-2 ${confirmColors} ${requireType && typedConfirm !== requireType ? "opacity-40 cursor-not-allowed" : ""}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
