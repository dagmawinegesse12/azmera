"use client";

import { type ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  isLoading?: boolean;
  icon?: ReactNode;
}

export function EmptyState({
  title,
  description,
  isLoading = false,
  icon,
}: EmptyStateProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 my-16 text-text-muted">
        <span
          className="block h-8 w-8 animate-spin rounded-full border-2 border-accent-green border-t-transparent"
          role="status"
          aria-label="Loading"
        />
        <span className="text-sm">Loading…</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-3 my-16 text-center text-text-muted">
      {icon !== undefined && (
        <div className="flex h-12 w-12 items-center justify-center opacity-50">
          {icon}
        </div>
      )}
      <p className="text-sm font-medium text-text-secondary">{title}</p>
      {description !== undefined && (
        <p className="max-w-sm text-xs text-text-muted">{description}</p>
      )}
    </div>
  );
}
