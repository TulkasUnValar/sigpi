import * as React from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  description?: string;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

/**
 * Stat card with gradient icon background and optional trend indicator.
 * Used for KPIs and dashboard metrics.
 */
export function StatCard({
  title,
  value,
  icon: Icon,
  description,
  trend,
  className,
}: StatCardProps) {
  return (
    <Card className={cn("card-attio rounded-xl", className)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wider text-gray-500">
          {title}
        </CardTitle>
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-surface-100 dark:bg-surface-200">
          <Icon className="h-4 w-4 text-foreground" aria-hidden="true" />
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-semibold tracking-tight">{value}</p>
        {description && (
          <p className="mt-1 text-xs text-gray-500">{description}</p>
        )}
        {trend && (
          <div
            className={cn(
              "mt-2 inline-flex items-center gap-1 text-xs font-medium",
              trend === "up" && "text-green-600 dark:text-green-500",
              trend === "down" && "text-red-600 dark:text-red-500",
              trend === "neutral" && "text-gray-500",
            )}
          >
            {trend === "up" && "↑"}
            {trend === "down" && "↓"}
            {trend === "neutral" && "→"}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
