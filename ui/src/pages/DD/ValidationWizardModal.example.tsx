/**
 * Example Integration: How to use ValidationWizardModal in the Processing Dashboard
 *
 * This file shows how to integrate the ValidationWizardModal component
 * into your existing DD Processing workflow.
 */

import React, { useState, useEffect } from "react";
import { ValidationWizardModal } from "./ValidationWizardModal";
import { useValidationCheckpoint, CheckpointData } from "@/hooks/useValidationCheckpoint";

// ============================================
// Example 1: Basic Integration in Processing Dashboard
// ============================================

interface ProcessingDashboardExampleProps {
  ddId: string;
  currentRunId: string | null;
}

export function ProcessingDashboardExample({ ddId, currentRunId }: ProcessingDashboardExampleProps) {
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [activeCheckpoint, setActiveCheckpoint] = useState<CheckpointData | null>(null);

  // Fetch pending checkpoint
  const { data: checkpointResponse, refetch: refetchCheckpoint } = useValidationCheckpoint(
    ddId,
    !!ddId // Only enable when ddId exists
  );

  // Check for pending checkpoint when data arrives
  useEffect(() => {
    if (checkpointResponse?.has_checkpoint && checkpointResponse.checkpoint) {
      const checkpoint = checkpointResponse.checkpoint;

      // Only show modal for awaiting_user_input status
      if (checkpoint.status === "awaiting_user_input") {
        setActiveCheckpoint(checkpoint);
        setShowValidationModal(true);
      }
    }
  }, [checkpointResponse]);

  const handleCheckpointComplete = () => {
    setShowValidationModal(false);
    setActiveCheckpoint(null);
    // Refetch to check if there are more checkpoints
    refetchCheckpoint();
    // Continue processing...
  };

  const handleCheckpointSkip = () => {
    setShowValidationModal(false);
    setActiveCheckpoint(null);
    // Refetch and continue
    refetchCheckpoint();
  };

  return (
    <>
      {/* Your existing dashboard content */}
      <div>
        {/* ... processing dashboard UI ... */}
      </div>

      {/* Validation Wizard Modal */}
      {activeCheckpoint && (
        <ValidationWizardModal
          open={showValidationModal}
          onClose={() => setShowValidationModal(false)}
          checkpoint={activeCheckpoint}
          ddId={ddId}
          onComplete={handleCheckpointComplete}
          onSkip={handleCheckpointSkip}
        />
      )}
    </>
  );
}

// ============================================
// Example 2: Manual Checkpoint Trigger
// ============================================

import { useCreateCheckpoint, UnderstandingQuestion, FinancialConfirmation, MissingDocument } from "@/hooks/useValidationCheckpoint";

export function ManualCheckpointExample({ ddId, runId }: { ddId: string; runId: string }) {
  const createCheckpoint = useCreateCheckpoint();

  const triggerPostAnalysisCheckpoint = async () => {
    // Example: Create a post_analysis checkpoint with generated questions
    const questions: UnderstandingQuestion[] = [
      {
        question_id: "q1",
        question: "Is the corporate structure correct?",
        context: "We understand ABC Holdings is acquiring 100% of XYZ Mining",
        ai_assessment: "ABC Holdings (Buyer) → acquiring 100% of XYZ Mining, which has 2 subsidiaries",
        confidence: 0.85,
        options: [
          { value: "correct", label: "Yes, this is correct" },
          { value: "partial", label: "Partially correct" },
          { value: "incorrect", label: "No, this is incorrect" },
        ],
      },
      {
        question_id: "q2",
        question: "What is the expected closing date?",
        context: "Documents reference various dates",
        ai_assessment: "We identified March 2026 as the target closing date",
        confidence: 0.70,
      },
    ];

    const financialConfirmations: FinancialConfirmation[] = [
      {
        metric: "Revenue (FY2024)",
        extracted_value: 145000000,
        currency: "ZAR",
        source_document: "Annual Financial Statements.pdf",
        confidence: 0.92,
      },
      {
        metric: "Net Profit (FY2024)",
        extracted_value: 12500000,
        currency: "ZAR",
        source_document: "Annual Financial Statements.pdf",
        confidence: 0.90,
      },
      {
        metric: "Total Debt",
        extracted_value: 85000000,
        currency: "ZAR",
        source_document: "Facility Agreement.pdf",
        confidence: 0.88,
      },
    ];

    const missingDocs: MissingDocument[] = [
      {
        doc_type: "Group Structure Chart",
        description: "Organizational chart showing subsidiary relationships",
        importance: "high",
        reason: "Would help clarify subsidiary relationships identified in MOI",
        expected_folder: "01_Corporate",
      },
      {
        doc_type: "Latest Management Accounts",
        description: "Month-end management accounts for current period",
        importance: "medium",
        reason: "Would verify current financial position vs annual statements",
        expected_folder: "03_Financial",
      },
    ];

    await createCheckpoint.mutateAsync({
      ddId,
      runId,
      checkpointType: "post_analysis",
      content: {
        preliminary_summary:
          "This appears to be an acquisition of XYZ Mining (Pty) Ltd by ABC Holdings, structured as a share sale for approximately R150 million. The target holds mining rights in Limpopo Province expiring in 2030.",
        questions,
        financial_confirmations: financialConfirmations,
        missing_docs: missingDocs,
      },
    });
  };

  return (
    <button onClick={triggerPostAnalysisCheckpoint}>
      Trigger Validation Checkpoint
    </button>
  );
}

// ============================================
// Example 3: Polling for Checkpoints During Processing
// ============================================

export function ProcessingWithCheckpointPolling({ ddId, runId }: { ddId: string; runId: string }) {
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [activeCheckpoint, setActiveCheckpoint] = useState<CheckpointData | null>(null);
  const [processingPaused, setProcessingPaused] = useState(false);

  // Poll for checkpoints every 30 seconds during processing
  const { data: checkpointResponse } = useValidationCheckpoint(
    ddId,
    !processingPaused // Disable polling while modal is open
  );

  useEffect(() => {
    if (checkpointResponse?.has_checkpoint && checkpointResponse.checkpoint) {
      const checkpoint = checkpointResponse.checkpoint;

      if (checkpoint.status === "awaiting_user_input") {
        // Pause processing and show modal
        setProcessingPaused(true);
        setActiveCheckpoint(checkpoint);
        setShowValidationModal(true);
      }
    }
  }, [checkpointResponse]);

  const handleComplete = () => {
    setShowValidationModal(false);
    setActiveCheckpoint(null);
    // Resume processing
    setProcessingPaused(false);
  };

  return (
    <>
      {/* Processing UI */}
      <div>
        {processingPaused && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-yellow-800">
              Processing paused - validation required
            </p>
          </div>
        )}
      </div>

      {/* Modal */}
      {activeCheckpoint && (
        <ValidationWizardModal
          open={showValidationModal}
          onClose={() => {
            setShowValidationModal(false);
            setProcessingPaused(false);
          }}
          checkpoint={activeCheckpoint}
          ddId={ddId}
          onComplete={handleComplete}
          onSkip={handleComplete}
        />
      )}
    </>
  );
}

// ============================================
// Example 4: Using in Findings Explorer for Entity Confirmation
// ============================================

import { EntityQuestion } from "@/hooks/useValidationCheckpoint";

export function EntityConfirmationExample({ ddId, runId }: { ddId: string; runId: string }) {
  const createCheckpoint = useCreateCheckpoint();
  const [showModal, setShowModal] = useState(false);
  const [checkpoint, setCheckpoint] = useState<CheckpointData | null>(null);

  const triggerEntityConfirmation = async () => {
    const entities: EntityQuestion[] = [
      {
        entity_name: "Pamish Investments (Pty) Ltd",
        registration_number: "2008/054321/07",
        appears_in_documents: 47,
        ai_assessment: "Likely a related party - ore supplier",
        confidence: 0.85,
        suggested_relationship: "related_party",
      },
      {
        entity_name: "Unknown Mining Services CC",
        appears_in_documents: 2,
        ai_assessment: "Relationship unclear from documents",
        confidence: 0.30,
      },
    ];

    const result = await createCheckpoint.mutateAsync({
      ddId,
      runId,
      checkpointType: "entity_confirmation",
      content: {
        preliminary_summary: "We found entities that couldn't be confidently linked to your target company.",
        questions: entities,
      },
    });

    // Fetch the created checkpoint and show modal
    // In production, you'd fetch this from the API
    setCheckpoint({
      id: result.checkpoint_id,
      checkpoint_type: "entity_confirmation",
      status: "awaiting_user_input",
      questions: entities,
    });
    setShowModal(true);
  };

  return (
    <>
      <button onClick={triggerEntityConfirmation}>
        Confirm Entity Relationships
      </button>

      {checkpoint && (
        <ValidationWizardModal
          open={showModal}
          onClose={() => setShowModal(false)}
          checkpoint={checkpoint}
          ddId={ddId}
          onComplete={() => {
            setShowModal(false);
            setCheckpoint(null);
          }}
        />
      )}
    </>
  );
}

export default ProcessingDashboardExample;
