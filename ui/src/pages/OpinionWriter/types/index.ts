// File: ui/src/pages/OpinionWriter/types/index.ts
// Opinion Writer Types
export type OpinionStep = "configuration" | "drafting" | "compilation";

export type OpinionView = "initial" | "verification" | "rewritten";

// Chat types
export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  changeSuggestions?: ChangesuggestionSet;
};

export type ChangesuggestionSet = {
  changes: ChangesuggestionItem[];
  summary: string;
  confidence: number;
};

export type ChangesuggestionItem = {
  id: string;
  type: "replace" | "insert" | "delete" | "restructure";
  originalText: string;
  newText: string;
  startIndex: number;
  endIndex: number;
  reasoning: string;
  section?: string;
  priority: "high" | "medium" | "low";
};

export interface PendingChange extends ChangesuggestionItem {
  applied: boolean;
  previewMode: boolean;
}

// Opinion data types
export interface OpinionFormData {
  title: string;
  facts: string;
  questions: string;
  assumptions: string;
  clientName: string;
  clientAddress: string;
}

export interface OpinionVersionInfo {
  version: number;
  name: string;
  draft_id: string;
}

export interface OpinionDraft {
  draft: string;
  docs: any[];
}

// Component props interfaces
export interface StepIndicatorProps {
  step: string;
  label: string;
  isActive: boolean;
  isCompleted: boolean;
  canNavigate: boolean;
  onClick: () => void;
}

export interface ConfigurationStepProps {
  formData: OpinionFormData;
  onFormChange: (data: Partial<OpinionFormData>) => void;
  selectedOpinionId: string | null;
  hasUnsavedChanges: boolean;
  isLoading?: boolean;
  onSave: () => void;
  onCreate: () => void;
  onStartNew: () => void;
  onContinueToDrafting: () => void;
  onShowDocs: () => void;
  onGetPrecedents: () => void;
}

export interface DraftingStepProps {
  selectedOpinionId: string | null;
  title: string;
  currentOpinionDraft: OpinionDraft | null;
  currentOpinionVersionInfo: OpinionVersionInfo | null;
  modifiedOpinionText: string;
  hasUnsavedTextChanges: boolean;
  isLoadingDraft: boolean;
  loadedOpinion: any;
  onOpinionTextChange: (text: string) => void;
  onSaveChanges: () => void;
  onStartNew: () => void;
  onGenerateOpinion: () => void;
  onChangeVersion: (value: string) => void;
  onShowVersionSaver: () => void;
  onBackToConfiguration: () => void;
  onContinueToCompilation: () => void;
  copyToClipboard: () => void;
  copyingTextToClipboard: boolean;
  isGenerating?: boolean;
}

export interface AlchemioChatProps {
  opinionText: string;
  opinionVersionInfo: {
    version: number;
    name: string;
    draft_id: string;
  } | null;
  selectedOpinionId: string;
  onOpinionChange: (newText: string, appliedChange?: any) => void; // ← Add appliedChange parameter
}

export interface EnhancedOpinionDisplayProps {
  opinionText: string;
  originalText?: string; // NEW: Original text before AI changes
  showChangeMarkup?: boolean; // NEW: Whether to show markup
  onToggleMarkup?: () => void; // NEW: Toggle markup visibility
  onAcceptChanges?: () => void; // NEW: Accept all changes callback
  currentOpinionVersionInfo: {
    version: number;
    name: string;
    draft_id: string;
  } | null;
  copyToClipboard: () => void;
  copyingTextToClipboard: boolean;
  hasUnsavedChanges?: boolean;
  onSaveChanges?: () => void;
}

// Dialog props
export interface VersionSaverDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (versionName: string) => void;
  isLoading?: boolean;
}

export interface PrecedentCasesDialogProps {
  isOpen: boolean;
  onClose: () => void;
  precedentData: any;
}

export interface AdditionalDocsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  selectedOpinionId: string | null;
  loadedOpinion: any;
  globalDocs: any;
  onUploadSuccess: () => void;
  onRefreshDocs: () => void;
}
