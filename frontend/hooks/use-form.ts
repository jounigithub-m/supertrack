import { useState, useCallback, ChangeEvent, FormEvent } from 'react';

type ValidationFn<T> = (values: T) => Partial<Record<keyof T, string>>;

interface UseFormOptions<T> {
  initialValues: T;
  onSubmit: (values: T) => void | Promise<void>;
  validate?: ValidationFn<T>;
  onError?: (errors: Partial<Record<keyof T, string>>) => void;
}

/**
 * Custom hook for form handling with validation
 */
export function useForm<T extends Record<string, any>>({
  initialValues,
  onSubmit,
  validate,
  onError,
}: UseFormOptions<T>) {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  // Handle input change
  const handleChange = useCallback((
    e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    const fieldName = name as keyof T;
    
    // Handle checkbox inputs differently
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setValues((prev) => ({ ...prev, [fieldName]: checked }));
    } else {
      setValues((prev) => ({ ...prev, [fieldName]: value }));
    }
    
    // Clear error when field is changed
    if (errors[fieldName]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[fieldName];
        return newErrors;
      });
    }
  }, [errors]);

  // Handle blur event to mark field as touched
  const handleBlur = useCallback((e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name } = e.target;
    const fieldName = name as keyof T;
    
    setTouched((prev) => ({ ...prev, [fieldName]: true }));
    
    // Validate on blur if validate function is provided
    if (validate) {
      const validationErrors = validate(values);
      if (validationErrors[fieldName]) {
        setErrors((prev) => ({ ...prev, [fieldName]: validationErrors[fieldName] }));
      }
    }
  }, [values, validate]);

  // Set form value programmatically
  const setValue = useCallback(<K extends keyof T>(
    field: K,
    value: T[K]
  ) => {
    setValues((prev) => ({ ...prev, [field]: value }));
    
    // Clear error when field is set
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  }, [errors]);

  // Set multiple form values at once
  const setMultipleValues = useCallback((newValues: Partial<T>) => {
    setValues((prev) => ({ ...prev, ...newValues }));
    
    // Clear errors for updated fields
    const updatedFields = Object.keys(newValues) as Array<keyof T>;
    if (updatedFields.some((field) => errors[field])) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        updatedFields.forEach((field) => {
          delete newErrors[field];
        });
        return newErrors;
      });
    }
  }, [errors]);

  // Reset the form to initial values
  const resetForm = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
    setIsSubmitted(false);
  }, [initialValues]);

  // Handle form submission
  const handleSubmit = useCallback(async (e?: FormEvent) => {
    if (e) {
      e.preventDefault();
    }
    
    setIsSubmitted(true);
    
    // Validate all fields if validation is provided
    if (validate) {
      const validationErrors = validate(values);
      const hasErrors = Object.keys(validationErrors).length > 0;
      
      setErrors(validationErrors);
      
      // Mark all fields as touched on submit
      const allTouched: Partial<Record<keyof T, boolean>> = {};
      Object.keys(values).forEach((key) => {
        allTouched[key as keyof T] = true;
      });
      setTouched(allTouched);
      
      if (hasErrors) {
        onError?.(validationErrors);
        return;
      }
    }
    
    setIsSubmitting(true);
    
    try {
      await onSubmit(values);
    } catch (error) {
      console.error('Form submission error:', error);
    } finally {
      setIsSubmitting(false);
    }
  }, [values, validate, onSubmit, onError]);

  // Check if a field has an error and has been touched
  const hasFieldError = useCallback((field: keyof T) => {
    return !!(touched[field] && errors[field]);
  }, [touched, errors]);

  // Get field error message
  const getFieldError = useCallback((field: keyof T) => {
    return hasFieldError(field) ? errors[field] : '';
  }, [hasFieldError, errors]);

  return {
    values,
    errors,
    touched,
    isSubmitting,
    isSubmitted,
    handleChange,
    handleBlur,
    handleSubmit,
    setValue,
    setMultipleValues,
    resetForm,
    hasFieldError,
    getFieldError,
  };
}

export default useForm;