import React, { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import Toast, { Variant } from '@leafygreen-ui/toast';

interface ToastMessage {
  id: string;
  title: string;
  body?: string;
  variant: Variant;
}

interface ToastContextType {
  showToast: (title: string, body?: string, variant?: Variant) => void;
  showSuccess: (title: string, body?: string) => void;
  showError: (title: string, body?: string) => void;
  showWarning: (title: string, body?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((title: string, body?: string, variant: Variant = 'success') => {
    const id = Date.now().toString();
    setToasts((prev) => [...prev, { id, title, body, variant }]);
    
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const showSuccess = useCallback((title: string, body?: string) => {
    showToast(title, body, 'success');
  }, [showToast]);

  const showError = useCallback((title: string, body?: string) => {
    showToast(title, body, 'warning');
  }, [showToast]);

  const showWarning = useCallback((title: string, body?: string) => {
    showToast(title, body, 'note');
  }, [showToast]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast, showSuccess, showError, showWarning }}>
      {children}
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          title={toast.title}
          body={toast.body}
          variant={toast.variant}
          open={true}
          close={() => removeToast(toast.id)}
        />
      ))}
    </ToastContext.Provider>
  );
}
