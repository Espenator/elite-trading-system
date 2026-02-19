// PAGE HEADER - Consistent title, description, and icon for all pages
// Matches Operator Console style: cyan icon, bold white title, light gray description

export default function PageHeader({
  icon: Icon,
  title,
  description,
  children,
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
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
  );
}
