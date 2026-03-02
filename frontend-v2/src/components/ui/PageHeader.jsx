// PAGE HEADER - Consistent title, description, and icon for all pages
// Matches Operator Console style: cyan icon, bold white title, light gray description
// Supports optional top/bottom decorative banner images

export default function PageHeader({
  icon: Icon,
  title,
  description,
  children,
  topImageSrc,
  bottomImageSrc,
}) {
  return (
    <div className="relative overflow-hidden">
      {topImageSrc && (
        <img
          src={topImageSrc}
          alt=""
          aria-hidden="true"
          className="pointer-events-none select-none absolute left-0 top-0 w-full opacity-80"
          style={{ mixBlendMode: "screen" }}
        />
      )}
      {bottomImageSrc && (
        <img
          src={bottomImageSrc}
          alt=""
          aria-hidden="true"
          className="pointer-events-none select-none absolute left-0 bottom-0 w-full opacity-70"
          style={{ mixBlendMode: "screen" }}
        />
      )}

      <div className="relative z-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            {Icon && <Icon className="w-7 h-7 text-cyan-400 shrink-0" />}
            {title}
          </h1>
          {description && (
            <p className="text-gray-400 text-sm mt-1">{description}</p>
          )}
        </div>
        {children && (
          <div className="flex items-center gap-3 flex-wrap shrink-0">
            {children}
          </div>
        )}
      </div>
    </div>
  );
}
