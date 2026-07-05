import * as React from "react";

import { cn } from "@/lib/utils";

export function Separator({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      className={cn("h-px w-full bg-[#313131]", className)}
      role="separator"
      {...props}
    />
  );
}
