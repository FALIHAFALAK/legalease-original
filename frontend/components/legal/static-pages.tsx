'use client';

import { useState } from 'react';
import { Check, ChevronDown, Mail, Send, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input, Textarea } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export function PageHero({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <div className="mx-auto max-w-3xl text-center"><p className="eyebrow">{eyebrow}</p><h1 className="mt-4 font-display text-balance text-4xl leading-[1.12] tracking-tight sm:text-5xl">{title}</h1><p className="mt-5 text-lg leading-8 text-muted">{description}</p></div>;
}

export function LegalPage({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children: React.ReactNode }) {
  return <div className="container-shell py-16 sm:py-24"><PageHero eyebrow={eyebrow} title={title} description={description} /><div className="mx-auto mt-14 max-w-3xl"><Card><CardContent className="space-y-7 p-7 leading-8 text-muted sm:p-10 [&_h2]:mt-8 [&_h2]:text-xl [&_h2]:font-bold [&_h2]:text-ink [&_h3]:font-bold [&_h3]:text-ink [&_li]:ml-5 [&_li]:list-disc [&_strong]:text-ink dark:[&_h2]:text-white dark:[&_h3]:text-white dark:[&_strong]:text-white">{children}</CardContent></Card></div></div>;
}

const faqs = [
  ['Is LegalEase a law firm?', 'No. LegalEase is an AI-assisted drafting and information tool. It is not a law firm and does not provide legal advice or representation.'],
  ['Will my document be legally valid?', 'No tool can guarantee that a document is valid or enforceable. Laws, facts, and required formalities vary by jurisdiction. A qualified lawyer should review your final document.'],
  ['What happens to my content?', 'Your document content may be sent to Google Gemini when you use an AI feature and a provider is configured. Review the Privacy page for details and configure your deployment appropriately.'],
  ['Can I edit an AI-generated draft?', 'Yes. Every saved document is editable, versioned, and exportable. Treat the AI output as a starting point and review every section.'],
  ['Do I need a credit card?', 'No. You can create an account and explore the workspace without entering payment details.'],
];
export function FaqPageContent() {
  const [open, setOpen] = useState<number | null>(0);
  return <div className="mx-auto max-w-3xl"><div className="space-y-3">{faqs.map(([question, answer], index) => <Card key={question} className="overflow-hidden"><button onClick={() => setOpen(open === index ? null : index)} className="flex w-full items-center justify-between gap-4 p-5 text-left text-sm font-bold sm:p-6"><span>{question}</span><ChevronDown className={`h-4 w-4 shrink-0 text-muted transition ${open === index ? 'rotate-180 text-forest' : ''}`} /></button>{open === index ? <div className="border-t border-border px-5 pb-5 pt-4 text-sm leading-7 text-muted sm:px-6 sm:pb-6">{answer}</div> : null}</Card>)}</div></div>;
}

export function ContactForm() {
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSending(true);
    const form = new FormData(event.currentTarget);
    await new Promise((resolve) => window.setTimeout(resolve, 500));
    if (!form.get('email') || !form.get('message')) { toast.error('Add your email and a message first.'); setSending(false); return; }
    setSending(false); setSent(true); toast.success('Thanks — your message is ready for our team.');
  }
  if (sent) return <Card className="p-8 text-center"><div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10"><Check className="h-6 w-6" /></div><h2 className="mt-5 text-xl font-bold">Message received</h2><p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted">A member of the LegalEase team will follow up at the email you provided.</p><Button variant="secondary" className="mt-6" onClick={() => setSent(false)}>Send another message</Button></Card>;
  return <Card><CardHeader><CardTitle>Send us a note</CardTitle><p className="text-sm text-muted">We typically respond within two business days.</p></CardHeader><CardContent><form onSubmit={submit} className="space-y-5"><div className="grid gap-5 sm:grid-cols-2"><div className="space-y-2"><Label htmlFor="name">Name</Label><Input id="name" name="name" placeholder="Your name" /></div><div className="space-y-2"><Label htmlFor="email">Email</Label><Input id="email" name="email" type="email" placeholder="you@example.com" required /></div></div><div className="space-y-2"><Label htmlFor="topic">What can we help with?</Label><Input id="topic" name="topic" placeholder="Product question" /></div><div className="space-y-2"><Label htmlFor="message">Message</Label><Textarea id="message" name="message" placeholder="Tell us a little about what you need" required /></div><Button size="lg" className="w-full" disabled={sending}>{sending ? 'Sending…' : <><Send className="h-4 w-4" /> Send message</>}</Button><p className="flex items-start gap-2 text-xs leading-5 text-muted"><ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" /> Please do not include confidential or sensitive information in a support message.</p></form></CardContent></Card>;
}

export function ContactAside() {
  return <div className="space-y-5"><Card className="p-6"><Mail className="h-5 w-5 text-forest" /><h2 className="mt-4 text-lg font-bold">Email</h2><p className="mt-2 text-sm leading-6 text-muted">For product questions, feedback, or privacy requests.</p><a href="mailto:hello@legalease.local" className="mt-4 inline-block text-sm font-bold text-forest">hello@legalease.local</a></Card><Card className="p-6"><h2 className="text-lg font-bold">Before you write</h2><p className="mt-2 text-sm leading-6 text-muted">LegalEase cannot provide legal advice or review your individual legal situation through support. Please consult a qualified lawyer for advice about your circumstances.</p></Card></div>;
}
