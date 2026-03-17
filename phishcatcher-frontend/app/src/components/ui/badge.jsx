import * as React from "react";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-violet-500 text-white hover:bg-violet-600",
        secondary: "border-transparent bg-secondary-30 text-white hover:bg-secondary-30/80",
        destructive: "border-transparent bg-pink-500 text-white hover:bg-pink-600",
        outline: "text-violet-400 border-violet-500/30",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

function Badge({ className, variant, ...props }) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
