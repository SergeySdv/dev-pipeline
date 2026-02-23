"use client";

import * as React from "react";

import { Loader2, MessageSquare } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export interface ClarificationEntry {
  question: string;
  answer: string;
}

export interface ClarificationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: { entries: ClarificationEntry[]; notes?: string }) => Promise<void> | void;
  isLoading?: boolean;
  title?: string;
  description?: string;
  specName?: string;
  showNotes?: boolean;
}

export function ClarificationDialog({
  open,
  onOpenChange,
  onSubmit,
  isLoading = false,
  title = "Clarify Specification",
  description = "Add a clarification entry or notes to the spec.",
  specName,
  showNotes = true,
}: ClarificationDialogProps) {
  const [question, setQuestion] = React.useState("");
  const [answer, setAnswer] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  const resetForm = React.useCallback(() => {
    setQuestion("");
    setAnswer("");
    setNotes("");
    setError(null);
  }, []);

  const handleOpenChange = React.useCallback(
    (newOpen: boolean) => {
      if (!newOpen) {
        resetForm();
      }
      onOpenChange(newOpen);
    },
    [onOpenChange, resetForm]
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const hasEntry = question.trim() && answer.trim();
    const hasNotesContent = notes.trim();

    if (!hasEntry && !hasNotesContent) {
      setError("Provide a question/answer pair or notes");
      return;
    }

    try {
      await onSubmit({
        entries: hasEntry ? [{ question: question.trim(), answer: answer.trim() }] : [],
        notes: hasNotesContent ? notes.trim() : undefined,
      });
      handleOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit clarification");
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent size="xl">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-blue-500" />
              {title}
            </DialogTitle>
            <DialogDescription>
              {description}
              {specName && (
                <span className="mt-1 block font-medium text-foreground">
                  Spec: {specName}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="clarify-question">Question</Label>
              <Input
                id="clarify-question"
                placeholder="What needs clarification?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="clarify-answer">Answer</Label>
              <Input
                id="clarify-answer"
                placeholder="Provide the resolved answer"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                disabled={isLoading}
              />
              <p className="text-muted-foreground text-xs">
                Both question and answer are required to add a Q&amp;A entry.
              </p>
            </div>

            {showNotes && (
              <div className="space-y-2">
                <Label htmlFor="clarify-notes">Additional Notes</Label>
                <Textarea
                  id="clarify-notes"
                  placeholder="Add any additional clarification notes or context..."
                  rows={4}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  disabled={isLoading}
                />
              </div>
            )}

            {error && (
              <div className="text-destructive text-sm" role="alert">
                {error}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Clarification"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function useClarificationDialog() {
  const [open, setOpen] = React.useState(false);

  const openDialog = React.useCallback(() => setOpen(true), []);
  const closeDialog = React.useCallback(() => setOpen(false), []);

  return {
    open,
    setOpen,
    openDialog,
    closeDialog,
    ClarificationDialogComponent: ClarificationDialog,
  };
}
