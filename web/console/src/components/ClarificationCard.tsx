import React from 'react';
import { Button } from '@/components/ui/Button';
import { FormField } from '@/components/ui/Form';
import { cn } from '@/lib/cn';

interface Clarification {
  id: string;
  key: string;
  question: string;
  recommended?: string;
  options?: string[];
  applies_to: string;
  blocking: boolean;
  answer?: string;
  status: 'open' | 'answered';
  answered_at?: string;
  answered_by?: string;
}

interface ClarificationCardProps {
  clarification: Clarification;
  onAnswer?: (key: string, answer: string) => void;
  className?: string;
}

export function ClarificationCard({ clarification, onAnswer, className }: ClarificationCardProps) {
  const [answer, setAnswer] = React.useState(clarification.answer || '');
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!answer.trim() || !onAnswer) return;
    
    setIsSubmitting(true);
    try {
      await onAnswer(clarification.key, answer);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isAnswered = clarification.status === 'answered';
  const isBlocking = clarification.blocking && !isAnswered;

  return (
    <div className={cn(
      'border rounded-lg p-4 space-y-3',
      isBlocking ? 'border-red-200 bg-red-50' : 'border-gray-200 bg-white',
      className
    )}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          {isBlocking && (
            <span className="text-red-600 font-medium text-sm">🔒 BLOCKING</span>
          )}
          {!isBlocking && (
            <span className="text-gray-500 text-sm">ℹ️ INFO</span>
          )}
          <span className="font-medium text-gray-900">{clarification.key}</span>
        </div>
        
        {isAnswered && (
          <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
            ✓ ANSWERED
          </span>
        )}
      </div>

      <div className="text-gray-900">{clarification.question}</div>

      {clarification.options && clarification.options.length > 0 && (
        <div className="text-sm text-gray-600">
          <span className="font-medium">Options:</span>
          <ul className="list-disc list-inside mt-1 space-y-1">
            {clarification.options.map((option, index) => (
              <li key={index} className="cursor-pointer hover:text-blue-600" onClick={() => setAnswer(option)}>
                {option}
              </li>
            ))}
          </ul>
        </div>
      )}

      {clarification.recommended && (
        <div className="text-sm text-blue-600">
          <span className="font-medium">Recommended:</span> {clarification.recommended}
        </div>
      )}

      <div className="text-xs text-gray-500">
        Applies to: {clarification.applies_to}
      </div>

      {isAnswered ? (
        <div className="border-t pt-3">
          <div className="text-sm">
            <span className="font-medium">Answer:</span> {clarification.answer}
          </div>
          {clarification.answered_by && (
            <div className="text-xs text-gray-500 mt-1">
              Answered by: {clarification.answered_by}
              {clarification.answered_at && (
                <span> at {new Date(clarification.answered_at).toLocaleString()}</span>
              )}
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="border-t pt-3">
          <FormField label="Your Answer">
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Type your answer here..."
              className="w-full h-20 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
              required
            />
          </FormField>
          <div className="flex justify-end mt-2">
            <Button
              type="submit"
              size="small"
              disabled={!answer.trim() || isSubmitting}
              loading={isSubmitting}
            >
              Submit Answer
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}