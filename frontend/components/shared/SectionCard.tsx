import * as React from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface SectionCardProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

/**
 * Section card with icon header and consistent styling.
 * Used for dashboard sections and grouped content.
 */
export function SectionCard({
  title,
  description,
  icon: Icon,
  action,
  children,
  className,
}: SectionCardProps) {
  return (
    <Card className={cn("card-attio rounded-xl", className)}>
      <CardHeader className="border-b border-border-subtle dark:border-border-default">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {Icon && (
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-surface-100 dark:bg-surface-200">
                <Icon className="h-3.5 w-3.5 text-foreground" aria-hidden="true" />
              </div>
            )}
            <div>
              <CardTitle className="text-base font-semibold">{title}</CardTitle>
              {description && (
                <p className="text-xs text-gray-500">{description}</p>
              )}
            </div>
          </div>
          {action && <div>{action}</div>}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
