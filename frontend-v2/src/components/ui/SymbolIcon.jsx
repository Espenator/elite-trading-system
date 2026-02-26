import React, { useState, useEffect } from "react";
import clsx from "clsx";
import { getSymbolIconUrl, getSymbolInitials } from "../../lib/symbolIcons";

/**
 * Renders a symbol icon: logo image when available, otherwise initials in a pill.
 * Use in tables (OpenClaw candidates, positions) and KPI cards (indices).
 */
export default function SymbolIcon({
  symbol,
  size = "md",
  showSymbol = true,
  className,
  ...rest
}) {
  const [imgError, setImgError] = useState(false);
  const url = getSymbolIconUrl(symbol);
  const initials = getSymbolInitials(symbol);

  const sizeClasses = {
    sm: "w-6 h-6 text-[10px]",
    md: "w-8 h-8 text-xs",
    lg: "w-10 h-10 text-sm",
  };
  const iconSize = {
    sm: "w-6 h-6",
    md: "w-8 h-8",
    lg: "w-10 h-10",
  };

  const showLogo = url && !imgError;

  useEffect(() => setImgError(false), [symbol]);

  return (
    <span
      className={clsx("inline-flex items-center gap-2 shrink-0", className)}
      {...rest}
    >
      {showLogo ? (
        <img
          src={url}
          alt={symbol}
          className={clsx(iconSize[size], "object-contain rounded")}
          onError={() => setImgError(true)}
        />
      ) : (
        <span
          className={clsx(
            "rounded flex items-center justify-center font-semibold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30",
            sizeClasses[size]
          )}
          title={symbol}
        >
          {initials}
        </span>
      )}
      {showSymbol && (
        <span className="font-medium text-white/90 truncate">{symbol}</span>
      )}
    </span>
  );
}
