import { ContactAside, ContactForm } from '@/components/legal/static-pages';
import { PublicShell } from '@/components/legal/public-shell';

export default function ContactPage() { return <PublicShell><div className="container-shell py-16 sm:py-24"><div className="mx-auto max-w-3xl text-center"><p className="eyebrow">Contact</p><h1 className="mt-4 font-display text-4xl leading-[1.12] tracking-tight sm:text-5xl">We would like to hear from you.</h1><p className="mt-5 text-lg leading-8 text-muted">Questions, feedback, and thoughtful suggestions are welcome.</p></div><div className="mx-auto mt-14 grid max-w-5xl gap-6 lg:grid-cols-[1fr_330px]"><ContactForm /><ContactAside /></div></div></PublicShell>; }
