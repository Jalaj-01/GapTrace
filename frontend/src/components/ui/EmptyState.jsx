import React from 'react';
import { Inbox } from 'lucide-react';

export default function EmptyState({
  icon: Icon = Inbox,
  title = 'No records found',
  description = 'There is currently no data available for this section.',
  actionLabel,
  onAction,
}) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-subtle rounded-lg bg-card/40 my-4">
      <div className="p-3 bg-muted rounded-full mb-3 text-secondary">
        <Icon size={24} />
      </div>
      <h3 className="text-base font-semibold text-primary mb-1">{title}</h3>
      <p className="text-sm text-secondary max-w-md mb-4">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="px-4 py-2 bg-primary text-primary-contrast rounded-md text-sm font-medium hover:opacity-90 transition"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
