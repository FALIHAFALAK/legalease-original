import PreviewDocumentClient from '../preview-client';

export function generateStaticParams() {
  return [{ id: 'demo' }];
}

export default function PreviewPage() {
  return <PreviewDocumentClient />;
}
