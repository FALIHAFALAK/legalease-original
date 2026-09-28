import TemplateDetailClient from './template-detail-client';

const slugs = [
  'mutual-nda',
  'partnership-agreement',
  'founders-agreement',
  'memorandum-of-understanding',
  'business-service-agreement',
  'independent-contractor-agreement',
  'employment-agreement',
  'offer-letter',
  'termination-letter',
  'confidentiality-agreement',
  'residential-rental-agreement',
  'lease-agreement',
  'rental-notice',
  'property-handover-checklist',
  'freelance-service-agreement',
  'consulting-agreement',
  'project-scope-agreement',
  'payment-agreement',
  'invoice-payment-terms',
  'authorization-letter',
  'affidavit-draft',
  'general-agreement',
  'loan-agreement',
  'consent-letter',
];

export function generateStaticParams() {
  return slugs.map((slug) => ({ slug }));
}

export default function Page() {
  return <TemplateDetailClient />;
}
