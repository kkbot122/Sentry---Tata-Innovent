import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-2 rounded-[4px] border px-2 py-1 font-mono text-xs uppercase tracking-[0.85px]",
  {
    variants: {
      variant: {
        default: "border-[#313131] bg-[#141414] text-[#a7a7a7]",
        active: "border-[#6798ff] bg-[#141414] text-white",
        healthy: "border-[#313131] bg-[#141414] text-white",
        warning: "border-[#313131] bg-[#141414] text-white",
        critical: "border-[#313131] bg-[#141414] text-white",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, className }))} {...props} />
  );
}
