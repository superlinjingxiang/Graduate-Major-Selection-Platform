import { Slot } from "@radix-ui/react-slot";
import { type ButtonHTMLAttributes, forwardRef, type ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "quiet";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean;
  children: ReactNode;
  variant?: ButtonVariant;
};

const variantClassNames: Record<ButtonVariant, string> = {
  primary: "button button-primary",
  secondary: "button button-secondary",
  quiet: "button button-quiet",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { asChild = false, children, className = "", type = "button", variant = "primary", ...props },
  ref,
) {
  const Component = asChild ? Slot : "button";
  const componentProps = asChild ? {} : { type };

  return (
    <Component
      className={`${variantClassNames[variant]} ${className}`.trim()}
      ref={ref}
      {...componentProps}
      {...props}
    >
      {children}
    </Component>
  );
});

export type { ButtonProps };
