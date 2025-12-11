import { ReactNode } from "react";
import { Button } from "./ui/button";
import { cn } from "@/lib/utils";

interface LinkProps {
  children?: ReactNode;
  className?: string;
}

export function Link({
  children,
  onclick,
  className = "",
}: LinkProps & { onclick: any }) {
  return (
    <Button
      variant="link"
      onClick={onclick}
      className={cn(` hover:no-underline`, className ? className : null)}
    >
      {children}
    </Button>
  );
}
