import EditDocumentClient from '../edit-client';

export function generateStaticParams() {
  return [{ id: 'demo' }];
}

export default function EditPage() {
  return <EditDocumentClient />;
}
