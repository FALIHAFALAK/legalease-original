export type Role = 'user' | 'admin';

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  created_at: string;
  last_login_at: string | null;
};

export type TemplateField = {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'date' | 'select' | 'number' | 'email';
  required: boolean;
  placeholder: string;
  help: string;
  options: string[];
};

export type TemplateSummary = {
  id: number;
  slug: string;
  name: string;
  category: string;
  description: string;
  estimated_time: string;
  is_active: boolean;
};

export type TemplateDetail = TemplateSummary & {
  fields: TemplateField[];
  sections: string[];
  disclaimer: string;
};

export type DocumentSummary = {
  id: number;
  title: string;
  status: string;
  jurisdiction: string | null;
  template_slug: string | null;
  updated_at: string;
  created_at: string;
  current_version: number;
};

export type DocumentDetail = DocumentSummary & {
  content_html: string;
  content_text: string;
  form_data: Record<string, string>;
  missing_information: string[];
  assumptions: string[];
  review_notes: string[];
};

export type DocumentListResponse = {
  items: DocumentSummary[];
  total: number;
  draft_count: number;
  completed_count: number;
};

export type Version = {
  id: number;
  version_number: number;
  title: string;
  content_html: string;
  change_note: string;
  created_at: string;
};

export type GeneratedDocument = {
  document: {
    title: string;
    content: string;
    sections: string[];
    jurisdiction: string | null;
    missing_information: string[];
    assumptions: string[];
    review_notes: string[];
  };
  document_id: number | null;
  provider: string;
  model: string;
  is_draft: boolean;
};

export type ReviewFinding = {
  category: string;
  severity: 'low' | 'medium' | 'high';
  excerpt: string;
  explanation: string;
  suggested_question: string;
};

export type ReviewSeverity = 'low' | 'medium' | 'high';

export type FindingStatus = 'open' | 'resolved' | 'dismissed' | 'needs_professional_review';

export type FindingLifecycle = 'new' | 'fixed' | 'unresolved' | 'carried_over';

export type FindingCategory =
  | 'unclear_clause'
  | 'missing_information'
  | 'inconsistent_detail'
  | 'ambiguous_wording'
  | 'unusual_obligation'
  | 'professional_review';

export type PageReferenceKind = 'source_page' | 'estimated_page';

export type ClauseReference = {
  index: number;
  heading: string;
  citation: string;
  page_start: number;
  page_end: number;
  page_reference_kind: PageReferenceKind;
  summary: string;
  text: string;
  finding_ids: number[];
  open_finding_count: number;
};

export type FindingSummary = {
  id: number;
  review_id: number;
  document_id: number | null;
  document_version_id: number | null;
  first_review_id: number | null;
  previous_finding_id: number | null;
  clause_index: number;
  clause_heading: string;
  clause_citation: string;
  page_start: number;
  page_end: number;
  page_reference_kind: PageReferenceKind;
  category: FindingCategory;
  severity: ReviewSeverity;
  title: string;
  excerpt: string;
  explanation: string;
  severity_explanation: string;
  suggested_wording: string;
  suggested_question: string;
  status: FindingStatus;
  status_note: string;
  status_evidence: string;
  status_changed_at: string | null;
  lifecycle: FindingLifecycle;
  resolution_evidence: string;
  round_number: number;
  confidence: number | null;
  question_count: number;
  created_at: string | null;
  updated_at: string | null;
};

/** Adds the clause the finding was raised from, plus its in-clause quote span. */
export type FindingDetail = FindingSummary & {
  clause_text: string;
  quote_start_offset: number;
  quote_end_offset: number;
};

export type ReviewCounts = {
  total: number;
  open: number;
  resolved: number;
  dismissed: number;
  needs_professional_review: number;
  high: number;
  medium: number;
  low: number;
};

export type ReviewListItem = {
  id: number;
  filename: string;
  file_type: string;
  document_title: string;
  document_id: number | null;
  document_version_id: number | null;
  parent_review_id: number | null;
  version_number: number;
  round_number: number;
  page_count: number;
  word_count: number;
  clause_count: number;
  page_reference_kind: PageReferenceKind;
  status: string;
  provider: string;
  model: string;
  fixed_count: number;
  unresolved_count: number;
  new_count: number;
  summary: string;
  created_at: string;
};

export type ReviewListResponse = {
  items: ReviewListItem[];
  total: number;
  counts: ReviewCounts;
};

export type ReviewResponse = ReviewListItem & {
  review_id: number;
  extracted_text: string;
  findings: ReviewFinding[];
  detailed_findings: FindingDetail[];
  clauses: ClauseReference[];
  counts: ReviewCounts;
  professional_review_notice: string;
  disclaimer: string;
};

export type ReviewDetailResponse = ReviewResponse & {
  comparison: ComparisonResponse | null;
};

export type ComparisonItem = {
  /** Null when an earlier concern is no longer raised, so no current row points at it. */
  finding_id: number | null;
  previous_finding_id: number | null;
  outcome: FindingLifecycle;
  category: FindingCategory;
  severity: ReviewSeverity;
  title: string;
  clause_citation: string;
  excerpt: string;
  status: FindingStatus;
  evidence: string;
  summary: string;
};

export type ComparisonResponse = {
  review_id: number;
  previous_review_id: number | null;
  previous_filename: string;
  items: ComparisonItem[];
  fixed: ComparisonItem[];
  unresolved: ComparisonItem[];
  newly_introduced: ComparisonItem[];
  fixed_count: number;
  unresolved_count: number;
  new_count: number;
  disclaimer: string;
};

export type ReviewMessage = {
  id: number;
  finding_id: number;
  role: 'user' | 'assistant';
  kind: 'question' | 'explanation' | 'suggested_revision';
  content: string;
  suggested_revision: string;
  created_at: string;
};

export type FindingQuestionResponse = {
  finding_id: number;
  question_id: number | null;
  answer_id: number | null;
  question: string;
  answer: string;
  suggested_revision: string;
  suggested_wording: string;
  disclaimer: string;
  provider: string;
  model: string;
  messages: ReviewMessage[];
  created_at: string | null;
};

export type ReanalyzeResponse = {
  review: ReviewResponse;
  comparison: ComparisonResponse | null;
};

export type Conversation = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
};

export type Message = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
};

export type AssistantResponse = {
  conversation_id: number;
  message: string;
  disclaimer: string;
  provider: string;
  model: string;
  created_at: string;
};

export type ConversationDetail = Conversation & { messages: Message[] };
