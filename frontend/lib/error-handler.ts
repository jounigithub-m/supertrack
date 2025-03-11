import { ApiError } from './api-client';
import { toast } from '@/components/ui/use-toast';

/**
 * Error severity levels
 */
export enum ErrorSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

/**
 * Error category types
 */
export enum ErrorCategory {
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  VALIDATION = 'validation',
  NETWORK = 'network',
  SERVER = 'server',
  CLIENT = 'client',
  UNKNOWN = 'unknown',
}

/**
 * Extended error information with category and severity
 */
export interface EnhancedError extends ApiError {
  severity: ErrorSeverity;
  category: ErrorCategory;
  userMessage: string;
  timestamp: string;
  handled: boolean;
}

/**
 * Maps HTTP status codes to error categories
 */
const statusToCategory: Record<number, ErrorCategory> = {
  400: ErrorCategory.VALIDATION,
  401: ErrorCategory.AUTHENTICATION,
  403: ErrorCategory.AUTHORIZATION,
  404: ErrorCategory.CLIENT,
  422: ErrorCategory.VALIDATION,
  500: ErrorCategory.SERVER,
  502: ErrorCategory.SERVER,
  503: ErrorCategory.SERVER,
  504: ErrorCategory.SERVER,
};

/**
 * Maps error codes to user-friendly messages
 */
const errorMessages: Record<string, string> = {
  NETWORK_ERROR: 'Unable to connect to the server. Please check your internet connection and try again.',
  HTTP_401: 'Your session has expired. Please sign in again.',
  HTTP_403: 'You don\'t have permission to access this resource.',
  HTTP_404: 'The requested resource was not found.',
  HTTP_500: 'An unexpected server error occurred. Our team has been notified.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  DEFAULT: 'An error occurred. Please try again later.',
};

/**
 * Determines error severity based on category and status code
 */
function getSeverity(category: ErrorCategory, status?: number): ErrorSeverity {
  if (category === ErrorCategory.SERVER) {
    return ErrorSeverity.ERROR;
  }
  
  if (category === ErrorCategory.NETWORK) {
    return ErrorSeverity.WARNING;
  }
  
  if (category === ErrorCategory.AUTHENTICATION || category === ErrorCategory.AUTHORIZATION) {
    return ErrorSeverity.WARNING;
  }
  
  if (category === ErrorCategory.VALIDATION) {
    return ErrorSeverity.INFO;
  }
  
  if (status && status >= 500) {
    return ErrorSeverity.ERROR;
  }
  
  return ErrorSeverity.WARNING;
}

/**
 * Get a user-friendly message for the error
 */
function getUserMessage(error: ApiError): string {
  // Check for specific error code message
  if (error.code && errorMessages[error.code]) {
    return errorMessages[error.code];
  }
  
  // Check for HTTP status code message
  if (error.status && errorMessages[`HTTP_${error.status}`]) {
    return errorMessages[`HTTP_${error.status}`];
  }
  
  // Use the original error message if it seems user-friendly
  if (error.message && !error.message.includes('Error') && !error.message.includes('Exception')) {
    return error.message;
  }
  
  // Fall back to default message
  return errorMessages.DEFAULT;
}

/**
 * Categorize an error based on its properties
 */
function categorizeError(error: ApiError): ErrorCategory {
  // Check for network errors
  if (error.code === 'NETWORK_ERROR') {
    return ErrorCategory.NETWORK;
  }
  
  // Categorize based on HTTP status
  if (error.status && statusToCategory[error.status]) {
    return statusToCategory[error.status];
  }
  
  // Check for validation errors
  if (error.errors || error.code === 'VALIDATION_ERROR') {
    return ErrorCategory.VALIDATION;
  }
  
  // Default to unknown
  return ErrorCategory.UNKNOWN;
}

/**
 * Process an API error into an enhanced error with more context
 */
export function processError(error: ApiError): EnhancedError {
  const category = categorizeError(error);
  const severity = getSeverity(category, error.status);
  const userMessage = getUserMessage(error);
  
  return {
    ...error,
    severity,
    category,
    userMessage,
    timestamp: new Date().toISOString(),
    handled: false,
  };
}

/**
 * Log an error for debugging purposes
 */
export function logError(error: EnhancedError, context?: any): void {
  // In development, log to console
  if (process.env.NODE_ENV === 'development') {
    console.group(`[${error.severity.toUpperCase()}] ${error.category}`);
    console.error('Error:', error.message);
    console.error('User Message:', error.userMessage);
    console.error('Code:', error.code);
    console.error('Status:', error.status);
    
    if (error.errors) {
      console.error('Validation Errors:', error.errors);
    }
    
    if (context) {
      console.error('Context:', context);
    }
    
    if (error.originalError) {
      console.error('Original Error:', error.originalError);
    }
    
    console.groupEnd();
  }
  
  // In production, we would send to a logging service
  if (process.env.NODE_ENV === 'production') {
    // TODO: Implement production error logging
    // Example: Send to a service like Sentry
    // captureException(error);
  }
}

/**
 * Display an error to the user
 */
export function displayError(error: EnhancedError): void {
  // Don't display errors that should be handled silently
  if (error.severity === ErrorSeverity.CRITICAL) {
    // For critical errors, we might want a more intrusive UI like a modal
    toast({
      title: 'Critical Error',
      description: error.userMessage,
      variant: 'destructive',
    });
  } else {
    // Use toast notifications for most errors
    toast({
      title: error.category === ErrorCategory.VALIDATION ? 'Please check your input' : 'Error',
      description: error.userMessage,
      variant: error.severity === ErrorSeverity.ERROR ? 'destructive' : 
               error.severity === ErrorSeverity.WARNING ? 'warning' : 'default',
    });
  }
}

/**
 * Main error handler function that processes, logs, and displays errors
 */
export function handleError(error: unknown, context?: any): EnhancedError {
  // First, ensure we have a properly formatted API error
  const apiError: ApiError = error as ApiError;
  
  // Process into an enhanced error
  const enhancedError = processError(apiError);
  
  // Log the error
  logError(enhancedError, context);
  
  // Display to user unless it's been marked as handled
  if (!enhancedError.handled) {
    displayError(enhancedError);
    enhancedError.handled = true;
  }
  
  return enhancedError;
}

/**
 * Format validation errors into a user-friendly string
 */
export function formatValidationErrors(errors?: Record<string, string[]>): string {
  if (!errors) return '';
  
  const fields = Object.keys(errors);
  if (fields.length === 0) return '';
  
  if (fields.length === 1) {
    const field = fields[0];
    const fieldErrors = errors[field];
    
    if (fieldErrors.length === 1) {
      return fieldErrors[0];
    }
    
    return `Issues with ${field}: ${fieldErrors.join(', ')}`;
  }
  
  return `Please fix the following issues: ${fields.join(', ')}`;
}

export default handleError;