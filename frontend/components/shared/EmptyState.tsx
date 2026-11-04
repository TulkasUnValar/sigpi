import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
}

/** Empty-data placeholder with optional icon and action. */
export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
}: EmptyStateProps) {
  return (
    <div className="card-attio flex flex-col items-center justify-center gap-3 rounded-xl p-12 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-surface-100 dark:bg-surface-200">
        <Icon
          className="h-7 w-7 text-gray-400 dark:text-gray-500"
          aria-hidden="true"
          aria-label={title}
        />
      </div>
      <p className="text-base font-semibold">{title}</p>
      {description ? (
        <p className="max-w-sm text-sm text-gray-500">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
