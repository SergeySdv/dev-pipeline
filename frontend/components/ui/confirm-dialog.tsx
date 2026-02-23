"use client";

import { AlertTriangle, Info, Trash2 } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";

export type ConfirmVariant = "default" | "destructive" | "warning";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmVariant;
  loading?: boolean;
  onConfirm: () => void | Promise<void>;
}

const variantConfig: Record<ConfirmVariant, { icon: typeof Info; iconClass: string; buttonClass: string }> = {
  default: {
    icon: Info,
    iconClass: "text-blue-500",
    buttonClass: "",
  },
  destructive: {
    icon: Trash2,
    iconClass: "text-destructive",
    buttonClass: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
  },
  warning: {
    icon: AlertTriangle,
    iconClass: "text-yellow-500",
    buttonClass: "bg-yellow-600 text-white hover:bg-yellow-700",
  },
};

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "default",
  loading = false,
  onConfirm,
}: ConfirmDialogProps) {
  const config = variantConfig[variant];
  const Icon = config.icon;

  const handleConfirm = async () => {
    try {
      await onConfirm();
      onOpenChange(false);
    } catch {
      // Let the parent handle the error
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-start gap-3">
            <div className={cn("mt-0.5", config.iconClass)}>
              <Icon className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <AlertDialogTitle>{title}</AlertDialogTitle>
              <AlertDialogDescription className="mt-2">{description}</AlertDialogDescription>
            </div>
          </div>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading}>{cancelText}</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            className={config.buttonClass}
            disabled={loading}
          >
            {loading ? "Processing..." : confirmText}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

/**
 * Hook-friendly confirmation dialog that can be triggered programmatically.
 */
interface UseConfirmOptions {
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmVariant;
}

export function createConfirmDialog() {
  let resolveRef: ((value: boolean) => void) | null = null;

  const confirm = (_options: UseConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      resolveRef = resolve;
    });
  };

  const handleConfirm = () => {
    resolveRef?.(true);
    resolveRef = null;
  };

  const handleCancel = () => {
    resolveRef?.(false);
    resolveRef = null;
  };

  return { confirm, handleConfirm, handleCancel };
}

/**
 * Delete confirmation dialog - preset for destructive delete actions.
 */
interface DeleteConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  itemName: string;
  itemType?: string;
  onConfirm: () => void | Promise<void>;
  loading?: boolean;
}

export function DeleteConfirmDialog({
  open,
  onOpenChange,
  itemName,
  itemType = "item",
  onConfirm,
  loading = false,
}: DeleteConfirmDialogProps) {
  return (
    <ConfirmDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Delete ${itemType}?`}
      description={`Are you sure you want to delete "${itemName}"? This action cannot be undone.`}
      confirmText="Delete"
      cancelText="Cancel"
      variant="destructive"
      loading={loading}
      onConfirm={onConfirm}
    />
  );
}

/**
 * Cancel confirmation dialog - for cancelling running processes.
 */
interface CancelConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  itemName: string;
  itemType?: string;
  onConfirm: () => void | Promise<void>;
  loading?: boolean;
}

export function CancelConfirmDialog({
  open,
  onOpenChange,
  itemName,
  itemType = "process",
  onConfirm,
  loading = false,
}: CancelConfirmDialogProps) {
  return (
    <ConfirmDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Cancel ${itemType}?`}
      description={`Are you sure you want to cancel "${itemName}"? This will stop the current operation.`}
      confirmText="Cancel"
      cancelText="Keep Running"
      variant="warning"
      loading={loading}
      onConfirm={onConfirm}
    />
  );
}
