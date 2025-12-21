/**
 * Types for the Findings Explorer
 */

export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'positive' | 'gap';

export interface FinancialExposureDetail {
  amount: number | null;
  currency: string;
  calculation: string | null;  // "Show your working" - e.g., "500,000 tonnes × R927/tonne × 24 months = R927M"
}

export interface Finding {
  id: string;
  title: string;
  severity: FindingSeverity;
  category: string;
  document_id: string;
  document_name: string;
  page_reference?: string;
  source_text?: string;
  analysis: string;
  chain_of_thought?: string;
  recommendation?: string;
  exposure_amount?: number;
  confidence_score?: number;
  created_at?: string;
  // Financial exposure with calculation details
  financial_exposure?: FinancialExposureDetail;
  deal_impact?: string;  // "deal_blocker" | "condition_precedent" | "price_chip" | etc.
  // Phase 3: Folder-aware processing fields
  folder_category?: string;  // e.g., "01_Corporate", "02_Commercial"
  question_id?: string;      // Links to blueprint question that generated this finding
  is_cross_document?: boolean;  // True for cross-document findings
  related_document_ids?: string[];  // Document IDs for cross-doc findings
  source_cluster?: string;   // Pass 3 cluster: "corporate_governance", "financial", etc.
  // Gap finding fields
  gap_reason?: 'documents_not_provided' | 'information_not_found' | 'inconclusive';
  gap_detail?: string;       // Detailed explanation of the gap
  documents_analyzed_count?: number;  // How many docs were analyzed for this category
}

export interface DocumentWithFindings {
  id: string;
  name: string;
  file_type: string;
  findings_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  positive_count: number;
  gap_count: number;
}

export interface RunInfo {
  id: string;
  run_number: number;
  status: string;
  created_at: string;
  completed_at?: string;
  total_findings: number;
  critical_findings: number;
  documents_processed: number;
  total_tokens?: number;
  total_cost?: number;
}

export interface FindingsExplorerProps {
  ddId: string;
  runs: RunInfo[];
  selectedRunId: string | null;
  onRunSelect: (runId: string) => void;
}

export interface RunSelectorProps {
  runs: RunInfo[];
  selectedRunId: string | null;
  onSelect: (runId: string) => void;
}

export interface DocumentNavigatorProps {
  documents: DocumentWithFindings[];
  selectedDocId: string | null;
  onDocumentSelect: (docId: string | null) => void;
  onViewDocument?: (docId: string) => void;
  onDownloadDocument?: (docId: string) => void;
}

export interface FindingsListProps {
  findings: Finding[];
  selectedFindingId: string | null;
  onFindingSelect: (findingId: string) => void;
  filterDocId: string | null;
}

export interface FindingDetailProps {
  finding: Finding | null;
  onAskQuestion?: (question: string) => void;
}

// Severity configuration for consistent styling
export const SEVERITY_CONFIG: Record<FindingSeverity, {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: string;
}> = {
  critical: {
    label: 'Critical',
    color: 'text-red-700 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-red-200 dark:border-red-800',
    icon: '●'
  },
  high: {
    label: 'High',
    color: 'text-orange-700 dark:text-orange-400',
    bgColor: 'bg-orange-50 dark:bg-orange-900/20',
    borderColor: 'border-orange-200 dark:border-orange-800',
    icon: '●'
  },
  medium: {
    label: 'Medium',
    color: 'text-yellow-700 dark:text-yellow-400',
    bgColor: 'bg-yellow-50 dark:bg-yellow-900/20',
    borderColor: 'border-yellow-200 dark:border-yellow-800',
    icon: '●'
  },
  low: {
    label: 'Low',
    color: 'text-blue-700 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-blue-200 dark:border-blue-800',
    icon: '●'
  },
  positive: {
    label: 'Positive',
    color: 'text-green-700 dark:text-green-400',
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    borderColor: 'border-green-200 dark:border-green-800',
    icon: '✓'
  },
  gap: {
    label: 'Gap',
    color: 'text-gray-700 dark:text-gray-400',
    bgColor: 'bg-gray-50 dark:bg-gray-800/50',
    borderColor: 'border-gray-200 dark:border-gray-700',
    icon: '○'
  }
};

// Severity sort order (most important first)
export const SEVERITY_ORDER: FindingSeverity[] = ['critical', 'high', 'medium', 'low', 'positive', 'gap'];

// ============================================
// DD Category Types (for filtering findings)
// ============================================

// Standard DD categories for filtering findings
export type DDCategory =
  | 'Governance'
  | 'Commercial'
  | 'Financial'
  | 'Regulatory'
  | 'Employment'
  | 'Insurance'
  | 'Litigation'
  | 'Tax'
  | 'Other';

export interface DDCategoryConfig {
  label: string;
  color: string;
  bgColor: string;
  keywords: string[];  // Keywords to match against finding category
}

export const DD_CATEGORY_CONFIG: Record<DDCategory, DDCategoryConfig> = {
  'Governance': {
    label: 'Governance',
    color: 'text-blue-700 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    keywords: ['governance', 'corporate', 'constitutional', 'shareholding', 'board', 'resolution', 'company']
  },
  'Commercial': {
    label: 'Commercial',
    color: 'text-purple-700 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    keywords: ['commercial', 'contract', 'agreement', 'supply', 'offtake', 'service', 'jv', 'joint venture']
  },
  'Financial': {
    label: 'Financial',
    color: 'text-emerald-700 dark:text-emerald-400',
    bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
    keywords: ['financial', 'finance', 'banking', 'loan', 'security', 'guarantee', 'debt', 'credit']
  },
  'Regulatory': {
    label: 'Regulatory',
    color: 'text-red-700 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    keywords: ['regulatory', 'regulation', 'license', 'permit', 'environmental', 'compliance', 'mining right', 'water use']
  },
  'Employment': {
    label: 'Employment',
    color: 'text-orange-700 dark:text-orange-400',
    bgColor: 'bg-orange-50 dark:bg-orange-900/20',
    keywords: ['employment', 'labour', 'labor', 'employee', 'hr', 'human resource', 'union', 'pension', 'benefit']
  },
  'Insurance': {
    label: 'Insurance',
    color: 'text-cyan-700 dark:text-cyan-400',
    bgColor: 'bg-cyan-50 dark:bg-cyan-900/20',
    keywords: ['insurance', 'policy', 'coverage', 'claim', 'indemnity']
  },
  'Litigation': {
    label: 'Litigation',
    color: 'text-rose-700 dark:text-rose-400',
    bgColor: 'bg-rose-50 dark:bg-rose-900/20',
    keywords: ['litigation', 'dispute', 'lawsuit', 'legal', 'court', 'arbitration', 'claim']
  },
  'Tax': {
    label: 'Tax',
    color: 'text-slate-700 dark:text-slate-400',
    bgColor: 'bg-slate-50 dark:bg-slate-900/20',
    keywords: ['tax', 'vat', 'income tax', 'withholding', 'transfer pricing', 'sars']
  },
  'Other': {
    label: 'Other',
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-50 dark:bg-gray-800/50',
    keywords: []  // Catch-all
  }
};

// DD categories in display order
export const DD_CATEGORY_ORDER: DDCategory[] = [
  'Governance',
  'Commercial',
  'Financial',
  'Regulatory',
  'Employment',
  'Insurance',
  'Litigation',
  'Tax',
  'Other'
];

// Helper to determine which DD category a finding belongs to based on its category string
export function getDDCategoryForFinding(findingCategory: string | undefined): DDCategory {
  if (!findingCategory) return 'Other';

  const lowerCategory = findingCategory.toLowerCase();

  for (const ddCategory of DD_CATEGORY_ORDER) {
    if (ddCategory === 'Other') continue;
    const config = DD_CATEGORY_CONFIG[ddCategory];
    if (config.keywords.some(keyword => lowerCategory.includes(keyword))) {
      return ddCategory;
    }
  }

  return 'Other';
}

// ============================================
// Legacy Folder Category Types (kept for compatibility)
// ============================================

export type FolderCategory =
  | '01_Corporate'
  | '02_Commercial'
  | '03_Financial'
  | '04_Regulatory'
  | '05_Employment'
  | '06_Property'
  | '07_Insurance'
  | '08_Litigation'
  | '09_Tax'
  | '99_Needs_Review';

export const FOLDER_CATEGORY_CONFIG: Record<FolderCategory, { shortLabel: string; color: string; bgColor: string; borderColor: string; icon: string }> = {
  '01_Corporate': { shortLabel: 'Corporate', color: 'text-blue-700 dark:text-blue-400', bgColor: 'bg-blue-50 dark:bg-blue-900/20', borderColor: 'border-blue-200 dark:border-blue-800', icon: '🏛️' },
  '02_Commercial': { shortLabel: 'Commercial', color: 'text-purple-700 dark:text-purple-400', bgColor: 'bg-purple-50 dark:bg-purple-900/20', borderColor: 'border-purple-200 dark:border-purple-800', icon: '📋' },
  '03_Financial': { shortLabel: 'Financial', color: 'text-emerald-700 dark:text-emerald-400', bgColor: 'bg-emerald-50 dark:bg-emerald-900/20', borderColor: 'border-emerald-200 dark:border-emerald-800', icon: '💰' },
  '04_Regulatory': { shortLabel: 'Regulatory', color: 'text-red-700 dark:text-red-400', bgColor: 'bg-red-50 dark:bg-red-900/20', borderColor: 'border-red-200 dark:border-red-800', icon: '⚖️' },
  '05_Employment': { shortLabel: 'Employment', color: 'text-orange-700 dark:text-orange-400', bgColor: 'bg-orange-50 dark:bg-orange-900/20', borderColor: 'border-orange-200 dark:border-orange-800', icon: '👥' },
  '06_Property': { shortLabel: 'Property', color: 'text-amber-700 dark:text-amber-400', bgColor: 'bg-amber-50 dark:bg-amber-900/20', borderColor: 'border-amber-200 dark:border-amber-800', icon: '🏠' },
  '07_Insurance': { shortLabel: 'Insurance', color: 'text-cyan-700 dark:text-cyan-400', bgColor: 'bg-cyan-50 dark:bg-cyan-900/20', borderColor: 'border-cyan-200 dark:border-cyan-800', icon: '🛡️' },
  '08_Litigation': { shortLabel: 'Litigation', color: 'text-rose-700 dark:text-rose-400', bgColor: 'bg-rose-50 dark:bg-rose-900/20', borderColor: 'border-rose-200 dark:border-rose-800', icon: '⚠️' },
  '09_Tax': { shortLabel: 'Tax', color: 'text-slate-700 dark:text-slate-400', bgColor: 'bg-slate-50 dark:bg-slate-900/20', borderColor: 'border-slate-200 dark:border-slate-800', icon: '📊' },
  '99_Needs_Review': { shortLabel: 'Review', color: 'text-gray-500 dark:text-gray-500', bgColor: 'bg-gray-50 dark:bg-gray-800/50', borderColor: 'border-gray-200 dark:border-gray-700', icon: '❓' }
};

export const FOLDER_CATEGORY_ORDER: FolderCategory[] = [
  '01_Corporate', '02_Commercial', '03_Financial', '04_Regulatory', '05_Employment',
  '06_Property', '07_Insurance', '08_Litigation', '09_Tax', '99_Needs_Review'
];

export function getFolderCategoryShortLabel(category: string): string {
  const config = FOLDER_CATEGORY_CONFIG[category as FolderCategory];
  return config?.shortLabel || category.replace(/_/g, ' ').replace(/^\d+/, '').trim();
}

// ============================================
// Human Review Types
// ============================================

export type ReviewStatus = 'pending' | 'confirmed' | 'dismissed' | 'reclassified';

export interface HumanReview {
  status: ReviewStatus;
  reclassified_severity?: FindingSeverity;
  reviewer_notes?: string;
  negotiation_implications?: string;
  client_specific_notes?: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

export interface FindingWithReview extends Finding {
  human_review?: HumanReview;
}

// ============================================
// Completeness Check Types
// ============================================

export type ImportanceLevel = 'critical' | 'high' | 'medium' | 'low';
export type MissingItemStatus = 'outstanding' | 'requested' | 'not_applicable' | 'received';

export interface MissingDocument {
  id: string;
  document_type: string;
  description: string;
  importance: ImportanceLevel;
  ai_rationale: string;
  status: MissingItemStatus;
  requested_at?: string;
  note?: string;
  blueprint_reference?: string;
}

export interface UnansweredQuestion {
  id: string;
  question: string;
  category: string;
  importance: ImportanceLevel;
  ai_rationale: string;
  status: MissingItemStatus;
  related_documents?: string[];
  note?: string;
}

export interface CompletenessCheckData {
  missing_documents: MissingDocument[];
  unanswered_questions: UnansweredQuestion[];
  completeness_score: number; // 0-100
  documents_received: number;
  documents_expected: number;
  questions_answered: number;
  questions_total: number;
  last_checked_at?: string;
}

// ============================================
// AI Chat Types
// ============================================

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  finding_id?: string;
  document_id?: string;
}

export interface AIChatProps {
  ddId: string;
  runId: string | null;
  selectedFinding?: Finding | null;
  onSendMessage: (message: string, context?: { findingId?: string; documentId?: string }) => Promise<string>;
  messages: ChatMessage[];
  isLoading?: boolean;
}

// ============================================
// Report Types
// ============================================

export type ReportType = 'preliminary' | 'final';

export interface ReportExportOptions {
  type: ReportType;
  includeHumanNotes: boolean;
  includeChainOfThought: boolean;
  includeMissingItems: boolean;
  format: 'pdf' | 'docx' | 'json';
}

// ============================================
// Importance Configuration
// ============================================

export const IMPORTANCE_CONFIG: Record<ImportanceLevel, {
  label: string;
  color: string;
  bgColor: string;
  description: string;
}> = {
  critical: {
    label: 'Critical',
    color: 'text-red-700 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    description: 'Essential for deal completion'
  },
  high: {
    label: 'High',
    color: 'text-orange-700 dark:text-orange-400',
    bgColor: 'bg-orange-50 dark:bg-orange-900/20',
    description: 'Strongly recommended'
  },
  medium: {
    label: 'Medium',
    color: 'text-yellow-700 dark:text-yellow-400',
    bgColor: 'bg-yellow-50 dark:bg-yellow-900/20',
    description: 'Recommended for thoroughness'
  },
  low: {
    label: 'Low',
    color: 'text-blue-700 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    description: 'Nice to have'
  }
};

export const IMPORTANCE_ORDER: ImportanceLevel[] = ['critical', 'high', 'medium', 'low'];
