"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { useProtocolEvents } from "@/lib/api/hooks/use-events";
import { useProtocolClarifications } from "@/lib/api/hooks/use-protocols";
import { useAnswerClarificationById } from "@/lib/api/hooks/use-clarifications";
import { LoadingState } from "@/components/ui/loading-state";
import { AlertCircle, CheckCircle2, HelpCircle, RotateCcw, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Event, Clarification } from "@/lib/api/types";

// =============================================================================
// Types
// =============================================================================

export interface FeedbackEvent {
  id: string;
  event_type: string;
  message: string;
  created_at: string;
  metadata: {
    action_taken?: string;
    error_type?: string;
    clarification_id?: string;
  };
}

export interface FeedbackPanelProps {
  protocolRunId: string;
  onClarificationAnswered?: () => void;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Gets the icon component for a feedback event type
 */
function getFeedbackEventIcon(eventType: string) {
  switch (eventType) {
    case "clarification_requested":
      return HelpCircle;
    case "clarification_answered":
      return CheckCircle2;
    case "retry_triggered":
      return RotateCcw;
    case "escalation":
      return AlertCircle;
    case "feedback_submitted":
      return MessageSquare;
    default:
      return AlertCircle;
  }
}

/**
 * Gets the color class for a feedback event type
 */
function getFeedbackEventColor(eventType: string): string {
  switch (eventType) {
    case "clarification_requested":
      return "text-yellow-500";
    case "clarification_answered":
      return "text-green-500";
    case "retry_triggered":
      return "text-blue-500";
    case "escalation":
      return "text-red-500";
    case "feedback_submitted":
      return "text-purple-500";
    default:
      return "text-muted-foreground";
  }
}

/**
 * Gets the badge variant for an event type
 */
function getFeedbackEventBadgeVariant(eventType: string): "default" | "secondary" | "destructive" | "outline" {
  switch (eventType) {
    case "clarification_requested":
      return "secondary";
    case "clarification_answered":
      return "default";
    case "retry_triggered":
      return "outline";
    case "escalation":
      return "destructive";
    default:
      return "outline";
  }
}

/**
 * Formats an event type for display
 */
function formatEventType(eventType: string): string {
  return eventType
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Filter events to only include feedback-related ones
 */
function filterFeedbackEvents(events: Event[] | undefined): FeedbackEvent[] {
  if (!events) return [];
  
  const feedbackTypes = [
    "clarification_requested",
    "clarification_answered",
    "retry_triggered",
    "escalation",
    "feedback_submitted",
    "error_recovered",
    "blocked",
  ];
  
  return events
    .filter((e) => feedbackTypes.includes(e.event_type) || e.event_category === "feedback")
    .map((e) => ({
      id: String(e.id),
      event_type: e.event_type,
      message: e.message,
      created_at: e.created_at,
      metadata: {
        action_taken: e.metadata?.action_taken as string | undefined,
        error_type: e.metadata?.error_type as string | undefined,
        clarification_id: e.metadata?.clarification_id as string | undefined,
      },
    }));
}

// =============================================================================
// Component
// =============================================================================

export function FeedbackPanel({ protocolRunId, onClarificationAnswered }: FeedbackPanelProps) {
  const [answeringId, setAnsweringId] = useState<number | null>(null);
  const [answerText, setAnswerText] = useState("");
  
  const { data: events, isLoading: eventsLoading } = useProtocolEvents(
    Number(protocolRunId)
  );
  
  const { data: clarifications } = useProtocolClarifications(
    Number(protocolRunId),
    "open"
  );
  
  const answerMutation = useAnswerClarificationById();
  
  const feedbackEvents = filterFeedbackEvents(events);
  
  const handleAnswer = async (clarificationId: number) => {
    if (!answerText.trim()) return;
    
    try {
      await answerMutation.mutateAsync({
        id: clarificationId,
        answer: answerText,
      });
      setAnswerText("");
      setAnsweringId(null);
      onClarificationAnswered?.();
    } catch (error) {
      console.error("Failed to answer clarification:", error);
    }
  };

  if (eventsLoading) {
    return <LoadingState message="Loading feedback..." />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          Feedback Loop
          {clarifications && clarifications.length > 0 && (
            <Badge variant="secondary" className="ml-2">
              {clarifications.length} pending
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Open Clarifications */}
        {clarifications && clarifications.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">
              Pending Clarifications
            </h4>
            {clarifications.map((clarification: Clarification) => (
              <Card key={clarification.id} className="border-yellow-200 bg-yellow-50/50">
                <CardContent className="pt-4">
                  <div className="space-y-2">
                    <p className="text-sm font-medium">{clarification.question}</p>
                    {clarification.options && (
                      <div className="flex flex-wrap gap-2">
                        {clarification.options.map((option: string, idx: number) => (
                          <Button
                            key={idx}
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setAnsweringId(clarification.id);
                              setAnswerText(option);
                            }}
                          >
                            {option}
                          </Button>
                        ))}
                      </div>
                    )}
                    {answeringId === clarification.id ? (
                      <div className="space-y-2">
                        <Textarea
                          value={answerText}
                          onChange={(e) => setAnswerText(e.target.value)}
                          placeholder="Type your answer..."
                          rows={2}
                        />
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleAnswer(clarification.id)}
                            disabled={!answerText.trim() || answerMutation.isPending}
                          >
                            Submit
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setAnsweringId(null);
                              setAnswerText("");
                            }}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setAnsweringId(clarification.id)}
                      >
                        Answer
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Feedback Events Timeline */}
        {feedbackEvents.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">
              Recent Events
            </h4>
            <div className="space-y-2">
              {feedbackEvents.slice(0, 10).map((event) => {
                const Icon = getFeedbackEventIcon(event.event_type);
                return (
                  <div
                    key={event.id}
                    className="flex items-start gap-3 p-2 rounded-lg bg-muted/50"
                  >
                    <Icon className={cn("h-4 w-4 mt-0.5", getFeedbackEventColor(event.event_type))} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant={getFeedbackEventBadgeVariant(event.event_type)} className="text-xs">
                          {formatEventType(event.event_type)}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {new Date(event.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm mt-1">{event.message}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {feedbackEvents.length === 0 && (!clarifications || clarifications.length === 0) && (
          <div className="text-center text-sm text-muted-foreground py-4">
            No feedback events yet
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Compact Variant
// =============================================================================

export function CompactFeedbackPanel({ protocolRunId }: { protocolRunId: string }) {
  const { data: events } = useProtocolEvents(Number(protocolRunId));
  const { data: clarifications } = useProtocolClarifications(Number(protocolRunId), "open");
  
  const feedbackEvents = filterFeedbackEvents(events);
  const openClarifications = clarifications?.length || 0;
  const recentEvents = feedbackEvents.slice(0, 3);
  
  return (
    <Card>
      <CardHeader className="py-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Feedback
          {openClarifications > 0 && (
            <Badge variant="destructive" className="text-xs">
              {openClarifications}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="py-2">
        {recentEvents.length > 0 ? (
          <div className="space-y-2">
            {recentEvents.map((event) => {
              const Icon = getFeedbackEventIcon(event.event_type);
              return (
                <div key={event.id} className="flex items-center gap-2 text-xs">
                  <Icon className={cn("h-3 w-3", getFeedbackEventColor(event.event_type))} />
                  <span className="truncate">{event.message}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">No recent events</p>
        )}
      </CardContent>
    </Card>
  );
}
