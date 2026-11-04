import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const statusBadgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        draft: "bg-status-draft text-status-draft",
        submitted: "bg-status-submitted text-status-submitted",
        review: "bg-status-review text-status-review",
        observed: "bg-status-observed text-status-observed",
        approved: "bg-status-approved text-status-approved",
        execution: "bg-status-execution text-status-execution",
        suspended: "bg-status-suspended text-status-suspended",
        finalized: "bg-status-finalized text-status-finalized",
        closed: "bg-status-closed text-status-closed",
        rejected: "bg-status-rejected text-status-rejected",
        cancelled: "bg-status-cancelled text-status-cancelled",
      },
    },
    defaultVariants: {
      variant: "draft",
    },
  }
);

const dotVariants = cva("h-1.5 w-1.5 rounded-full", {
  variants: {
    variant: {
      draft: "bg-status-draft",
      submitted: "bg-status-submitted",
      review: "bg-status-review",
      observed: "bg-status-observed",
      approved: "bg-status-approved",
      execution: "bg-status-execution",
      suspended: "bg-status-suspended",
      finalized: "bg-status-finalized",
      closed: "bg-status-closed",
      rejected: "bg-status-rejected",
      cancelled: "bg-status-cancelled",
    },
  },
  defaultVariants: {
    variant: "draft",
  },
});

export interface StatusBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof statusBadgeVariants> {
  showDot?: boolean;
}

const StatusBadge = React.forwardRef<HTMLSpanElement, StatusBadgeProps>(
  ({ className, variant, showDot = true, children, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(statusBadgeVariants({ variant }), className)}
        {...props}
      >
        {showDot && <span className={cn(dotVariants({ variant }))} aria-hidden="true" />}
        {children}
      </span>
    );
  }
);
StatusBadge.displayName = "StatusBadge";

export { StatusBadge, statusBadgeVariants };
