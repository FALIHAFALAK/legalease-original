'use client';

import { useParams } from 'next/navigation';
import { DocumentEditor } from '@/components/legal/document-editor';

export default function EditDocumentPage() { const params = useParams<{ id: string }>(); return <DocumentEditor documentId={Number(params.id)} />; }
