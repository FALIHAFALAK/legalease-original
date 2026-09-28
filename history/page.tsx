import DocumentHistoryClient from '../history-client';

export function generateStaticParams() {
  return [{ id: 'demo' }];
}

export default function HistoryPage() {
  return <DocumentHistoryClient />;
}
