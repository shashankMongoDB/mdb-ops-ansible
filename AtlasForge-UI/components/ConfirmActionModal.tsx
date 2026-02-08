import React from 'react';
import ConfirmationModal from '@leafygreen-ui/confirm-modal';

interface ConfirmActionModalProps {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  title: string;
  children: React.ReactNode;
  confirmText?: string;
  variant?: 'default' | 'danger';
}

export function ConfirmActionModal({
  open,
  onConfirm,
  onCancel,
  title,
  children,
  confirmText = 'Confirm',
  variant = 'default',
}: ConfirmActionModalProps) {
  return (
    <ConfirmationModal
      open={open}
      title={title}
      onConfirm={onConfirm}
      onCancel={onCancel}
      confirmButtonProps={{
        variant: variant === 'danger' ? 'danger' : 'primary',
        children: confirmText,
      }}
    >
      {children}
    </ConfirmationModal>
  );
}
