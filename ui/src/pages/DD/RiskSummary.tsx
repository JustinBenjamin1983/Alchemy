// File: ui/src/pages/DD/RiskSummary.tsx
import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { useGetDDRiskResults } from "@/hooks/useGetDDRiskResults";
import { useMutateDDRiskAdd } from "@/hooks/useMutateDDRiskAdd";
import { useMutateDDRiskEdit } from "@/hooks/useMutateDDRiskEdit";
import { useGetDD } from "@/hooks/useGetDD";
import EnhancedRiskManager from "./EnhancedRiskManager";
import SingleTextPrompt from "@/components/SingleTextPrompt";
import { useAnalysisRunsList } from "@/hooks/useAnalysisRuns";
import { FindingsExplorer } from "./FindingsExplorer";
import { useMutateExportDDReport } from "@/hooks/useMutateExportDDReport";
import { useMutateGetLink } from "@/hooks/useMutateGetLink";
import { useMutateChat } from "@/hooks/useMutateChat";
import { useToast } from "@/components/ui/use-toast";
import type {
  Finding as ExplorerFinding,
  RunInfo,
  HumanReview,
  ChatMessage,
  CompletenessCheckData,
  MissingItemStatus
} from "./FindingsExplorer/types";

type DocRef = {
  id: string;
  original_file_name: string;
  type?: string;
  converted_doc_id?: string;
  folder: { path: string; category?: string };
};

type FindingReasoning = {
  step_1_identification?: string;
  step_2_context?: string;
  step_3_transaction_impact?: string;
  step_4_severity_reasoning?: string;
  step_5_deal_impact_reasoning?: string;
  step_6_financial_quantification?: string;
};

type FinancialExposure = {
  amount: number | null;
  currency: string;
  calculation: string | null;
};

type Finding = {
  finding_id?: string;
  perspective_risk_id?: string;
  finding_type?: "positive" | "negative" | "gap" | "neutral" | "informational";
  finding_status?: "New" | "Red" | "Amber" | "Green" | "Info" | "Deleted";
  confidence_score?: number;
  direct_answer?: string;
  phrase?: string;
  evidence_quote?: string;
  requires_action?: boolean;
  action_items?: string;
  missing_documents?: string;
  document: DocRef;
  page_number?: number;
  actual_page_number?: number;
  clause_reference?: string;
  finding_is_reviewed?: boolean;
  detail?: string;
  category?: string;
  // Chain of Thought reasoning from AI
  reasoning?: FindingReasoning;
  // Financial exposure with calculation details
  financial_exposure?: FinancialExposure;
  deal_impact?: string;
  // Gap-specific fields
  gap_reason?: 'documents_not_provided' | 'information_not_found' | 'inconclusive';
  gap_detail?: string;
  documents_analyzed_count?: number;
};

// Helper to format structured reasoning into readable chain of thought
function formatReasoningToChainOfThought(reasoning?: FindingReasoning): string | undefined {
  if (!reasoning) return undefined;

  const sections: string[] = [];

  if (reasoning.step_1_identification) {
    sections.push(`**Identification:** ${reasoning.step_1_identification}`);
  }
  if (reasoning.step_2_context) {
    sections.push(`**Context:** ${reasoning.step_2_context}`);
  }
  if (reasoning.step_3_transaction_impact) {
    sections.push(`**Transaction Impact:** ${reasoning.step_3_transaction_impact}`);
  }
  if (reasoning.step_4_severity_reasoning) {
    sections.push(`**Severity Reasoning:** ${reasoning.step_4_severity_reasoning}`);
  }
  if (reasoning.step_5_deal_impact_reasoning) {
    sections.push(`**Deal Impact Reasoning:** ${reasoning.step_5_deal_impact_reasoning}`);
  }
  if (reasoning.step_6_financial_quantification) {
    sections.push(`**Financial Quantification:** ${reasoning.step_6_financial_quantification}`);
  }

  return sections.length > 0 ? sections.join('\n\n') : undefined;
}

// Main component
export function RiskSummary() {
  const [selectedDDID] = useState(() => {
    const query = new URLSearchParams(location.search);
    return query.get("id");
  });

  // State management
  const [showEnhancedRiskManager, setShowEnhancedRiskManager] = useState(false);
  const [showEditRisk, setShowEditRisk] = useState(false);
  const [selectedRisk, setSelectedRisk] = useState<{ id: string; detail: string } | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  // Human Review state
  const [findingReviews, setFindingReviews] = useState<Record<string, HumanReview>>({});

  // AI Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Completeness Check state (mock data for now - will be fetched from API)
  const [completenessData, setCompletenessData] = useState<CompletenessCheckData>({
    missing_documents: [],
    unanswered_questions: [],
    completeness_score: 100,
    documents_received: 0,
    documents_expected: 0,
    questions_answered: 0,
    questions_total: 0,
    last_checked_at: new Date().toISOString()
  });
  const [isCompletenessLoading, setIsCompletenessLoading] = useState(false);

  // Report generation state
  const [reportTypeLoading, setReportTypeLoading] = useState<'preliminary' | 'final' | null>(null);

  // Hooks
  const mutateAddRisk = useMutateDDRiskAdd();
  const mutateEditRisk = useMutateDDRiskEdit();
  const exportReportMutation = useMutateExportDDReport();
  const mutateGetLink = useMutateGetLink();
  const chatMutation = useMutateChat();
  const { toast } = useToast();

  const { data: runsData } = useAnalysisRunsList(selectedDDID || undefined);
  const { data: dd } = useGetDD(selectedDDID);

  const {
    data: riskResultsRaw,
    refetch: refetchRiskResults,
    isFetching: isRiskResultsFetching,
  } = useGetDDRiskResults(selectedDDID, selectedRunId);

  const riskResults = (riskResultsRaw ?? []) as Array<{
    category?: string;
    findings?: Finding[];
  }>;

  // Auto-select the most recent completed run if none selected
  useEffect(() => {
    if (runsData?.runs && runsData.runs.length > 0 && !selectedRunId) {
      const completedRuns = runsData.runs.filter((r) => r.status === "completed");
      if (completedRuns.length > 0) {
        setSelectedRunId(completedRuns[0].run_id);
      }
    }
  }, [runsData, selectedRunId]);

  // Get synthesis data from selected run
  const selectedRunSynthesis = useMemo(() => {
    if (!runsData?.runs || !selectedRunId) return null;
    const selectedRun = runsData.runs.find((r) => r.run_id === selectedRunId);
    return selectedRun?.synthesis_data || null;
  }, [runsData, selectedRunId]);

  // Get all analyzed documents from selected run
  const selectedRunDocuments = useMemo(() => {
    if (!runsData?.runs || !selectedRunId) return [];
    const selectedRun = runsData.runs.find((r) => r.run_id === selectedRunId);
    return selectedRun?.selected_documents || [];
  }, [runsData, selectedRunId]);

  // Manual refresh function
  const handleManualRefresh = useCallback(async () => {
    try {
      await refetchRiskResults();
    } catch (error) {
      console.warn("Refresh error:", error);
    }
  }, [refetchRiskResults]);

  // Process findings
  const allFindings: Finding[] = useMemo(() => {
    if (!riskResults) return [];
    return riskResults.flatMap((category) =>
      (category.findings ?? []).map((finding) => ({
        ...finding,
        category: category.category ?? "Uncategorized",
      }))
    );
  }, [riskResults]);

  // Transform findings for FindingsExplorer component
  const explorerFindings: ExplorerFinding[] = useMemo(() => {
    return allFindings.map((f, index) => {
      let severity: ExplorerFinding['severity'] = 'medium';
      if (f.finding_status === 'Red' || f.finding_type === 'negative') {
        severity = f.finding_status === 'Red' ? 'critical' : 'high';
      } else if (f.finding_status === 'Amber') {
        severity = 'medium';
      } else if (f.finding_status === 'Green' || f.finding_type === 'positive') {
        severity = 'positive';
      } else if (f.finding_type === 'gap' || f.finding_status === 'Info') {
        severity = 'gap';
      } else if (f.finding_type === 'neutral' || f.finding_type === 'informational') {
        severity = 'low';
      }

      // Use folder_category directly from the API (e.g., "01_Corporate")
      const folderCategory = f.document?.folder?.category || undefined;

      return {
        id: f.finding_id || `finding-${index}`,
        title: f.direct_answer || f.phrase || 'Finding',
        severity,
        category: f.category || 'Uncategorized',
        document_id: f.document?.id || '',
        document_name: f.document?.original_file_name || 'Unknown Document',
        document_type: f.document?.type || undefined,
        converted_doc_id: f.document?.converted_doc_id || undefined,
        page_reference: f.page_number ? `Page ${f.page_number}` : undefined,
        actual_page_number: f.actual_page_number || undefined,
        clause_reference: f.clause_reference || undefined,
        evidence_quote: f.evidence_quote || undefined,
        source_text: f.evidence_quote,
        analysis: f.phrase || f.direct_answer || '',
        chain_of_thought: formatReasoningToChainOfThought(f.reasoning),
        recommendation: f.action_items ? JSON.parse(f.action_items).join('\n') : undefined,
        confidence_score: f.confidence_score,
        folder_category: folderCategory,
        // Financial exposure with calculation details
        financial_exposure: f.financial_exposure ? {
          amount: f.financial_exposure.amount,
          currency: f.financial_exposure.currency || 'ZAR',
          calculation: f.financial_exposure.calculation
        } : undefined,
        deal_impact: f.deal_impact,
        // Gap-specific fields
        gap_reason: f.gap_reason,
        gap_detail: f.gap_detail,
        documents_analyzed_count: f.documents_analyzed_count,
      };
    });
  }, [allFindings]);

  // Transform runs for FindingsExplorer component
  const explorerRuns: RunInfo[] = useMemo(() => {
    if (!runsData?.runs) return [];
    return runsData.runs.map((run) => ({
      id: run.run_id,
      run_number: run.run_number || 1,
      status: run.status,
      created_at: run.created_at,
      completed_at: run.completed_at,
      total_findings: run.findings_total || 0,
      critical_findings: run.findings_critical || 0,
      documents_processed: run.total_documents || run.selected_documents?.length || 0,
      total_tokens: run.total_tokens,
      total_cost: run.total_cost,
    }));
  }, [runsData]);

  // Effects for mutations
  useEffect(() => {
    if (mutateAddRisk.isSuccess) {
      setShowEnhancedRiskManager(false);
    }
  }, [mutateAddRisk.isSuccess]);

  useEffect(() => {
    if (mutateEditRisk.isSuccess) {
      setShowEditRisk(false);
      setSelectedRisk(null);
    }
  }, [mutateEditRisk.isSuccess]);

  // Handlers
  const handleEnhancedRiskManagerSubmit = (newRisks: any[]) => {
    const formattedRisks = newRisks.map((risk) => ({
      category: risk.category,
      detail: risk.detail,
      folder_scope: risk.folder_scope,
    }));
    mutateAddRisk.mutate(
      { dd_id: selectedDDID, risks: formattedRisks },
      { onSuccess: () => handleManualRefresh() }
    );
  };

  const closingEditRisk = (value: string | null) => {
    if (value == null) {
      setShowEditRisk(false);
    } else if (selectedRisk) {
      mutateEditRisk.mutate({
        dd_id: selectedDDID,
        perspective_risk_id: selectedRisk.id,
        detail: value,
      });
    }
  };

  // Human Review handlers
  const handleUpdateFindingReview = useCallback((findingId: string, review: Partial<HumanReview>) => {
    setFindingReviews(prev => ({
      ...prev,
      [findingId]: {
        ...prev[findingId],
        ...review,
        reviewed_at: new Date().toISOString()
      } as HumanReview
    }));
    // TODO: Persist to backend API
    console.log('Review updated:', findingId, review);
  }, []);

  // AI Chat handlers
  const handleSendChatMessage = useCallback((message: string, context?: { findingId?: string; documentId?: string }) => {
    if (!selectedDDID) return;

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
      finding_id: context?.findingId,
      document_id: context?.documentId
    };
    setChatMessages(prev => [...prev, userMessage]);
    setIsChatLoading(true);

    // Call the actual DDChat API with Claude
    chatMutation.mutate(
      {
        question: message,
        dd_id: selectedDDID,
        run_id: selectedRunId || undefined,
        document_id: context?.documentId,
      },
      {
        onSuccess: (response) => {
          const answer = response?.data?.answer || 'No response received from the AI.';
          const assistantMessage: ChatMessage = {
            id: `msg-${Date.now() + 1}`,
            role: 'assistant',
            content: answer,
            timestamp: new Date().toISOString(),
            finding_id: context?.findingId,
            document_id: context?.documentId
          };
          setChatMessages(prev => [...prev, assistantMessage]);
          setIsChatLoading(false);
        },
        onError: (error) => {
          console.error('Chat error:', error);
          const errorMessage: ChatMessage = {
            id: `msg-${Date.now() + 1}`,
            role: 'assistant',
            content: 'Sorry, I encountered an error processing your question. Please try again.',
            timestamp: new Date().toISOString(),
            finding_id: context?.findingId,
            document_id: context?.documentId
          };
          setChatMessages(prev => [...prev, errorMessage]);
          setIsChatLoading(false);
        }
      }
    );
  }, [selectedDDID, selectedRunId, chatMutation]);

  // Completeness Check handlers
  const handleUpdateDocumentStatus = useCallback((docId: string, status: MissingItemStatus, note?: string) => {
    setCompletenessData(prev => ({
      ...prev,
      missing_documents: prev.missing_documents.map(doc =>
        doc.id === docId ? { ...doc, status, note: note ?? doc.note } : doc
      )
    }));
    // TODO: Persist to backend API
    console.log('Document status updated:', docId, status);
  }, []);

  const handleUpdateQuestionStatus = useCallback((questionId: string, status: MissingItemStatus, note?: string) => {
    setCompletenessData(prev => ({
      ...prev,
      unanswered_questions: prev.unanswered_questions.map(q =>
        q.id === questionId ? { ...q, status, note: note ?? q.note } : q
      )
    }));
    // TODO: Persist to backend API
    console.log('Question status updated:', questionId, status);
  }, []);

  const handleGenerateRequestLetter = useCallback(() => {
    // TODO: Call API to generate request letter using Claude
    console.log('Generating request letter...');
    alert('Request letter generation will be implemented with Claude API integration.');
  }, []);

  const handleRefreshCompletenessAssessment = useCallback(() => {
    setIsCompletenessLoading(true);
    // TODO: Call API to refresh completeness assessment using Claude
    console.log('Refreshing completeness assessment...');
    setTimeout(() => {
      // Mock assessment result
      setCompletenessData(prev => ({
        ...prev,
        last_checked_at: new Date().toISOString()
      }));
      setIsCompletenessLoading(false);
    }, 2000);
  }, []);

  // Report download handler - calls API to generate Word document
  const handleDownloadReport = useCallback((type: 'preliminary' | 'final') => {
    console.log('[Report] Download requested:', { type, ddId: selectedDDID, runId: selectedRunId });
    if (!selectedDDID) {
      console.warn('[Report] No DD ID selected');
      return;
    }

    console.log('[Report] Calling export API with run_id:', selectedRunId);
    setReportTypeLoading(type);
    exportReportMutation.mutate(
      {
        dd_id: selectedDDID,
        run_id: selectedRunId,  // Pass selected run to filter findings
        report_type: type,
      },
      {
        onSettled: () => {
          setReportTypeLoading(null);
        },
      }
    );
  }, [selectedDDID, selectedRunId, exportReportMutation]);

  // Document view handler - opens document in new tab
  const handleOpenDocumentInTab = useCallback((docId: string) => {
    mutateGetLink.mutate(
      { doc_id: docId, is_dd: true },
      {
        onSuccess: (data) => {
          const url = data?.data?.url;
          if (url) {
            window.open(url, "_blank", "noopener,noreferrer");
          }
        },
        onError: (error: any) => {
          console.error("Failed to get document link:", error);
          const errorMessage = error?.response?.data?.message || error?.message || "Unknown error";
          toast({
            title: "Failed to open document",
            description: errorMessage,
            variant: "destructive",
          });
        },
      }
    );
  }, [mutateGetLink, toast]);

  // Document download handler
  const handleDownloadDocument = useCallback((docId: string) => {
    mutateGetLink.mutate(
      { doc_id: docId, is_dd: true },
      {
        onSuccess: (data) => {
          const url = data?.data?.url;
          if (url) {
            const link = document.createElement("a");
            link.href = url;
            link.download = "";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }
        },
        onError: (error: any) => {
          console.error("Failed to get document link:", error);
          const errorMessage = error?.response?.data?.message || error?.message || "Unknown error";
          toast({
            title: "Failed to download document",
            description: errorMessage,
            variant: "destructive",
          });
        },
      }
    );
  }, [mutateGetLink, toast]);

  return (
    <div className="p-6 pb-32 space-y-4 bg-gray-200 dark:bg-gray-900 min-h-screen">
      {/* Modals */}
      <EnhancedRiskManager
        folders={dd?.folders ?? []}
        isOpen={showEnhancedRiskManager}
        onClose={() => setShowEnhancedRiskManager(false)}
        onSubmit={handleEnhancedRiskManagerSubmit}
        isSubmitting={mutateAddRisk.isPending}
      />

      <SingleTextPrompt
        show={showEditRisk}
        onClosing={closingEditRisk}
        header={`Edit question - ${selectedRisk?.detail}`}
        label="Question Detail"
        warning="Editing a question will invalidate all findings linked to it"
      />

      {/* Main Content - Explorer View */}
      {selectedDDID && (
        <div>
          <FindingsExplorer
            ddId={selectedDDID}
            runs={explorerRuns}
            selectedRunId={selectedRunId}
            onRunSelect={setSelectedRunId}
            findings={explorerFindings}
            isLoading={isRiskResultsFetching}
            // Human Review
            findingReviews={findingReviews}
            onUpdateFindingReview={handleUpdateFindingReview}
            // AI Chat
            chatMessages={chatMessages}
            onSendChatMessage={handleSendChatMessage}
            isChatLoading={isChatLoading}
            // Completeness Check
            completenessData={completenessData}
            onUpdateDocumentStatus={handleUpdateDocumentStatus}
            onUpdateQuestionStatus={handleUpdateQuestionStatus}
            onGenerateRequestLetter={handleGenerateRequestLetter}
            onRefreshCompletenessAssessment={handleRefreshCompletenessAssessment}
            isCompletenessLoading={isCompletenessLoading}
            // Report Generation
            onDownloadReport={handleDownloadReport}
            reportTypeLoading={reportTypeLoading}
            // Synthesis Data
            synthesisData={selectedRunSynthesis}
            // All analyzed documents from the run
            analyzedDocuments={selectedRunDocuments}
            // Document Actions
            onOpenDocumentInTab={handleOpenDocumentInTab}
            onDownloadDocument={handleDownloadDocument}
          />
        </div>
      )}
    </div>
  );
}
