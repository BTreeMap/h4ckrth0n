import { InputHTMLAttributes, forwardRef, useId, useState } from "react";
import { cn } from "../lib/utils";
import { Label } from "./Label";
import { Eye, EyeOff } from "lucide-react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, label, error, id, ...props }, ref) => {
    const generatedId = useId();
    const inputId = id || generatedId;
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = type === "password";

    const handleTogglePassword = () => {
      setShowPassword(!showPassword);
    };

    return (
      <div className="space-y-2">
        {label && <Label htmlFor={inputId}>{label}</Label>}
        <div className="relative">
          <input
            id={inputId}
            type={isPassword ? (showPassword ? "text" : "password") : type}
            className={cn(
              "flex h-10 w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm ring-offset-surface file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
              error && "border-danger focus-visible:ring-danger",
              isPassword && "pr-10",
              className
            )}
            ref={ref}
            {...props}
          />
          {isPassword && (
            <button
              type="button"
              onClick={handleTogglePassword}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-md p-1"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          )}
        </div>
        {error && <p className="text-sm text-danger">{error}</p>}
      </div>
    );
  },
);
Input.displayName = "Input";

export { Input };
