import React from 'react';

export function LoadingSpinner({ size = 20, text = 'Loading data...' }) {
  return (
    <div className="flex items-center justify-center p-6 gap-3 text-secondary text-sm">
      <div
        className="border-2 border-t-transparent border-primary rounded-full animate-spin"
        style={{ width: size, height: size }}
      />
      {text && <span>{text}</span>}
    </div>
  );
}

export function SkeletonCard({ count = 3, height = 120 }) {
  return (
    <div className="space-y-4 w-full">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="skeleton-loader rounded-lg border border-subtle p-4"
          style={{ height }}
        >
          <div className="h-4 bg-muted rounded w-1/3 mb-3 animate-pulse" />
          <div className="h-3 bg-muted rounded w-3/4 mb-2 animate-pulse" />
          <div className="h-3 bg-muted rounded w-1/2 animate-pulse" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div className="w-full border border-subtle rounded-lg overflow-hidden">
      <div className="bg-muted p-3 flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="h-4 bg-secondary rounded flex-1 animate-pulse" />
        ))}
      </div>
      <div className="divide-y divide-subtle">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="p-3 flex gap-4 items-center">
            {Array.from({ length: cols }).map((_, c) => (
              <div key={c} className="h-3 bg-muted rounded flex-1 animate-pulse" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
