import React from 'react';
import Modal from '@leafygreen-ui/modal';
import Button from '@leafygreen-ui/button';
import { Body } from '@leafygreen-ui/typography';

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
    <Modal open={open} setOpen={onCancel}>
      <div style={{ padding: '24px' }}>
        <h2 style={{ marginBottom: '16px', fontSize: '20px', fontWeight: 600 }}>
          {title}
        </h2>
        <Body style={{ marginBottom: '24px' }}>
          {children}
        </Body>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <Button variant="default" onClick={onCancel}>
            Cancel
          </Button>
          <Button 
            variant={variant === 'danger' ? 'danger' : 'primary'}
            onClick={onConfirm}
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
