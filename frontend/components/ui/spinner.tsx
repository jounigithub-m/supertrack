import React from 'react';
import { cn } from '@/lib/utils';

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * The size of the spinner
   * @default "md"
   */
  size?: 'sm' | 'md' | 'lg';
  
  /**
   * The color of the spinner
   * @default "primary"
   */
  variant?: 'primary' | 'secondary' | 'destructive' | 'muted';
  
  /**
   * Whether to show a centered spinner with overlay
   * @default false
   */
  fullScreen?: boolean;
  
  /**
   * Text to display underneath the spinner
   */
  text?: string;
}

/**
 * Spinner component for indicating loading states
 */
export function Spinner({
  size = 'md',
  variant = 'primary',
  fullScreen = false,
  text,
  className,
  ...props
}: SpinnerProps) {
  // Size classes
  const sizeClasses = {
    sm: 'h-4 w-4 border-2',
    md: 'h-8 w-8 border-3',
    lg: 'h-12 w-12 border-4',
  };
  
  // Variant (color) classes
  const variantClasses = {
    primary: 'border-t-primary',
    secondary: 'border-t-secondary',
    destructive: 'border-t-destructive',
    muted: 'border-t-muted-foreground',
  };

  const spinnerClass = cn(
    'rounded-full animate-spin border-solid border-background',
    sizeClasses[size],
    variantClasses[variant],
    className
  );

  // If fullScreen, return a fixed position spinner with overlay
  if (fullScreen) {
    return (
      <div
        className="fixed inset-0 flex flex-col items-center justify-center bg-background/80 z-50"
        {...props}
      >
        <div className={spinnerClass} />
        {text && <p className="mt-4 text-sm text-muted-foreground">{text}</p>}
      </div>
    );
  }

  // For text with spinner but not fullscreen
  if (text) {
    return (
      <div className="flex flex-col items-center justify-center" {...props}>
        <div className={spinnerClass} />
        <p className="mt-2 text-sm text-muted-foreground">{text}</p>
      </div>
    );
  }

  // Default: just return the spinner
  return <div className={spinnerClass} {...props} />;
}

export default Spinner;