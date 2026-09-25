"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

function Dialog({ open, onOpenChange, children }: DialogProps) {
  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === "Escape") onOpenChange(false);
      };
      document.addEventListener("keydown", handleEscape);
      return () => {
        document.body.style.overflow = "";
        document.removeEventListener("keydown", handleEscape);
      };
    }
    document.body.style.overflow = "";
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={() => onOpenChange(false)} />
      <div className="relative z-50">{children}</div>
    </div>
  );
}

function DialogContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "w-full max-w-lg rounded-xl border bg-white p-6 shadow-2xl dark:bg-zinc-900 dark:border-zinc-800",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

function DialogHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col space-y-1.5 mb-4", className)} {...props} />;
}

function DialogTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("text-lg font-semibold", className)} {...props} />;
}

function DialogDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-zinc-500", className)} {...props} />;
}

function DialogFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex justify-end gap-2 mt-4", className)} {...props} />;
}

function ConfirmDialog({ open, onOpenChange, title, description, onConfirm, variant = "destructive" }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  onConfirm: () => void;
  variant?: "destructive" | "default";
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button variant={variant} onClick={() => { onConfirm(); onOpenChange(false); }}>
            Confirm
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PromptDialog({ open, onOpenChange, title, description, placeholder, onSubmit, type = "text" }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  placeholder?: string;
  onSubmit: (value: string) => void;
  type?: string;
}) {
  const [value, setValue] = React.useState("");
  React.useEffect(() => { if (open) setValue(""); }, [open]);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <Input value={value} onChange={e => setValue(e.target.value)} placeholder={placeholder} type={type} autoFocus onKeyDown={e => { if (e.key === "Enter" && value.trim()) { onSubmit(value.trim()); onOpenChange(false); } }} />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={() => { if (value.trim()) { onSubmit(value.trim()); onOpenChange(false); } }}>Submit</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PromptAreaDialog({ open, onOpenChange, title, description, placeholder, onSubmit }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  placeholder?: string;
  onSubmit: (value: string) => void;
}) {
  const [value, setValue] = React.useState("");
  React.useEffect(() => { if (open) setValue(""); }, [open]);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <textarea value={value} onChange={e => setValue(e.target.value)} placeholder={placeholder} rows={4} className="w-full px-3 py-2 text-sm border rounded-lg dark:bg-zinc-800" autoFocus />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={() => { if (value.trim()) { onSubmit(value.trim()); onOpenChange(false); } }}>Submit</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, ConfirmDialog, PromptDialog, PromptAreaDialog };

