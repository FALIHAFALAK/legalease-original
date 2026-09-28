import { PublicShell } from '@/components/legal/public-shell';
import { FaqPageContent, PageHero } from '@/components/legal/static-pages';

export default function FaqPage() { return <PublicShell><div className="container-shell py-16 sm:py-24"><PageHero eyebrow="Questions, answered" title="A little clarity goes a long way." description="Here are the things people ask most often about LegalEase and responsible AI-assisted legal work." /><div className="mt-14"><FaqPageContent /></div></div></PublicShell>; }
