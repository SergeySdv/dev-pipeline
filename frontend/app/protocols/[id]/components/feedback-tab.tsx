"use client"

import { useState } from "react"
import { useProtocolFeedback, useSubmitProtocolFeedback } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { LoadingState } from "@/components/ui/loading-state"
import { EmptyState } from "@/components/ui/empty-state"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { MessageSquare, Send, CheckCircle2, XCircle, HelpCircle, RotateCcw } from "lucide-react"
import { toast } from "sonner"
import { formatRelativeTime } from "@/lib/format"
import type { FeedbackCreate } from "@/lib/api/types"

interface FeedbackTabProps {
  protocolId: number
}

const feedbackTypeConfig = {
  approve: { label: "Approve", icon: CheckCircle2, color: "text-green-600" },
  reject: { label: "Reject", icon: XCircle, color: "text-red-600" },
  clarify: { label: "Clarify", icon: HelpCircle, color: "text-amber-600" },
  retry: { label: "Retry", icon: RotateCcw, color: "text-blue-600" },
} as const

export function FeedbackTab({ protocolId }: FeedbackTabProps) {
  const { data: feedback, isLoading } = useProtocolFeedback(protocolId)
  const submitFeedback = useSubmitProtocolFeedback()
  const [feedbackType, setFeedbackType] = useState<FeedbackCreate["feedback_type"]>("approve")
  const [message, setMessage] = useState("")

  const handleSubmit = async () => {
    if (!message.trim()) {
      toast.error("Please enter a message")
      return
    }
    try {
      await submitFeedback.mutateAsync({
        protocolId,
        data: { feedback_type: feedbackType, message: message.trim() },
      })
      toast.success("Feedback submitted")
      setMessage("")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to submit feedback")
    }
  }

  if (isLoading) return <LoadingState message="Loading feedback..." />

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Submit Feedback</CardTitle>
          <CardDescription>Provide approval, rejection, or clarification for this protocol run</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <Select value={feedbackType} onValueChange={(v) => setFeedbackType(v as FeedbackCreate["feedback_type"])}>
              <SelectTrigger className="w-[160px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(feedbackTypeConfig).map(([key, config]) => {
                  const Icon = config.icon
                  return (
                    <SelectItem key={key} value={key}>
                      <div className="flex items-center gap-2">
                        <Icon className={`h-4 w-4 ${config.color}`} />
                        {config.label}
                      </div>
                    </SelectItem>
                  )
                })}
              </SelectContent>
            </Select>
          </div>
          <Textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Enter your feedback message..."
            rows={3}
          />
          <Button onClick={handleSubmit} disabled={submitFeedback.isPending || !message.trim()}>
            <Send className="h-4 w-4 mr-2" />
            {submitFeedback.isPending ? "Submitting..." : "Submit Feedback"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Feedback History
          </CardTitle>
          <CardDescription>{feedback?.length || 0} feedback item(s)</CardDescription>
        </CardHeader>
        <CardContent>
          {!feedback || feedback.length === 0 ? (
            <EmptyState icon={MessageSquare} title="No feedback yet" description="Submit feedback to guide the protocol execution." />
          ) : (
            <div className="space-y-3">
              {feedback.map((item) => {
                const config = feedbackTypeConfig[item.feedback_type as keyof typeof feedbackTypeConfig] || feedbackTypeConfig.clarify
                const Icon = config.icon
                return (
                  <div key={item.id} className="flex items-start gap-3 rounded-lg border p-3">
                    <Icon className={`h-5 w-5 mt-0.5 shrink-0 ${config.color}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px]">{config.label}</Badge>
                        {item.created_by && (
                          <span className="text-xs text-muted-foreground">by {item.created_by}</span>
                        )}
                        <span className="text-xs text-muted-foreground">{formatRelativeTime(item.created_at)}</span>
                      </div>
                      <p className="mt-1 text-sm">{item.message}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
