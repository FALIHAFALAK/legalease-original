'use client';

import { useEffect, useRef, useState } from 'react';
import { HelpCircle, Loader2, MessageSquare, Send, Wand2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/input';
import { askFindingQuestion, listFindingQuestions, reviewErrorMessage } from '@/lib/review-api';
import type { FindingDetail, ReviewMessage } from '@/lib/types';

type QuestionThreadProps = {
  finding: FindingDetail;
  questionCount: number;
};

function timeLabel(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function QuestionThread({ finding, questionCount }: QuestionThreadProps) {
  const [messages, setMessages] = useState<ReviewMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [wantRevision, setWantRevision] = useState(false);
  const [loading, setLoading] = useState(questionCount > 0);
  const [asking, setAsking] = useState(false);
  const [disclaimer, setDisclaimer] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    setLoading(questionCount > 0);
    if (questionCount === 0) {
      setMessages([]);
      return () => {
        active = false;
      };
    }
    listFindingQuestions(finding.id)
      .then((rows) => {
        if (active) setMessages(rows);
      })
      .catch(() => {
        if (active) setMessages([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [finding.id, questionCount]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [messages.length]);

  async function ask() {
    const trimmed = question.trim();
    if (trimmed.length < 2) {
      toast.error('Ask a question about this clause.');
      return;
    }
    setAsking(true);
    try {
      const response = await askFindingQuestion(finding.id, {
        question: trimmed,
        request_revision: wantRevision,
      });
      setMessages(response.messages);
      setDisclaimer(response.disclaimer);
      setQuestion('');
    } catch (error) {
      toast.error(reviewErrorMessage(error));
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="rounded-xl border border-border bg-[var(--background)] p-4">
      <p className="flex items-center gap-2 text-sm font-bold text-ink dark:text-white">
        <HelpCircle className="h-4 w-4 text-forest" />
        Ask about this clause
      </p>
      <p className="mt-1 text-xs leading-5 text-muted">
        Answers explain the flagged wording. They are general legal information, not advice on your
        situation.
      </p>

      {loading ? (
        <div className="mt-3 flex items-center gap-2 text-xs text-muted">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Loading earlier questions...
        </div>
      ) : null}

      {messages.length ? (
        <ul className="mt-3 space-y-2">
          {messages.map((message) => (
            <li
              key={message.id}
              className={
                message.role === 'user'
                  ? 'ml-6 rounded-xl rounded-br-sm bg-forest px-3 py-2 text-xs leading-5 text-white'
                  : 'mr-6 rounded-xl rounded-bl-sm border border-border bg-card px-3 py-2'
              }
            >
              <span className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide opacity-70">
                <MessageSquare className="h-3 w-3" />
                {message.role === 'user' ? 'You' : 'Assistant'}
                {message.kind === 'suggested_revision' ? ' · suggested wording' : ''}
                <span className="ml-auto font-normal normal-case">{timeLabel(message.created_at)}</span>
              </span>
              <p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-ink dark:text-white">
                {message.content}
              </p>
              {message.suggested_revision ? (
                <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-muted/10 p-2 text-[11px] leading-5 text-ink dark:text-white">
                  {message.suggested_revision}
                </pre>
              ) : null}
            </li>
          ))}
          <div ref={endRef} />
        </ul>
      ) : null}

      <form
        className="mt-3"
        onSubmit={(event) => {
          event.preventDefault();
          void ask();
        }}
      >
        <Textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
          placeholder="Is this payment period enforceable if the invoice is disputed?"
          aria-label="Your question about this clause"
        />
        <label className="mt-2 flex items-center gap-2 text-xs text-muted">
          <input
            type="checkbox"
            checked={wantRevision}
            onChange={(event) => setWantRevision(event.target.checked)}
            className="h-4 w-4 rounded border-border text-forest focus:ring-forest/30"
          />
          <Wand2 className="h-3.5 w-3.5" />
          Also draft wording I could send to the other side
        </label>
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-[11px] leading-4 text-muted">
            {disclaimer || finding.suggested_question || 'A qualified lawyer should confirm anything you rely on.'}
          </p>
          <Button type="submit" size="sm" disabled={asking || question.trim().length < 2}>
            {asking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            {asking ? 'Thinking' : 'Ask'}
          </Button>
        </div>
      </form>
    </div>
  );
}
