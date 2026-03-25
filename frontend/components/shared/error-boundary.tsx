"use client";

import * as React from "react";

import { AlertTriangle, RefreshCw } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onRetry?: () => void;
  title?: string;
  description?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });
    // Log error to monitoring service
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    this.props.onRetry?.();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              {this.props.title || "Something went wrong"}
            </CardTitle>
            <CardDescription>
              {this.props.description || "An unexpected error occurred. Please try again."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {process.env.NODE_ENV === "development" && this.state.error && (
              <Alert variant="destructive">
                <AlertTitle>Error Details</AlertTitle>
                <AlertDescription className="font-mono text-xs">
                  {this.state.error.message}
                </AlertDescription>
              </Alert>
            )}
            <Button onClick={this.handleRetry} variant="outline">
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}

export interface AsyncErrorDisplayProps {
  error: Error | string | null;
  onRetry?: () => void;
  title?: string;
  className?: string;
  variant?: "alert" | "card";
}

export function AsyncErrorDisplay({
  error,
  onRetry,
  title = "Operation failed",
  className,
  variant = "alert",
}: AsyncErrorDisplayProps) {
  if (!error) return null;

  const errorMessage = typeof error === "string" ? error : error.message;

  if (variant === "card") {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted-foreground text-sm">{errorMessage}</p>
          {onRetry && (
            <Button onClick={onRetry} variant="outline" size="sm">
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Alert variant="destructive" className={className}>
      <AlertTriangle className="h-4 w-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="flex items-center justify-between gap-4">
        <span>{errorMessage}</span>
        {onRetry && (
          <Button onClick={onRetry} variant="outline" size="sm">
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}

export interface LoadingErrorWrapperProps {
  isLoading: boolean;
  error: Error | string | null;
  onRetry?: () => void;
  children: React.ReactNode;
  loadingComponent?: React.ReactNode;
  errorTitle?: string;
  className?: string;
}

export function LoadingErrorWrapper({
  isLoading,
  error,
  onRetry,
  children,
  loadingComponent,
  errorTitle,
  className,
}: LoadingErrorWrapperProps) {
  if (isLoading) {
    return (
      loadingComponent || (
        <div className={className}>
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="text-muted-foreground h-8 w-8 animate-spin" />
          </div>
        </div>
      )
    );
  }

  if (error) {
    return (
      <AsyncErrorDisplay
        error={error}
        onRetry={onRetry}
        title={errorTitle}
        className={className}
      />
    );
  }

  return <>{children}</>;
}
