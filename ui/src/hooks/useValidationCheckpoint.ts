import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";
import { reactQueryDefaults } from "./reactQuerySetup";

// ============================================
// Types for Validation Checkpoint
// ============================================

export type CheckpointType = 'missing_docs' | 'post_analysis' | 'entity_confirmation';
export type CheckpointStatus = 'pending' | 'awaiting_user_input' | 'completed' | 'skipped';

export interface UnderstandingQuestion {
  question_id: string;
  question: string;
  context?: string;
  ai_assessment?: string;
  confidence?: number;
  options?: Array<{
    value: string;
    label: string;
    description?: string;
  }>;
  requires_correction_text?: boolean;
}

export interface FinancialConfirmation {
  metric: string;
  extracted_value: number | null;
  currency?: string;
  source_document?: string;
  confirmed_value?: number | null;
  confidence?: number;
}

export interface MissingDocument {
  doc_type: string;
  description: string;
  importance: 'critical' | 'high' | 'medium';
  reason: string;
  expected_folder?: string;
}

export interface EntityQuestion {
  entity_name: string;
  registration_number?: string;
  appears_in_documents: number;
  ai_assessment?: string;
  confidence?: number;
  suggested_relationship?: string;
}

export interface CheckpointData {
  id: string;
  checkpoint_type: CheckpointType;
  status: CheckpointStatus;
  preliminary_summary?: string;
  questions?: UnderstandingQuestion[] | EntityQuestion[];
  missing_docs?: MissingDocument[];
  financial_confirmations?: FinancialConfirmation[];
  user_responses?: Record<string, unknown>;
  created_at?: string;
}

export interface CheckpointResponse {
  has_checkpoint: boolean;
  dd_id: string;
  checkpoint?: CheckpointData;
}

export interface SubmitResponse {
  checkpoint_id: string;
  status: CheckpointStatus;
  is_complete: boolean;
  message: string;
}

// ============================================
// User Response Types
// ============================================

export interface QuestionResponse {
  selected_option: string;
  correction_text?: string;
}

export interface FinancialResponse {
  metric: string;
  extracted_value: number | null;
  confirmed_value: number | null;
  status: 'correct' | 'incorrect' | 'not_available' | 'uncertain_check';
  correction_text?: string;  // Used with uncertain_check to specify what to verify
}

export interface MissingDocResponse {
  doc_type: string;
  action: 'uploaded' | 'dont_have' | 'not_applicable';
  uploaded_doc_id?: string;
  note?: string;
}

export interface EntityResponse {
  entity_name: string;
  relationship: 'related_party' | 'subsidiary' | 'parent' | 'counterparty' | 'exclude' | 'other';
  other_description?: string;
}

export interface CheckpointResponses {
  // Step 1: Understanding questions
  question_responses?: Record<string, QuestionResponse>;

  // Step 2: Financial confirmations
  financial_confirmations?: FinancialResponse[];
  manual_inputs?: Record<string, number | string>;

  // Step 3: Missing docs
  missing_doc_responses?: Record<string, MissingDocResponse>;
  uploaded_doc_ids?: string[];

  // Step 4: Final confirmation
  step_4_confirmed?: boolean;

  // Entity confirmation
  entity_responses?: Record<string, EntityResponse>;
}

// ============================================
// Hooks
// ============================================

/**
 * Hook to get pending checkpoint for a DD project
 */
export function useValidationCheckpoint(ddId: string | undefined, enabled = true) {
  const axios = useAxiosWithAuth();

  return useQuery<CheckpointResponse>({
    queryKey: ["validation-checkpoint", ddId],
    queryFn: async () => {
      const { data } = await axios({
        url: `/dd-validation-checkpoint?dd_id=${ddId}`,
        method: "GET",
      });
      return data;
    },
    enabled: !!ddId && enabled,
    refetchInterval: 30000, // Check every 30 seconds for new checkpoints
    ...reactQueryDefaults,
  });
}

/**
 * Hook to submit checkpoint responses
 */
export function useSubmitCheckpointResponse() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation<SubmitResponse, Error, { checkpointId: string; responses: CheckpointResponses }>({
    mutationFn: async ({ checkpointId, responses }) => {
      const { data } = await axios({
        url: "/dd-validation-checkpoint",
        method: "POST",
        data: {
          action: "respond",
          checkpoint_id: checkpointId,
          responses: responses,
        },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["validation-checkpoint"] });
    },
  });
}

/**
 * Hook to skip a checkpoint
 */
export function useSkipCheckpoint() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation<SubmitResponse, Error, { checkpointId: string; reason?: string }>({
    mutationFn: async ({ checkpointId, reason }) => {
      const { data } = await axios({
        url: "/dd-validation-checkpoint",
        method: "POST",
        data: {
          action: "skip",
          checkpoint_id: checkpointId,
          reason: reason,
        },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["validation-checkpoint"] });
    },
  });
}

/**
 * Hook to create a checkpoint (typically called by backend, but exposed for manual creation)
 */
export function useCreateCheckpoint() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation<{ checkpoint_id: string }, Error, {
    ddId: string;
    runId: string;
    checkpointType: CheckpointType;
    content: {
      preliminary_summary?: string;
      questions?: UnderstandingQuestion[] | EntityQuestion[];
      missing_docs?: MissingDocument[];
      financial_confirmations?: FinancialConfirmation[];
    };
  }>({
    mutationFn: async ({ ddId, runId, checkpointType, content }) => {
      const { data } = await axios({
        url: "/dd-validation-checkpoint",
        method: "POST",
        data: {
          action: "create",
          dd_id: ddId,
          run_id: runId,
          checkpoint_type: checkpointType,
          content: content,
        },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["validation-checkpoint"] });
    },
  });
}

/**
 * Hook to regenerate the preliminary summary using AI with user corrections
 */
export function useRegenerateSummary() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation<
    {
      success: boolean;
      updated_summary: string;
      corrections_applied?: {
        question_corrections: number;
        financial_corrections: number;
      };
      message: string;
      error?: string;
    },
    Error,
    {
      checkpointId: string;
      corrections: {
        question_responses?: Record<string, QuestionResponse>;
        financial_confirmations?: FinancialResponse[];
      };
    }
  >({
    mutationFn: async ({ checkpointId, corrections }) => {
      const { data } = await axios({
        url: "/dd-validation-checkpoint",
        method: "POST",
        data: {
          action: "regenerate_summary",
          checkpoint_id: checkpointId,
          corrections: corrections,
        },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["validation-checkpoint"] });
    },
  });
}
