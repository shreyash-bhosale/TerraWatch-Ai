import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "outline" | "ghost" | "destructive" | "warning";
  size?: "default" | "sm" | "lg" | "icon";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", disabled, ...props }, ref) => {
    const variantStyles = {
      default: "bg-blue-600 text-white hover:bg-blue-500 shadow-sm shadow-blue-500/20 active:bg-blue-700",
      secondary: "bg-slate-800 text-slate-100 hover:bg-slate-700 border border-slate-700",
      outline: "border border-slate-700 bg-transparent hover:bg-slate-800 text-slate-200",
      ghost: "hover:bg-slate-800/60 text-slate-300 hover:text-slate-100",
      destructive: "bg-red-600 text-white hover:bg-red-500 active:bg-red-700",
      warning: "bg-amber-600 text-white hover:bg-amber-500 active:bg-amber-700",
    }[variant];

    const sizeStyles = {
      default: "h-9 px-4 py-2 text-sm",
      sm: "h-8 px-3 text-xs rounded-md",
      lg: "h-10 px-6 text-base rounded-md",
      icon: "h-9 w-9 p-0 flex items-center justify-center",
    }[size];

    return (
      <button
        ref={ref}
        disabled={disabled}
        className={cn(
          "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:pointer-events-none disabled:opacity-50",
          variantStyles,
          sizeStyles,
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
