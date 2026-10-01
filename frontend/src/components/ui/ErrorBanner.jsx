import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default function ErrorBanner({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="border border-red-500/30 bg-red-500/10 text-red-400 p-4 rounded-lg flex items-center justify-between gap-3 my-3">
      <div className="flex items-center gap-2">
        <AlertCircle size={18} className="text-red-400 flex-shrink-0" />
        <span className="text-sm font-medium">{message}</span>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 px-3 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded text-xs font-medium transition"
        >
          <RefreshCw size={13} />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
}
