export function LoadingSpinner({ size = 'md', text = 'Loading...' }) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <div className="flex items-center justify-center gap-2 py-4">
      <div
        className={`${sizeClasses[size]} border-2 border-gray-600 border-t-emerald-500 rounded-full animate-spin`}
      />
      {text && <span className="text-gray-400 text-sm">{text}</span>}
    </div>
  );
}

export function EmptyState({ message = 'No data available', icon }) {
  return (
    <div className="text-center py-8 text-gray-400">
      {icon && <div className="mb-2">{icon}</div>}
      <p>{message}</p>
    </div>
  );
}

export function ErrorMessage({ message = 'Something went wrong', onRetry }) {
  return (
    <div className="p-4 bg-red-900/30 border border-red-800 rounded-lg text-red-400">
      <p>{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 text-sm text-red-300 hover:text-red-200 underline"
        >
          Try again
        </button>
      )}
    </div>
  );
}