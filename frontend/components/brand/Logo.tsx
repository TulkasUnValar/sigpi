import * as React from "react";
import { BookOpenCheck } from "lucide-react";
import { cn } from "@/lib/utils";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  showTagline?: boolean;
  className?: string;
}

const sizeConfig = {
  sm: { icon: 16, text: "text-base", tagline: "text-[10px]" },
  md: { icon: 20, text: "text-lg", tagline: "text-xs" },
  lg: { icon: 28, text: "text-2xl", tagline: "text-sm" },
};

/**
 * SIGPI brand logo — text-based with icon.
 * Uses the brand gradient for visual identity.
 */
export function Logo({ size = "md", showTagline = false, className }: LogoProps) {
  const config = sizeConfig[size];

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex items-center justify-center rounded-lg border border-border-subtle bg-surface-50 p-1.5 dark:border-border-default dark:bg-surface-100">
        <BookOpenCheck
          className="text-foreground"
          width={config.icon}
          height={config.icon}
          aria-hidden="true"
        />
      </div>
      <div className="flex flex-col">
        <span
          className={cn(
            "font-semibold tracking-tight text-foreground",
            config.text,
          )}
        >
          SIGPI
        </span>
        {showTagline && (
          <span className={cn("text-muted-foreground", config.tagline)}>
            Gestión de Investigación
          </span>
        )}
      </div>
    </div>
  );
}
