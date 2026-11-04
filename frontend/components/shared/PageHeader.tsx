import * as React from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  icon?: LucideIcon;
  action?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}

/**
 * Page header with icon, title hierarchy, optional description, and action slot.
 * Used at the top of all pages for consistent visual hierarchy.
 */
export function PageHeader({
  title,
  description,
  icon: Icon,
  action,
  children,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between", className)}>
      <div className="flex items-start gap-3">
        {Icon && (
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border-subtle bg-surface-50 dark:border-border-default dark:bg-surface-100">
            <Icon className="h-5 w-5 text-foreground" aria-hidden="true" />
          </div>
        )}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
          {description && (
            <p className="text-sm text-gray-500">{description}</p>
          )}
        </div>
      </div>
      {(action || children) && (
        <div className="flex items-center gap-2">
          {action}
          {children}
        </div>
      )}
    </div>
  );
}
