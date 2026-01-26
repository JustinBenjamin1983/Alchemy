/**
 * DD Dashboard (formerly Processing Dashboard)
 *
 * Three-phase dashboard:
 * Phase 1: Document Organisation - AI classifies documents into categories
 * Phase 2: Document Readability Check - validates all documents before processing
 * Phase 3: Due Diligence Analysis - runs the 7-pass DD pipeline
 *
 * The 7-pass pipeline:
 * - Pass 1 (Extract): Haiku extraction of key data
 * - Pass 2 (Analyze): Sonnet document analysis
 * - Pass 2.5 (Calculate): Python calculations from extracted data
 * - Pass 3 (Cross-Doc): Opus cross-document analysis
 * - Pass 3.5 (Aggregate): Python aggregation of calculations
 * - Pass 4 (Synthesize): Sonnet synthesis of findings
 * - Pass 5 (Verify): Opus verification of deal-blockers and calculations
 *
 * Features:
 * - Document checklist with classification and readability status
 * - AI classification progress with confidence indicators
 * - "Run Due Diligence" button (enabled after organisation and readability passes)
 * - Animated concentric pipeline rings showing 7-pass progress
 * - Process log with attorney-friendly messages
 * - Confirmation popups before starting
 */
import React, { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useParams, useNavigate } from "react-router-dom";
import { Play, Pause, Square, AlertTriangle, CheckCircle2, Loader2, X, RotateCcw, RefreshCw, ClipboardCheck } from "lucide-react";
import { ProcessingProgress, RiskSummary, PASS_CONFIG, STATUS_COLORS, RING_COLORS, ProcessingPass } from "./types";
import {
  useProcessingProgress,
  useElapsedTime,
  useReducedMotion,
  useStartProcessing,
} from "./hooks";
import { PipelineRings } from "./PipelineRings";
import { RiskSummaryCounters } from "./FindingsFeed";
import { FileTree } from "./FileTree";
import { DocumentItem } from "./DocumentChecklistPanel";
import { ProcessLog, LogEntry, createLogEntry } from "./ProcessLog";
import { TransactionSummary } from "./TransactionSummary";
import { useCheckReadability } from "@/hooks/useCheckReadability";
import { useGetDD } from "@/hooks/useGetDD";
import { useCreateAnalysisRun, useAnalysisRunsList } from "@/hooks/useAnalysisRuns";
import { useOrganisationProgress, useClassifyDocuments, useOrganiseFolders, useDocumentReassign, useCancelOrganisation } from "@/hooks/useOrganisationProgress";
import { useBlueprintRequirements } from "@/hooks/useBlueprintRequirements";
import { useDeleteDocument } from "@/hooks/useDeleteDocument";
import useEntityMapping, { useGetEntityMap } from "@/hooks/useEntityMapping";
import { CategoryCount, CategoryDocument } from "./FileTree/FileTree";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { celebrationVariants, SPRING_GENTLE } from "./animations";
import { AccuracyTierSelector, ModelTier } from "./AccuracyTierSelector";
import { ControlBar } from "./ControlBar";
import { useValidationCheckpoint } from "@/hooks/useValidationCheckpoint";
import { ValidationWizardModal } from "../ValidationWizardModal";
import { EntityMappingModal, EntityMappingResult } from "./EntityMappingModal";

interface DDProcessingDashboardProps {
  ddId?: string;
  documents?: DocumentItem[];
  onBack?: () => void;
  onViewResults?: () => void;
  onReclassify?: () => void;
}

type DashboardPhase = "classifying" | "classified" | "organising" | "organised" | "readability" | "ready" | "processing" | "completed" | "failed" | "cancelled";

export const DDProcessingDashboard: React.FC<DDProcessingDashboardProps> = ({
  ddId: propDdId,
  documents: propDocuments = [],
  onBack,
  onViewResults,
  onReclassify,
}) => {
  const params = useParams<{ ddId: string }>();
  const navigate = useNavigate();
  const reducedMotion = useReducedMotion();

  const ddId = propDdId || params.ddId || "";

  // Local state
  const [selectedDocIds, setSelectedDocIds] = useState<Set<string>>(new Set());
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [showWarningDialog, setShowWarningDialog] = useState(false);
  const [showRerunWarningDialog, setShowRerunWarningDialog] = useState(false);
  const [matchingCompletedRun, setMatchingCompletedRun] = useState<{ name: string; completedAt: string } | null>(null);
  const [isDocPanelCollapsed, setIsDocPanelCollapsed] = useState(false);
  const [isLogCollapsed, setIsLogCollapsed] = useState(false);
  const [isSummaryCollapsed, setIsSummaryCollapsed] = useState(false);
  const [readabilityChecked, setReadabilityChecked] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isRestarting, setIsRestarting] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [dismissedRuns, setDismissedRuns] = useState<Set<string>>(new Set());
  const [userHasModifiedSelection, setUserHasModifiedSelection] = useState(false);
  const [customCategories, setCustomCategories] = useState<string[]>([]);
  const [deletedCategories, setDeletedCategories] = useState<Set<string>>(new Set());
  const [logEntriesLoaded, setLogEntriesLoaded] = useState(false);
  const [selectedModelTier, setSelectedModelTier] = useState<ModelTier>("balanced");

  // Track dismissed completion popups per run in localStorage
  const getCompletionDismissedKey = (runId: string) => `dd-completion-dismissed-${runId}`;

  // Log entries storage key (per DD project, not per run - so we see full history)
  const getLogEntriesKey = (id: string) => `dd-log-entries-${id}`;

  // Load log entries from localStorage when component mounts or ddId changes
  useEffect(() => {
    if (ddId) {
      try {
        const stored = localStorage.getItem(getLogEntriesKey(ddId));
        if (stored) {
          const parsed = JSON.parse(stored);
          // Restore Date objects from ISO strings
          const restored = parsed.map((entry: LogEntry & { timestamp: string }) => ({
            ...entry,
            timestamp: new Date(entry.timestamp),
          }));
          setLogEntries(restored);
        }
      } catch (e) {
        console.error("Failed to load log entries from localStorage:", e);
      }
      setLogEntriesLoaded(true);
    }
  }, [ddId]);

  // Save log entries to localStorage whenever they change (after initial load)
  useEffect(() => {
    if (ddId && logEntriesLoaded && logEntries.length > 0) {
      try {
        // Keep only the last 500 entries to prevent localStorage bloat
        const toStore = logEntries.slice(-500);
        localStorage.setItem(getLogEntriesKey(ddId), JSON.stringify(toStore));
      } catch (e) {
        console.error("Failed to save log entries to localStorage:", e);
      }
    }
  }, [ddId, logEntries, logEntriesLoaded]);

  // Initialize dismissedRuns from localStorage on mount
  useEffect(() => {
    if (currentRunId) {
      const isDismissed = localStorage.getItem(getCompletionDismissedKey(currentRunId)) === "true";
      if (isDismissed) {
        setDismissedRuns((prev) => new Set(prev).add(currentRunId));
      }
    }
  }, [currentRunId]);

  const isCompletionDismissed = useCallback((runId: string | null) => {
    if (!runId) return false;
    return dismissedRuns.has(runId) || localStorage.getItem(getCompletionDismissedKey(runId)) === "true";
  }, [dismissedRuns]);

  const setCompletionDismissed = useCallback((runId: string | null) => {
    if (runId) {
      localStorage.setItem(getCompletionDismissedKey(runId), "true");
      setDismissedRuns((prev) => new Set(prev).add(runId));
    }
  }, []);

  // Poll interval state - faster during active processing
  const [pollInterval, setPollInterval] = useState(5000);

  // Hooks
  const { data: ddData, refetch: refetchDD } = useGetDD(ddId, !!ddId);
  const { data: runsData } = useAnalysisRunsList(ddId || undefined);
  const { progress: rawProgress, isLoading, error, refetch } = useProcessingProgress(ddId, pollInterval, currentRunId);
  const checkReadability = useCheckReadability();
  const { startProcessing, isStarting, error: startError } = useStartProcessing();
  const createRun = useCreateAnalysisRun();

  // Validation checkpoint hook - polls for pending checkpoints during processing
  const { data: checkpointData, refetch: refetchCheckpoint } = useValidationCheckpoint(ddId || undefined);
  const [showValidationWizard, setShowValidationWizard] = useState(false);

  // Auto-show validation wizard when checkpoint is awaiting user input
  useEffect(() => {
    if (checkpointData?.has_checkpoint && checkpointData.checkpoint?.status === 'awaiting_user_input') {
      setShowValidationWizard(true);
    }
  }, [checkpointData]);

  // Sanitized progress - returns undefined during new run creation to reset UI
  // This ensures pipeline rings, progress bars, and elapsed time reset when starting a new run
  const progress = useMemo(() => {
    const isNewRunPending = createRun.isPending || isStarting;
    const isProgressStale = rawProgress?.runId && currentRunId && rawProgress.runId !== currentRunId;

    if (isNewRunPending || isProgressStale) {
      return undefined;
    }
    return rawProgress;
  }, [rawProgress, createRun.isPending, isStarting, currentRunId]);

  const elapsedTime = useElapsedTime(progress?.startedAt || null, progress?.status);

  // Adjust polling speed based on processing status
  useEffect(() => {
    if (progress?.status === "processing") {
      setPollInterval(2000); // Fast polling during active processing
    } else {
      setPollInterval(5000); // Normal polling otherwise
    }
  }, [progress?.status]);

  // Organisation/Classification hooks
  const { data: organisationProgress, refetch: refetchOrganisation } = useOrganisationProgress(ddId || undefined);
  const classifyDocuments = useClassifyDocuments();
  const organiseFolders = useOrganiseFolders();
  const documentReassign = useDocumentReassign();
  const cancelOrganisation = useCancelOrganisation();
  const deleteDocument = useDeleteDocument();
  const entityMapping = useEntityMapping();

  // Entity mapping state
  const [entityMappingComplete, setEntityMappingComplete] = useState(false);
  const [entityCount, setEntityCount] = useState(0);
  const [showEntityMappingModal, setShowEntityMappingModal] = useState(false);
  const [entityMappingResult, setEntityMappingResult] = useState<EntityMappingResult | null>(null);

  // Fetch stored entity map on page load (enable after readability is checked or if we have existing data)
  const { data: storedEntityMap, isLoading: isLoadingEntityMap } = useGetEntityMap(
    ddId || undefined,
    readabilityChecked || entityMappingComplete
  );

  // Update entity mapping state when stored data is loaded
  useEffect(() => {
    if (storedEntityMap?.entity_map && storedEntityMap.entity_map.length > 0) {
      setEntityMappingComplete(true);
      setEntityCount(storedEntityMap.summary?.total_unique_entities || storedEntityMap.entity_map.length);
      // Set result for viewing in modal - provide defaults for required fields
      setEntityMappingResult({
        dd_id: storedEntityMap.dd_id,
        status: storedEntityMap.status || "completed",
        total_documents_processed: storedEntityMap.total_documents_processed || 0,
        entity_map: storedEntityMap.entity_map,
        summary: storedEntityMap.summary || {
          total_unique_entities: storedEntityMap.entity_map.length,
          entities_needing_confirmation: storedEntityMap.entity_map.filter((e: any) => e.requires_human_confirmation).length,
          target_subsidiaries: storedEntityMap.entity_map.filter((e: any) => e.relationship_to_target === "subsidiary").length,
          counterparties: storedEntityMap.entity_map.filter((e: any) => e.relationship_to_target === "counterparty").length,
        },
        checkpoint_recommended: storedEntityMap.checkpoint_recommended || false,
        checkpoint_reason: storedEntityMap.checkpoint_reason,
        stored_count: storedEntityMap.entity_map.length,
      });
    }
  }, [storedEntityMap]);

  // Blueprint requirements for Checkpoint A - fetch after classification is done
  // Enable when status is past classification (not pending/classifying/cancelled/failed)
  const classificationComplete = organisationProgress?.status &&
    !["pending", "classifying", "cancelled", "failed"].includes(organisationProgress.status);
  const { data: blueprintRequirements, refetch: refetchBlueprint } = useBlueprintRequirements(
    ddData?.transaction_type,
    ddId,
    !!classificationComplete
  );

  // Auto-select the most recent completed run if none selected (for returning visitors)
  useEffect(() => {
    if (runsData?.runs && runsData.runs.length > 0 && !currentRunId) {
      // Find the most recent completed run
      const completedRuns = runsData.runs.filter((r) => r.status === "completed");
      if (completedRuns.length > 0) {
        setCurrentRunId(completedRuns[0].run_id);
      }
    }
  }, [runsData, currentRunId]);

  // Set currentRunId from progress data if not already set (fallback for when dd_analysis_runs table doesn't exist)
  useEffect(() => {
    if (progress?.runId && !currentRunId) {
      setCurrentRunId(progress.runId);
    }
  }, [progress?.runId, currentRunId]);

  // Sync isPaused state with actual progress status
  useEffect(() => {
    if (progress?.status === "paused" && !isPaused) {
      setIsPaused(true);
    } else if (progress?.status === "processing" && isPaused) {
      setIsPaused(false);
    }
  }, [progress?.status, isPaused]);

  // Refetch DD data when classification completes to sync documentsByCategory with categoryCounts
  useEffect(() => {
    if (organisationProgress?.status === "classified" && organisationProgress?.categoryCounts) {
      // Small delay to ensure database is updated
      const timer = setTimeout(() => {
        refetchDD();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [organisationProgress?.status, organisationProgress?.categoryCounts, refetchDD]);

  // Helper to add log entry
  const addLogEntry = useCallback(
    (type: LogEntry["type"], message: string, details?: string) => {
      setLogEntries((prev) => [...prev, createLogEntry(type, message, details)]);
    },
    []
  );

  // Transform documents to include readability status
  const documents: DocumentItem[] = useMemo(() => {
    if (propDocuments.length > 0) {
      return propDocuments;
    }
    // Get from progress if available
    return (progress?.documents ?? []).map((doc: any) => {
      const processingStatus = doc.status || doc.processing_status;
      // If document was already processed successfully, treat as "ready" for selection
      // This handles documents processed before readability checking was added
      const inferredReadabilityStatus =
        doc.readability_status ||
        (processingStatus === "completed" ? "ready" : "pending");

      return {
        document_id: doc.id || doc.document_id,
        original_file_name: doc.filename || doc.original_file_name || doc.name || "Unknown",
        type: doc.type || doc.doc_type || "unknown",
        readability_status: inferredReadabilityStatus,
        readability_error: doc.readability_error,
        processing_status: processingStatus,
      };
    });
  }, [propDocuments, progress?.documents]);

  // Determine current phase
  const currentPhase: DashboardPhase = useMemo(() => {
    if (progress?.status === "completed") return "completed";
    if (progress?.status === "failed") return "failed";
    if (progress?.status === "processing") return "processing";

    // Check organisation/classification status first (Phase 1 & 2)
    const orgStatus = organisationProgress?.status;

    // Phase 1: Classification
    if (orgStatus === "classifying") return "classifying";
    if (orgStatus === "classified") return "classified"; // Show OrganisationReview
    if (orgStatus === "cancelled") return "cancelled"; // User cancelled - show restart option

    // Phase 2: Folder organisation
    if (orgStatus === "organising") return "organising";
    if (orgStatus === "organised") return "organised"; // Ready for readability

    // If classification hasn't started yet and we have documents
    if (orgStatus === "pending" && documents.length > 0) return "classifying";

    // Check if all documents have passed readability
    const allReady = documents.every(
      (d) => d.readability_status === "ready" || d.readability_status === "failed"
    );
    const anyChecking = documents.some((d) => d.readability_status === "checking");

    if (anyChecking) return "readability";
    if (allReady && readabilityChecked) return "ready";

    return "readability";
  }, [progress?.status, documents, readabilityChecked, organisationProgress?.status]);

  // Summary counts
  const readabilitySummary = useMemo(() => {
    return documents.reduce(
      (acc, doc) => {
        const status = doc.readability_status || "pending";
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      },
      { pending: 0, checking: 0, ready: 0, failed: 0 } as Record<string, number>
    );
  }, [documents]);

  // Risk summary from progress
  // Note: progress is already sanitized to be undefined during new run transitions
  const riskSummary: RiskSummary = useMemo(
    () => {
      // Calculate completion percentage from documents processed
      const totalDocs = progress?.totalDocuments ?? 0;
      const processedDocs = progress?.documentsProcessed ?? 0;
      const completionPercent = totalDocs > 0 ? Math.round((processedDocs / totalDocs) * 100) : 0;

      return {
        total: progress?.findingCounts?.total ?? 0,
        critical: progress?.findingCounts?.critical ?? 0,
        high: progress?.findingCounts?.high ?? 0,
        medium: progress?.findingCounts?.medium ?? 0,
        low: progress?.findingCounts?.low ?? 0,
        positive: progress?.findingCounts?.positive ?? 0,
        dealBlockers: progress?.findingCounts?.dealBlockers ?? 0,
        conditionsPrecedent: progress?.findingCounts?.conditionsPrecedent ?? 0,
        warranties: progress?.findingCounts?.warranties ?? 0,
        indemnities: progress?.findingCounts?.indemnities ?? 0,
        completionPercent,
        totalExposure: 0,
        currency: "ZAR",
      };
    },
    [progress]
  );

  // Documents grouped by category for classification review
  // NOTE: This must come BEFORE categoryDistribution to be used for accurate counts
  const documentsByCategory: Record<string, CategoryDocument[]> = useMemo(() => {
    const result: Record<string, CategoryDocument[]> = {};

    // Build a map of document readability status from the documents array (for real-time updates during checking)
    const readabilityMap = new Map<string, string>();
    documents.forEach((doc) => {
      readabilityMap.set(doc.document_id, doc.readability_status || "pending");
    });

    // Get all documents from ddData.folders
    // Use readability_status from ddData (persisted) or readabilityMap (real-time) - prefer real-time if available
    // Filter out converted documents - only show original uploaded files during classification/organization
    const allDocs = ddData?.folders?.flatMap((folder: any) =>
      folder.documents
        ?.filter((doc: any) => !doc.converted_from_id) // Exclude converted docs
        ?.map((doc: any) => ({
          id: doc.document_id,
          name: doc.original_file_name,
          type: doc.type,
          confidence: doc.ai_confidence,
          subcategory: doc.ai_subcategory,
          category: doc.ai_category || "99_Needs_Review",
          readabilityStatus: readabilityMap.get(doc.document_id) || doc.readability_status || "pending",
          conversionStatus: doc.conversion_status,
        })) || []
    ) || [];

    // Group by ai_category
    for (const doc of allDocs) {
      const cat = doc.category;
      if (!result[cat]) {
        result[cat] = [];
      }
      result[cat].push({
        id: doc.id,
        name: doc.name,
        type: doc.type,
        confidence: doc.confidence,
        subcategory: doc.subcategory,
        readabilityStatus: doc.readabilityStatus as "pending" | "checking" | "ready" | "failed",
        conversionStatus: doc.conversionStatus,
      });
    }

    return result;
  }, [ddData?.folders, documents]);

  // Category distribution for OrganisationReview
  // Uses counts from filtered documentsByCategory to exclude converted docs
  const categoryDistribution: CategoryCount[] = useMemo(() => {
    const backendCounts = organisationProgress?.categoryCounts || {};
    const relevanceMap: Record<string, "critical" | "high" | "medium" | "low" | "n/a"> = {
      "01_Corporate": "high",
      "01_Corporate_Governance": "high",
      "02_Commercial": "critical",
      "03_Financial": "critical",
      "04_Regulatory": "critical",
      "05_Employment": "high",
      "06_Property": "medium",
      "07_Insurance": "low",
      "08_Litigation": "high",
      "09_Tax": "medium",
      "99_Needs_Review": "n/a",
    };

    // Display name overrides for better readability
    const displayNameMap: Record<string, string> = {
      "01_Corporate": "Corporate Governance",
      "01_Corporate_Governance": "Corporate Governance",
    };

    // Helper to get display name
    const getDisplayName = (category: string): string => {
      if (displayNameMap[category]) return displayNameMap[category];
      return category.replace(/^\d+_/, "").replace(/_/g, " ");
    };

    // Start with backend categories, excluding deleted ones
    // Use actual document counts from documentsByCategory (excludes converted docs)
    const categories = Object.keys(backendCounts)
      .filter((category) => !deletedCategories.has(category))
      .map((category) => ({
        category,
        displayName: getDisplayName(category),
        // Use filtered count from documentsByCategory instead of raw backend count
        count: documentsByCategory[category]?.length || 0,
        relevance: relevanceMap[category] || "medium",
      }));

    // Add custom categories (empty, for user to move docs into)
    for (const customCat of customCategories) {
      if (!categories.find(c => c.category === customCat)) {
        categories.push({
          category: customCat,
          displayName: getDisplayName(customCat),
          count: documentsByCategory[customCat]?.length || 0,
          relevance: "medium",
        });
      }
    }

    return categories.sort((a, b) => a.category.localeCompare(b.category));
  }, [organisationProgress?.categoryCounts, customCategories, deletedCategories, documentsByCategory]);

  // Handle approve organisation - triggers folder creation
  const handleApproveOrganisation = useCallback(() => {
    if (!ddId) return;

    addLogEntry("info", "Creating organised folder structure...");

    organiseFolders.mutate(
      { ddId, transactionType: ddData?.briefing?.transaction_type },
      {
        onSuccess: (data: any) => {
          addLogEntry(
            "success",
            `Folder organisation complete`,
            `${data.summary?.moved_count || 0} documents organised into ${data.folders_created?.length || 0} folders`
          );
          if (data.summary?.needs_review_count > 0) {
            addLogEntry(
              "warning",
              `${data.summary.needs_review_count} document(s) need manual review`
            );
          }
          refetchOrganisation();
        },
        onError: (error: any) => {
          addLogEntry("error", "Folder organisation failed", error?.message || "Please try again");
        },
      }
    );
  }, [ddId, ddData, organiseFolders, addLogEntry, refetchOrganisation]);

  // Handle re-organise - re-runs classification
  const handleReorganise = useCallback(() => {
    if (!ddId) return;
    hasInitiatedClassification.current = false;
    addLogEntry("info", "Re-classifying documents...");
    // This will trigger the classification effect
    refetchOrganisation();
  }, [ddId, addLogEntry, refetchOrganisation]);

  // Handle moving a document to a different category
  const handleMoveDocument = useCallback(
    (docId: string, fromCategory: string, toCategory: string) => {
      if (!ddId) return;

      const fromName = fromCategory.replace(/^\d+_/, "").replace(/_/g, " ");
      const toName = toCategory.replace(/^\d+_/, "").replace(/_/g, " ");

      addLogEntry("info", `Moving document to ${toName}...`);

      documentReassign.mutate(
        {
          ddId,
          documentId: docId,
          targetCategory: toCategory,
          reason: `Manual reassignment from ${fromName} to ${toName}`,
        },
        {
          onSuccess: () => {
            addLogEntry("success", `Document moved to ${toName}`);
            refetchOrganisation();
            refetchDD(); // Refresh DD data to show document in new folder
          },
          onError: (error: any) => {
            addLogEntry("error", `Failed to move document: ${error?.message || "Unknown error"}`);
          },
        }
      );
    },
    [ddId, documentReassign, addLogEntry, refetchOrganisation, refetchDD]
  );

  // Handler to add a new custom category
  const handleAddCategory = useCallback((categoryName: string) => {
    // Convert to category format (e.g., "Regulatory Approvals" -> "10_Regulatory_Approvals")
    const nextNumber = 10 + customCategories.length;
    const formattedCategory = `${nextNumber.toString().padStart(2, "0")}_${categoryName.replace(/\s+/g, "_")}`;

    setCustomCategories(prev => [...prev, formattedCategory]);
    addLogEntry("info", `Added folder: ${categoryName}`);
  }, [customCategories, addLogEntry]);

  // Handler to delete a category
  const handleDeleteCategory = useCallback((category: string) => {
    // If it's a custom category, remove it from customCategories
    if (customCategories.includes(category)) {
      setCustomCategories(prev => prev.filter(c => c !== category));
    } else {
      // Otherwise, mark it as deleted
      setDeletedCategories(prev => new Set(prev).add(category));
    }

    // Move any documents in this category to "Needs Review"
    const docsInCategory = documentsByCategory[category] || [];
    if (docsInCategory.length > 0) {
      docsInCategory.forEach(doc => {
        documentReassign.mutate({
          ddId,
          documentId: doc.id,
          targetCategory: "99_Needs_Review",
          reason: `Folder "${category}" was deleted`,
        });
      });
      addLogEntry("warning", `Moved ${docsInCategory.length} document(s) to Needs Review`);
    }

    const displayName = category.replace(/^\d+_/, "").replace(/_/g, " ");
    addLogEntry("info", `Deleted folder: ${displayName}`);
  }, [customCategories, documentsByCategory, documentReassign, ddId, addLogEntry]);

  // Function to run readability check
  // Helper to get attorney-friendly readability error message
  const getReadabilityErrorMessage = (filename: string, error?: string): string => {
    const errorLower = error?.toLowerCase() || "";

    if (errorLower.includes("password") || errorLower.includes("encrypted")) {
      return "This document is password-protected. Please upload an unprotected version.";
    }
    if (errorLower.includes("corrupt") || errorLower.includes("damaged")) {
      return "This document appears to be corrupted. Please upload a fresh copy.";
    }
    if (errorLower.includes("empty") || errorLower.includes("no text")) {
      return "This document contains no readable text. It may be a scanned image - please upload a text-based version.";
    }
    if (errorLower.includes("format") || errorLower.includes("unsupported")) {
      return "This file format is not supported. Please convert to PDF or DOCX.";
    }
    if (errorLower.includes("too large") || errorLower.includes("size")) {
      return "This document is too large. Please split it into smaller files or contact support.";
    }

    return "This document cannot be processed. Try re-uploading or converting to a different format.";
  };

  const runReadabilityCheck = useCallback((docIds?: string[]) => {
    if (!ddId) return;

    // Use documentsByCategory if documents array is empty (classification phase)
    const categoryDocsCount = Object.values(documentsByCategory).flat().length;
    const totalDocs = documents.length > 0 ? documents.length : categoryDocsCount;
    const checkingCount = docIds?.length || totalDocs;
    addLogEntry("info", `Checking readability for ${checkingCount} document(s)...`);

    checkReadability.mutate(
      { dd_id: ddId, doc_ids: docIds },
      {
        onSuccess: (data) => {
          setReadabilityChecked(true);
          data.results.forEach((result) => {
            if (result.status === "ready") {
              addLogEntry("success", `${result.filename} ready for analysis`);
            } else if (result.status === "failed") {
              const friendlyError = getReadabilityErrorMessage(result.filename, result.error);
              addLogEntry(
                "error",
                `${result.filename} cannot be read`,
                friendlyError
              );
            }
          });
          if (data.summary.failed > 0) {
            addLogEntry(
              "warning",
              `${data.summary.failed} document(s) need attention`,
              "These documents will be excluded from analysis. You can proceed with the remaining documents or fix the issues and re-check."
            );
          } else {
            addLogEntry("success", "All documents ready for analysis");
          }
          // Auto-select all ready documents (merge with existing selection)
          const readyIds = new Set(
            data.results
              .filter((r) => r.status === "ready")
              .map((r) => r.doc_id)
          );
          setSelectedDocIds((prev) => {
            const newSet = new Set(prev);
            // Remove failed docs from selection, add ready ones
            data.results.forEach((r) => {
              if (r.status === "ready") {
                newSet.add(r.doc_id);
              } else {
                newSet.delete(r.doc_id);
              }
            });
            return newSet;
          });
          // Refetch progress to update document list
          refetch();
        },
        onError: (error: any) => {
          const errorMsg = error?.message?.toLowerCase() || "";
          let friendlyMessage = "Unable to check documents";
          let friendlyDetails = "Please try again. If the problem continues, contact support.";

          if (errorMsg.includes("network") || errorMsg.includes("timeout")) {
            friendlyMessage = "Connection problem";
            friendlyDetails = "Unable to reach the server. Please check your internet connection and try again.";
          } else if (errorMsg.includes("401") || errorMsg.includes("unauthorized")) {
            friendlyMessage = "Session expired";
            friendlyDetails = "Your login session has expired. Please refresh the page and sign in again.";
          }

          addLogEntry("error", friendlyMessage, friendlyDetails);
          setReadabilityChecked(true);
        },
      }
    );
  }, [ddId, documents.length, documentsByCategory, checkReadability, addLogEntry, refetch]);

  // Track if we've initiated classification to prevent duplicate calls
  const hasInitiatedClassification = React.useRef(false);

  // Trigger document classification when organisation status is pending
  useEffect(() => {
    if (
      ddId &&
      documents.length > 0 &&
      organisationProgress?.status === "pending" &&
      !hasInitiatedClassification.current &&
      !classifyDocuments.isPending
    ) {
      hasInitiatedClassification.current = true;
      addLogEntry("info", "Starting AI document classification...", `Classifying ${documents.length} documents`);

      classifyDocuments.mutate({ ddId }, {
        onSuccess: (data: any) => {
          addLogEntry(
            "success",
            `Classification complete: ${data.classified_count || 0} documents classified`,
            data.low_confidence_count > 0
              ? `${data.low_confidence_count} documents need manual review`
              : undefined
          );
          refetchOrganisation();
          refetchDD(); // Refresh DD data to get updated ai_category on documents
        },
        onError: (error: any) => {
          addLogEntry("error", "Classification failed", error?.message || "Please try again");
          hasInitiatedClassification.current = false; // Allow retry
        },
      });
    }
  }, [ddId, documents.length, organisationProgress?.status, classifyDocuments, addLogEntry, refetchOrganisation, refetchDD]);

  // Reset classification flag when ddId changes
  useEffect(() => {
    hasInitiatedClassification.current = false;
  }, [ddId]);

  // Run readability check on mount or set readabilityChecked if docs already ready
  // Uses a ref to track if we've already initiated a check to prevent loops
  const hasInitiatedReadabilityCheck = React.useRef(false);

  // Reset the ref when ddId changes (user navigates to different project)
  useEffect(() => {
    hasInitiatedReadabilityCheck.current = false;
  }, [ddId]);

  useEffect(() => {
    // Guard: Don't re-run if we've already initiated a check or one is in progress
    if (hasInitiatedReadabilityCheck.current || checkReadability.isPending) {
      return;
    }

    if (ddId && documents.length > 0 && !readabilityChecked) {
      // If we're in readability phase, check pending docs
      if (currentPhase === "readability") {
        const pendingDocs = documents.filter((d) => d.readability_status === "pending");
        if (pendingDocs.length > 0) {
          hasInitiatedReadabilityCheck.current = true;
          runReadabilityCheck();
        } else {
          setReadabilityChecked(true);
        }
      }
      // If we're on a completed/failed run or ready phase, docs were already checked
      else if (currentPhase === "completed" || currentPhase === "failed" || currentPhase === "ready") {
        // Docs have been checked in a previous run, mark as ready to allow new runs
        setReadabilityChecked(true);
      }
    }
  }, [ddId, documents.length, readabilityChecked, currentPhase, checkReadability.isPending]);
  // Note: Changed documents to documents.length to prevent re-triggering on every render
  // Removed runReadabilityCheck from deps since it's stable via useCallback

  // Auto-select ready documents when returning to a completed run with no selection
  // Only runs on initial load - not after user has manually changed selection
  useEffect(() => {
    if (ddId && documents.length > 0 && selectedDocIds.size === 0 && readabilityChecked && !userHasModifiedSelection) {
      const readyDocIds = documents
        .filter((d) => d.readability_status === "ready")
        .map((d) => d.document_id);
      if (readyDocIds.length > 0) {
        setSelectedDocIds(new Set(readyDocIds));
      }
    }
  }, [ddId, documents, readabilityChecked, userHasModifiedSelection]);
  // Note: removed selectedDocIds.size from deps to prevent re-triggering on deselect

  // Wrapper for selection changes that tracks user interaction
  const handleSelectionChange = useCallback((newSelection: Set<string>) => {
    setUserHasModifiedSelection(true);
    setSelectedDocIds(newSelection);
  }, []);

  // Handle Run DD button click
  // Note: checkForMatchingCompletedRun is defined inline to access allCategoryDocs which is defined later
  const handleRunDDClick = () => {
    // Check if current selection exactly matches a previously completed run
    const checkForMatchingCompletedRun = () => {
      if (!runsData?.runs) return null;

      // Get the docs that would be processed (same logic as handleStartDD)
      const docsToProcess = selectedDocIds.size > 0
        ? Array.from(selectedDocIds)
        : allCategoryDocs.filter((doc: any) => doc.readabilityStatus === "ready").map((doc: any) => doc.id);

      const docsToProcessSet = new Set(docsToProcess);

      // Find completed runs with the exact same document set
      for (const run of runsData.runs) {
        if (run.status !== "completed") continue;

        const runDocIds = run.selected_documents.map((d) => d.id);
        const runDocSet = new Set(runDocIds);

        // Check if sets are exactly equal
        if (runDocSet.size === docsToProcessSet.size &&
            Array.from(docsToProcessSet).every((id) => runDocSet.has(id))) {
          return {
            name: run.name,
            completedAt: run.completed_at || run.created_at || "",
          };
        }
      }

      return null;
    };

    // First check if this would be a re-run of the exact same documents
    const matchingRun = checkForMatchingCompletedRun();
    if (matchingRun) {
      setMatchingCompletedRun(matchingRun);
      setShowRerunWarningDialog(true);
      return;
    }

    // Then check for failed readability
    if (readabilitySummary.failed > 0) {
      setShowWarningDialog(true);
    } else {
      setShowConfirmDialog(true);
    }
  };

  // Helper to convert technical errors to attorney-friendly messages
  const getAttorneyFriendlyError = (error: any): { message: string; details: string; isFixable: boolean } => {
    const errorMsg = error?.message?.toLowerCase() || "";
    const statusCode = error?.response?.status || (errorMsg.match(/\b(4\d{2}|5\d{2})\b/)?.[0]);

    // Document/Project issues (attorney can fix)
    if (errorMsg.includes("no documents selected") || errorMsg.includes("selected_document_ids")) {
      return {
        message: "No documents selected for analysis",
        details: "Please select at least one document from the checklist before running Due Diligence.",
        isFixable: true
      };
    }
    if (errorMsg.includes("readability") || errorMsg.includes("cannot be read")) {
      return {
        message: "Some documents cannot be read",
        details: "One or more selected documents failed the readability check. Remove failed documents or upload readable versions.",
        isFixable: true
      };
    }
    if (errorMsg.includes("not found") && errorMsg.includes("dd")) {
      return {
        message: "Project not found",
        details: "This Due Diligence project may have been deleted. Please return to the project list and select a valid project.",
        isFixable: true
      };
    }
    if (errorMsg.includes("already processing") || statusCode === "409") {
      return {
        message: "Analysis already in progress",
        details: "A Due Diligence analysis is currently running. Please wait for it to complete or cancel it before starting a new run.",
        isFixable: true
      };
    }
    if (errorMsg.includes("already completed")) {
      return {
        message: "This run has already completed",
        details: "This analysis run has finished. To analyse documents again, start a new run from the Dashboard.",
        isFixable: true
      };
    }

    // Authentication issues
    if (statusCode === "401" || errorMsg.includes("unauthorized") || errorMsg.includes("authentication")) {
      return {
        message: "Session expired",
        details: "Your login session has expired. Please refresh the page and sign in again.",
        isFixable: true
      };
    }
    if (statusCode === "403" || errorMsg.includes("forbidden") || errorMsg.includes("permission")) {
      return {
        message: "Access denied",
        details: "You don't have permission to run this analysis. Contact your administrator if you believe this is an error.",
        isFixable: false
      };
    }

    // Server/System issues (developer needs to fix)
    if (statusCode === "500" || errorMsg.includes("internal") || errorMsg.includes("server error")) {
      return {
        message: "System error occurred",
        details: "An unexpected error occurred on our servers. Please try again in a few minutes. If the problem persists, contact support.",
        isFixable: false
      };
    }
    if (errorMsg.includes("network") || errorMsg.includes("timeout") || errorMsg.includes("failed to fetch")) {
      return {
        message: "Connection problem",
        details: "Unable to reach the server. Please check your internet connection and try again.",
        isFixable: true
      };
    }

    // Default fallback
    return {
      message: "Unable to start analysis",
      details: "An unexpected error occurred. Please try again or contact support if the problem continues.",
      isFixable: false
    };
  };

  // Start DD processing
  const handleStartDD = async () => {
    setShowConfirmDialog(false);
    setShowWarningDialog(false);
    setShowRerunWarningDialog(false);
    setMatchingCompletedRun(null);

    // If no docs selected, use all readable docs
    const docsToProcess = selectedDocIds.size > 0
      ? Array.from(selectedDocIds)
      : allCategoryDocs.filter((doc) => doc.readabilityStatus === "ready").map((doc) => doc.id);

    addLogEntry("info", `Creating analysis run for ${docsToProcess.length} documents...`);

    try {
      // Step 1: Create a new run with selected documents
      const runResult = await createRun.mutateAsync({
        ddId,
        selectedDocumentIds: docsToProcess,
      });

      addLogEntry("info", `Run "${runResult.name}" created, starting analysis...`);
      setCurrentRunId(runResult.run_id);

      // Step 2: Start processing for this run with selected model tier
      const result = await startProcessing(runResult.run_id, { modelTier: selectedModelTier });
      const tierLabel = selectedModelTier === "cost_optimized" ? "Economy" :
                       selectedModelTier === "balanced" ? "Balanced" :
                       selectedModelTier === "high_accuracy" ? "High Accuracy" : "Maximum";
      addLogEntry("success", "Due Diligence processing initiated", `Processing ${result.totalDocuments} documents with ${tierLabel} accuracy`);

      // Trigger a refetch to start showing progress
      refetch();
    } catch (error: any) {
      const friendlyError = getAttorneyFriendlyError(error);
      const actionHint = friendlyError.isFixable
        ? "You can resolve this issue."
        : "Please contact support for assistance.";
      addLogEntry("error", friendlyError.message, `${friendlyError.details} ${actionHint}`);
    }
  };

  // Pause/Resume processing
  const handlePauseResume = async () => {
    if (!currentRunId) {
      addLogEntry("warning", "No active run to pause/resume");
      return;
    }

    const action = isPaused ? "resume" : "pause";
    const actionLabel = isPaused ? "Resuming" : "Pausing";

    addLogEntry("info", `${actionLabel} Due Diligence analysis...`);

    try {
      const response = await fetch(
        `/api/dd-process-pause?run_id=${currentRunId}&action=${action}`,
        { method: "POST" }
      );

      if (response.ok) {
        setIsPaused(!isPaused);
        if (isPaused) {
          addLogEntry("success", "Analysis resumed", "Processing will continue from where it left off.");
        } else {
          addLogEntry("info", "Analysis paused", "You can resume at any time. Progress has been saved.");
        }
        refetch();
      } else {
        const data = await response.json();
        const status = response.status;

        if (status === 404) {
          addLogEntry("warning", "No active analysis to pause", "The analysis may have already completed.");
        } else if (status === 409) {
          addLogEntry("warning", `Cannot ${action} at this time`, data.error || "Please try again in a moment.");
        } else {
          addLogEntry("error", `Unable to ${action} analysis`, "Please try again. If the problem persists, contact support.");
        }
      }
    } catch (error) {
      addLogEntry("error", "Connection problem", "Unable to reach the server. Please check your internet connection and try again.");
    }
  };

  // Cancel processing
  const handleCancel = async () => {
    if (isCancelling) return;

    setIsCancelling(true);
    addLogEntry("warning", "Cancelling Due Diligence analysis...", "This may take a moment to complete.");

    try {
      // Use run_id if available, otherwise fall back to dd_id
      const queryParam = currentRunId ? `run_id=${currentRunId}` : `dd_id=${ddId}`;
      const response = await fetch(`/api/dd-process-cancel?${queryParam}`, {
        method: "POST",
      });

      if (response.ok) {
        addLogEntry("info", "Analysis cancelled successfully", "Any findings generated before cancellation have been saved. You can start a new analysis run at any time.");
        refetch(); // Refresh progress to show cancelled state
      } else {
        const status = response.status;
        if (status === 404) {
          addLogEntry("warning", "No active analysis to cancel", "The analysis may have already completed or was not running.");
        } else if (status === 409) {
          addLogEntry("warning", "Cannot cancel at this time", "The analysis is in a state that cannot be interrupted. Please wait for it to complete.");
        } else {
          addLogEntry("error", "Unable to cancel analysis", "Please try again. If the problem persists, the analysis will stop automatically when complete.");
        }
      }
    } catch (error) {
      addLogEntry("error", "Connection problem", "Unable to reach the server to cancel. Please check your internet connection and try again.");
    } finally {
      setIsCancelling(false);
    }
  };

  // Restart interrupted processing
  const handleRestart = async () => {
    if (!currentRunId || isRestarting) return;

    setIsRestarting(true);
    addLogEntry("info", "Restarting interrupted analysis...", "Continuing from the last saved checkpoint.");

    try {
      const response = await fetch(`/api/dd-process-restart?run_id=${currentRunId}`, {
        method: "POST",
      });

      const data = await response.json();

      if (response.ok) {
        addLogEntry(
          "success",
          "Analysis restarted successfully",
          `Resuming from pass ${data.progress?.current_pass || 1}. ${data.progress?.documents_processed || 0} of ${data.progress?.total_documents || 0} documents already processed.`
        );
        refetch();
      } else {
        const status = response.status;
        if (status === 409) {
          // Already running or completed
          addLogEntry("info", data.message || "No restart needed", data.error);
        } else if (status === 404) {
          addLogEntry("warning", "Cannot restart", data.message || "No checkpoint found. Please start a new run.");
        } else {
          addLogEntry("error", "Unable to restart analysis", data.error || "Please try again or start a new run.");
        }
      }
    } catch (error) {
      addLogEntry("error", "Connection problem", "Unable to reach the server. Please check your internet connection and try again.");
    } finally {
      setIsRestarting(false);
    }
  };

  // Check if the run appears to be stuck (processing but no updates for > 2 minutes)
  const isRunStuck = useMemo(() => {
    if (!progress || progress.status !== "processing") return false;
    if (!progress.lastUpdated) return false;

    const lastUpdate = new Date(progress.lastUpdated).getTime();
    const now = Date.now();
    const twoMinutes = 2 * 60 * 1000;

    return now - lastUpdate > twoMinutes;
  }, [progress]);

  // Check if run failed unexpectedly (not user-cancelled)
  const isUnexpectedFailure = useMemo(() => {
    if (!progress || progress.status !== "failed") return false;
    const lastError = progress.lastError?.toLowerCase() || "";
    return !lastError.includes("cancelled");
  }, [progress]);

  // Log phase changes to Process Log
  const previousPhaseRef = React.useRef<DashboardPhase | null>(null);
  useEffect(() => {
    // Skip initial render and only log on actual phase changes
    if (previousPhaseRef.current === null) {
      previousPhaseRef.current = currentPhase;
      return;
    }
    if (previousPhaseRef.current === currentPhase) return;

    previousPhaseRef.current = currentPhase;

    switch (currentPhase) {
      case "classifying":
        addLogEntry("progress", "Classifying documents with AI...");
        break;
      case "classified":
        addLogEntry("success", "Classification complete", "Review the folder assignments and approve to continue");
        break;
      case "organising":
        addLogEntry("progress", "Creating organised folder structure...");
        break;
      case "organised":
        addLogEntry("success", "Folders organised", "Proceeding to readability check");
        break;
      case "readability":
        addLogEntry("progress", "Checking document readability...");
        break;
      case "ready":
        addLogEntry("success", `${selectedDocIds.size} document(s) ready for analysis`);
        break;
      case "processing":
        addLogEntry("progress", "Due Diligence analysis in progress...");
        break;
      case "completed":
        addLogEntry("success", "Analysis complete", "View results in the Analysis tab");
        break;
      case "failed":
        if (isUnexpectedFailure) {
          addLogEntry("warning", "Analysis was interrupted", "Click 'Restart from Checkpoint' to continue");
        } else {
          addLogEntry("info", "Analysis was cancelled");
        }
        break;
      case "cancelled":
        addLogEntry("warning", "Classification cancelled", "Restart classification or proceed without folder organisation");
        break;
    }
  }, [currentPhase, selectedDocIds.size, isUnexpectedFailure, addLogEntry]);

  // Log when processing appears stuck
  useEffect(() => {
    if (isRunStuck) {
      addLogEntry("warning", "Processing appears stuck", "You can restart from checkpoint if needed");
    }
  }, [isRunStuck, addLogEntry]);

  // Track previous progress values for granular logging
  const prevProgressRef = useRef<{
    currentPass?: string;
    currentDocumentName?: string;
    passProgress?: Record<string, { itemsProcessed: number }>;
  }>({});

  // Add granular progress log entries
  useEffect(() => {
    if (!progress || progress.status !== "processing") return;

    const prev = prevProgressRef.current;
    const passLabels: Record<string, string> = {
      extract: "Pass 1: Extraction",
      analyze: "Pass 2: Analysis",
      calculate: "Pass 2.5: Calculations",
      crossdoc: "Pass 3: Cross-Document Analysis",
      aggregate: "Pass 3.5: Aggregation",
      synthesize: "Pass 4: Synthesis",
      verify: "Pass 5: Verification",
    };

    // Log pass changes
    if (progress.currentPass && progress.currentPass !== prev.currentPass) {
      const passLabel = passLabels[progress.currentPass] || progress.currentPass;
      addLogEntry("progress", `Starting ${passLabel}`, `Processing documents through ${progress.currentPass} phase`);
    }

    // Log current document changes (when a new document starts processing)
    if (progress.currentDocumentName && progress.currentDocumentName !== prev.currentDocumentName) {
      const passLabel = passLabels[progress.currentPass || ""] || progress.currentPass || "analysis";
      addLogEntry("document", `Processing: ${progress.currentDocumentName}`, `Running ${passLabel}`);
    }

    // Log document completions within passes
    if (progress.passProgress && prev.passProgress) {
      // Track all passes that process multiple items
      const passLabelMap: Record<string, string> = {
        extract: "extraction",
        analyze: "analysis",
        calculate: "calculations",
        crossdoc: "cross-document analysis",
        aggregate: "aggregation",
        synthesize: "synthesis",
        verify: "verification"
      };

      for (const [pass, label] of Object.entries(passLabelMap)) {
        const currentItems = progress.passProgress[pass as keyof typeof progress.passProgress]?.itemsProcessed || 0;
        const prevItems = prev.passProgress[pass]?.itemsProcessed || 0;
        const totalItems = progress.passProgress[pass as keyof typeof progress.passProgress]?.totalItems || 0;

        if (currentItems > prevItems && currentItems > 0) {
          // Progress was made in this pass
          if (pass === "extract" || pass === "analyze" || pass === "calculate") {
            // Document-level passes
            addLogEntry("success", `Document ${label} complete`, `${currentItems} of ${totalItems} documents processed`);
          } else if (currentItems === totalItems) {
            // Single-item passes (crossdoc, aggregate, synthesize, verify) - log when complete
            addLogEntry("success", `${label.charAt(0).toUpperCase() + label.slice(1)} complete`);
          }
        }
      }
    }

    // Update previous values
    prevProgressRef.current = {
      currentPass: progress.currentPass,
      currentDocumentName: progress.currentDocumentName,
      passProgress: progress.passProgress ? {
        extract: { itemsProcessed: progress.passProgress.extract?.itemsProcessed || 0 },
        analyze: { itemsProcessed: progress.passProgress.analyze?.itemsProcessed || 0 },
        calculate: { itemsProcessed: progress.passProgress.calculate?.itemsProcessed || 0 },
        crossdoc: { itemsProcessed: progress.passProgress.crossdoc?.itemsProcessed || 0 },
        aggregate: { itemsProcessed: progress.passProgress.aggregate?.itemsProcessed || 0 },
        synthesize: { itemsProcessed: progress.passProgress.synthesize?.itemsProcessed || 0 },
        verify: { itemsProcessed: progress.passProgress.verify?.itemsProcessed || 0 },
      } : undefined,
    };
  }, [progress?.currentPass, progress?.currentDocumentName, progress?.passProgress, progress?.status, addLogEntry]);

  // Navigation handlers - use callbacks if provided, otherwise use router
  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      navigate(`/dd?id=${ddId}`);
    }
  };
  const handleViewResults = () => {
    if (onViewResults) {
      onViewResults();
    } else {
      navigate(`/dd?id=${ddId}`);
    }
  };

  // Render loading state
  if (!ddId) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-gray-500">No DD project selected</p>
      </div>
    );
  }

  // Button state logic
  const isReadabilityInProgress = checkReadability.isPending;
  const isClassificationInProgress = classifyDocuments.isPending || organisationProgress?.status === "classifying";
  const isOrganisationInProgress = organiseFolders.isPending || organisationProgress?.status === "organising";
  const isCreatingRun = createRun.isPending;
  const isProcessingInProgress = isStarting || isCreatingRun || currentPhase === "processing";
  // Organisation is complete when status is "organised" or "completed" (or undefined for backwards compatibility)
  const isOrganisationComplete =
    organisationProgress?.status === "organised" ||
    organisationProgress?.status === "completed" ||
    organisationProgress?.status === undefined;

  // Count documents in 99_Needs_Review folder - blocks readability check until resolved
  const needsReviewCount = useMemo(() => {
    // First try from blueprint requirements (more accurate)
    if (blueprintRequirements?.requirements?.["99_Needs_Review"]?.document_count) {
      return blueprintRequirements.requirements["99_Needs_Review"].document_count;
    }
    // Fall back to documentsByCategory
    return documentsByCategory["99_Needs_Review"]?.length || 0;
  }, [blueprintRequirements, documentsByCategory]);

  // Readability check is blocked until 99_Needs_Review is empty
  const canRunReadabilityCheck = needsReviewCount === 0 && !isClassificationInProgress;

  // Get all documents from documentsByCategory for readability check
  const allCategoryDocs = useMemo(() => {
    return Object.values(documentsByCategory).flat();
  }, [documentsByCategory]);

  // Check if selected docs (or all docs if none selected) are all readable
  const areDocsReadyForDD = useMemo(() => {
    // If docs are selected, check only selected docs
    if (selectedDocIds.size > 0) {
      const selectedDocs = allCategoryDocs.filter((doc) => selectedDocIds.has(doc.id));
      return selectedDocs.length > 0 && selectedDocs.every((doc) => doc.readabilityStatus === "ready");
    }
    // If no docs selected, check all docs
    return allCategoryDocs.length > 0 && allCategoryDocs.every((doc) => doc.readabilityStatus === "ready");
  }, [selectedDocIds, allCategoryDocs]);

  // Count of docs that will be processed (for confirmation dialog)
  const docsToProcessCount = useMemo(() => {
    if (selectedDocIds.size > 0) {
      return selectedDocIds.size;
    }
    return allCategoryDocs.filter((doc) => doc.readabilityStatus === "ready").length;
  }, [selectedDocIds, allCategoryDocs]);

  // Allow re-running after completion - the button is available when:
  // - Readability check has been completed OR previous run is completed (docs already validated)
  // - Not currently processing or organising
  // - All docs to be processed are readable (selected docs if any, or all docs)
  const hasCompletedRun = progress?.status === "completed";
  const canStartDD =
    (readabilityChecked || hasCompletedRun) &&
    !isReadabilityInProgress &&
    !isClassificationInProgress &&
    !isOrganisationInProgress &&
    !isProcessingInProgress &&
    areDocsReadyForDD;

  // Tooltip message explaining why button is disabled
  const runDDTooltip = useMemo(() => {
    if (canStartDD) {
      return selectedDocIds.size > 0
        ? `Analyse ${selectedDocIds.size} selected document(s)`
        : `Analyse all ${docsToProcessCount} document(s)`;
    }
    // All disabled states show the same message
    return "Complete Doc Readability before performing Due Diligence analysis";
  }, [canStartDD, selectedDocIds.size, docsToProcessCount]);

  return (
    <div className="min-h-[600px] bg-gray-200 dark:from-gray-900 dark:to-gray-950 p-6 space-y-6">
      {/* Transaction Summary */}
      {ddData && (
        <TransactionSummary
          briefing={ddData.briefing}
          name={ddData.name}
          transactionTypeCode={ddData.transaction_type}
          projectSetup={ddData.project_setup}
          isCollapsed={isSummaryCollapsed}
          onToggleCollapse={() => setIsSummaryCollapsed(!isSummaryCollapsed)}
        />
      )}

      {/* Unified Control Bar */}
      <ControlBar
        // Organize actions
        onClassifyDocs={() => {
          if (ddId) {
            // Show the classification progress modal
            onReclassify?.();
            addLogEntry("info", "Reclassifying all documents...");
            classifyDocuments.mutate({ ddId, reset: true }, {
              onSuccess: () => {
                addLogEntry("success", "Document classification started");
                refetchOrganisation();
              },
              onError: (err) => {
                addLogEntry("error", `Classification failed: ${err.message}`);
              }
            });
          }
        }}
        isClassifying={classifyDocuments.isPending || organisationProgress?.status === "classifying"}
        onAddFolder={() => {
          // Trigger add folder dialog in FileTree - we'll handle this via state
          const event = new CustomEvent('dd-add-folder');
          window.dispatchEvent(event);
        }}
        // Validate actions
        onRunReadability={() => {
          const selectedArray = Array.from(selectedDocIds);
          runReadabilityCheck(selectedArray.length > 0 ? selectedArray : undefined);
        }}
        isCheckingReadability={checkReadability.isPending}
        readabilityComplete={readabilityChecked}
        readyCount={readabilitySummary.ready}
        failedCount={readabilitySummary.failed}
        // Checkpoint A blocking condition
        canRunReadability={canRunReadabilityCheck}
        needsReviewCount={needsReviewCount}
        // Entity Mapping
        onRunEntityMapping={() => {
          if (ddId) {
            // Show the modal immediately
            setShowEntityMappingModal(true);
            setEntityMappingResult(null);
            addLogEntry("info", "Running entity mapping...");
            entityMapping.mutate({ ddId }, {
              onSuccess: (data) => {
                setEntityMappingComplete(true);
                setEntityCount(data.summary?.total_unique_entities || 0);
                setEntityMappingResult(data as EntityMappingResult);
                addLogEntry("success", `Entity mapping complete: ${data.summary?.total_unique_entities || 0} entities found`);
                if (data.checkpoint_recommended) {
                  addLogEntry("warning", `Entity checkpoint recommended: ${data.checkpoint_reason}`);
                }
              },
              onError: (err) => {
                addLogEntry("error", `Entity mapping failed: ${err.message}`);
                setShowEntityMappingModal(false);
              }
            });
          }
        }}
        isRunningEntityMapping={entityMapping.isPending}
        entityMappingComplete={entityMappingComplete}
        canRunEntityMapping={(readabilityChecked || areDocsReadyForDD) && readabilitySummary.failed === 0}
        entityCount={entityCount}
        // View Entity Map
        onViewEntityMap={() => setShowEntityMappingModal(true)}
        hasEntityMap={entityMappingComplete && entityMappingResult !== null}
        // Configure
        selectedTier={selectedModelTier}
        onTierChange={setSelectedModelTier}
        // Run DD
        onRunDD={handleRunDDClick}
        canRunDD={canStartDD}
        runDDTooltip={runDDTooltip}
        docsToProcessCount={docsToProcessCount}
        // Processing state
        isProcessing={isProcessingInProgress}
        isPaused={isPaused}
        onPauseResume={handlePauseResume}
        onCancel={handleCancel}
        isCancelling={isCancelling}
        // Restart
        showRestart={isRunStuck || isUnexpectedFailure}
        onRestart={handleRestart}
        isRestarting={isRestarting}
        // Disabled during operations
        disabled={isClassificationInProgress || isOrganisationInProgress}
      />

      {/* Pending Checkpoint Banner */}
      {checkpointData?.has_checkpoint && checkpointData.checkpoint?.status === 'awaiting_user_input' && !showValidationWizard && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 p-4 rounded-lg border-2 border-amber-400 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-600"
        >
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 dark:bg-amber-800/40 rounded-full">
                <ClipboardCheck className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <h4 className="font-semibold text-amber-900 dark:text-amber-200">
                  Your Input Needed
                </h4>
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  {checkpointData.checkpoint.checkpoint_type === 'entity_confirmation'
                    ? 'Please confirm the entity relationships identified in the documents.'
                    : 'Please review and confirm our understanding of the transaction before continuing analysis.'}
                </p>
              </div>
            </div>
            <Button
              onClick={() => setShowValidationWizard(true)}
              className="bg-amber-600 hover:bg-amber-700 text-white transition-all duration-200 hover:scale-105"
            >
              <ClipboardCheck className="w-4 h-4 mr-2" />
              Open Validation Wizard
            </Button>
          </div>
        </motion.div>
      )}

      {/* Main content - Two column layout (Documents 60% | Pipeline 40%) */}
      <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
        {/* LEFT COLUMN (6/10 = 60%) - Documents (primary action area) */}
        <div className="lg:col-span-6 order-2 lg:order-1">
          {/* File Tree - Unified document panel */}
          <FileTree
            ddId={ddId}
            selectedDocIds={selectedDocIds}
            onSelectionChange={handleSelectionChange}
            onRecheckReadability={runReadabilityCheck}
            isCheckingReadability={checkReadability.isPending}
            isCollapsed={isDocPanelCollapsed}
            onToggleCollapse={() => setIsDocPanelCollapsed(!isDocPanelCollapsed)}
            isClassificationMode={currentPhase === "classified" || currentPhase === "organised" || currentPhase === "readability" || currentPhase === "ready" || currentPhase === "processing" || currentPhase === "completed"}
            transactionType={ddData?.transaction_type}
            categoryDistribution={categoryDistribution}
            documentsByCategory={documentsByCategory}
            classifiedCount={organisationProgress?.classifiedCount || 0}
            totalDocuments={organisationProgress?.totalDocuments || documents.length}
            isMovingDocument={documentReassign.isPending}
            onMoveDocument={handleMoveDocument}
            onAddCategory={handleAddCategory}
            onDeleteCategory={handleDeleteCategory}
            onClassifyDocuments={(reset) => {
              if (ddId) {
                addLogEntry("info", reset ? "Reclassifying all documents..." : "Classifying documents...");
                classifyDocuments.mutate({ ddId, reset }, {
                  onSuccess: () => {
                    addLogEntry("success", "Document classification started");
                    refetchOrganisation();
                  },
                  onError: (err) => {
                    addLogEntry("error", `Classification failed: ${err.message}`);
                  }
                });
              }
            }}
            isClassifying={classifyDocuments.isPending || organisationProgress?.status === "classifying"}
            hideHeaderActions
            blueprintRequirements={blueprintRequirements}
            onDeleteDocuments={(documentIds) => {
              if (ddId) {
                addLogEntry("info", `Deleting ${documentIds.length} document(s)...`);
                deleteDocument.mutate({ ddId, documentIds }, {
                  onSuccess: (result) => {
                    addLogEntry("success", `Deleted ${result.deleted_count} document(s)`);
                    refetchDD();
                    refetchOrganisation();
                  },
                  onError: (err) => {
                    addLogEntry("error", `Failed to delete: ${err.message}`);
                  }
                });
              }
            }}
            isDeletingDocuments={deleteDocument.isPending}
          />

          {/* Process Log - below documents */}
          <div className="mt-4">
          <ProcessLog
            entries={logEntries}
            isCollapsed={isLogCollapsed}
            onToggleCollapse={() => setIsLogCollapsed(!isLogCollapsed)}
            summary={
              readabilitySummary.ready > 0
                ? `${readabilitySummary.ready} ready, ${readabilitySummary.failed} failed`
                : undefined
            }
            currentlyProcessing={
              progress?.status === "processing" && progress?.currentDocumentName
                ? {
                    documentName: progress.currentDocumentName,
                    passLabel: PASS_CONFIG[progress.currentPass]?.label || progress.currentPass,
                    itemsProcessed: progress.passProgress?.[progress.currentPass]?.itemsProcessed,
                    totalItems: progress.passProgress?.[progress.currentPass]?.totalItems,
                  }
                : null
            }
          />
          </div>
        </div>

        {/* RIGHT COLUMN (4/10 = 40%) - Pipeline status area */}
        <div className="lg:col-span-4 order-1 lg:order-2 space-y-4">
          {/* Processing Pipeline Card */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-300 dark:border-gray-600 shadow-lg overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-alchemyPrimaryNavyBlue border-b border-gray-700">
              <h2 className="font-medium text-white">
                Processing Pipeline
              </h2>
            </div>
            {/* Content */}
            <div className="p-4">

            {/* Classification progress moved to ClassificationProgressModal */}

            {/* Cancelled state - show restart option */}
            {currentPhase === "cancelled" && (
              <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
                      Classification Cancelled
                    </p>
                    <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                      Documents remain in their original flat structure. You can restart classification or proceed without organising.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (ddId) {
                          addLogEntry("info", "Restarting document classification (all documents)...");
                          classifyDocuments.mutate({ ddId, reset: true });
                        }
                      }}
                      disabled={classifyDocuments.isPending}
                      className="text-xs transition-all duration-200 hover:scale-105 hover:shadow-md"
                    >
                      Restart Classification
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => {
                        // Skip organisation and go to ready state
                        addLogEntry("info", "Proceeding without folder organisation");
                      }}
                      className="text-xs transition-all duration-200 hover:scale-105 hover:shadow-md"
                    >
                      Skip & Continue
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Pipeline rings */}
            <div className="flex justify-center mt-20 mb-8">
              <PipelineRings progress={progress} size={200} />
            </div>

            {/* Pass progress bars - compact for narrow column */}
            <div className="space-y-2 mt-24">
              {(["extract", "analyze", "calculate", "crossdoc", "aggregate", "synthesize", "verify"] as const).map((pass) => {
                const config = PASS_CONFIG[pass];
                const passProgress = progress?.passProgress?.[pass];
                const isCompleted = passProgress?.status === "completed";
                const isFailed = passProgress?.status === "failed";
                const isActive = progress?.currentPass === pass && progress?.status === "processing";

                const ringColor = RING_COLORS[pass as ProcessingPass];
                const barColor = isFailed
                  ? STATUS_COLORS.failed
                  : isCompleted || isActive
                    ? ringColor
                    : STATUS_COLORS.default;

                return (
                  <div key={pass} className="flex items-center gap-2">
                    <div className="w-20 text-xs text-gray-600 dark:text-gray-400">
                      {config.shortLabel}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div
                        className="h-1.5 rounded-full overflow-hidden"
                        style={{
                          backgroundColor: 'transparent',
                          border: `1px solid ${barColor}`,
                        }}
                      >
                        <motion.div
                          className="h-full rounded-full"
                          style={{ backgroundColor: barColor }}
                          initial={{ width: 0 }}
                          animate={{ width: `${passProgress?.progress ?? 0}%` }}
                          transition={{ type: "spring", stiffness: 50, damping: 20 }}
                        />
                      </div>
                    </div>
                    <div
                      className="w-10 text-right text-[10px] font-mono"
                      style={{ color: barColor }}
                    >
                      {passProgress?.progress ?? 0}%
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Time tracking */}
            <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700 text-center text-xs text-gray-500">
              <span>Elapsed: {elapsedTime}</span>
            </div>
            </div>
          </div>

          {/* Risk Summary */}
          {(currentPhase === "processing" || currentPhase === "completed") && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-300 dark:border-gray-600 shadow-lg overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 bg-alchemyPrimaryNavyBlue border-b border-gray-700">
                <h2 className="font-medium text-white">
                  Due Diligence Findings
                </h2>
              </div>
              {/* Content */}
              <div className="p-4">
                <RiskSummaryCounters summary={riskSummary} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Dialog - All docs ready */}
      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base">Start Due Diligence Analysis?</DialogTitle>
            <DialogDescription className="text-sm">
              {docsToProcessCount} document(s) will be analysed.
              {selectedDocIds.size === 0 && " (All readable documents)"}
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <AccuracyTierSelector
              value={selectedModelTier}
              onChange={setSelectedModelTier}
            />
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" size="sm" onClick={() => setShowConfirmDialog(false)} className="transition-all duration-200 hover:scale-105 hover:shadow-md">
              Cancel
            </Button>
            <Button size="sm" className="bg-green-600 hover:bg-green-700 transition-all duration-200 hover:scale-105 hover:shadow-md" onClick={handleStartDD}>
              Start Analysis
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Warning Dialog - Some docs failed */}
      <Dialog open={showWarningDialog} onOpenChange={setShowWarningDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600 text-base">
              <AlertTriangle className="h-4 w-4" />
              Some Documents Failed
            </DialogTitle>
            <DialogDescription className="text-sm pt-2">
              {readabilitySummary.failed} document(s) failed readability check and will be skipped.
              {docsToProcessCount} document(s) will be analysed.
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <AccuracyTierSelector
              value={selectedModelTier}
              onChange={setSelectedModelTier}
            />
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" size="sm" onClick={() => setShowWarningDialog(false)} className="transition-all duration-200 hover:scale-105 hover:shadow-md">
              Go Back
            </Button>
            <Button size="sm" className="bg-amber-600 hover:bg-amber-700 transition-all duration-200 hover:scale-105 hover:shadow-md" onClick={handleStartDD}>
              Proceed Anyway
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Re-run Warning Dialog - Same documents already processed */}
      <Dialog open={showRerunWarningDialog} onOpenChange={setShowRerunWarningDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-blue-600 text-base">
              <RefreshCw className="h-4 w-4" />
              Re-run Analysis?
            </DialogTitle>
            <DialogDescription className="text-sm pt-2 space-y-2">
              <p>
                These documents were already analysed in <strong>{matchingCompletedRun?.name}</strong>
                {matchingCompletedRun?.completedAt && (
                  <span className="text-muted-foreground">
                    {" "}({new Date(matchingCompletedRun.completedAt).toLocaleDateString()})
                  </span>
                )}.
              </p>
              <p className="text-muted-foreground">
                Running DD again on the same documents will create a new analysis run.
                This may be useful if you want to compare results or if documents have been updated.
              </p>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" size="sm" onClick={() => setShowRerunWarningDialog(false)} className="transition-all duration-200 hover:scale-105 hover:shadow-md">
              Cancel
            </Button>
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700 transition-all duration-200 hover:scale-105 hover:shadow-md" onClick={handleStartDD}>
              Run Again
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Validation Wizard Modal - Human-in-the-loop Checkpoint B */}
      {checkpointData?.has_checkpoint && checkpointData.checkpoint && (
        <ValidationWizardModal
          open={showValidationWizard}
          onClose={() => setShowValidationWizard(false)}
          checkpoint={checkpointData.checkpoint}
          ddId={ddId}
          onComplete={() => {
            setShowValidationWizard(false);
            refetchCheckpoint();
            refetch(); // Refresh processing progress
            addLogEntry("success", "Validation checkpoint completed", "Analysis will continue with your corrections");
          }}
          onSkip={() => {
            setShowValidationWizard(false);
            refetchCheckpoint();
            refetch();
            addLogEntry("info", "Validation checkpoint skipped", "Analysis will continue with AI assessments");
          }}
        />
      )}

      {/* Entity Mapping Modal - Checkpoint A.5 */}
      <EntityMappingModal
        isOpen={showEntityMappingModal}
        onClose={() => setShowEntityMappingModal(false)}
        isRunning={entityMapping.isPending}
        result={entityMappingResult}
        onConfirmEntities={(confirmations) => {
          // TODO: Send confirmations to backend
          addLogEntry("success", `Entity relationships confirmed for ${Object.keys(confirmations).length} entities`);
        }}
      />

      {/* Completion celebration */}
      <AnimatePresence>
        {progress?.status === "completed" && currentRunId && !isCompletionDismissed(currentRunId) && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setCompletionDismissed(currentRunId)}
          >
            <motion.div
              variants={celebrationVariants}
              initial="initial"
              animate="animate"
              className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 max-w-md mx-4 text-center relative"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Close button */}
              <button
                onClick={() => setCompletionDismissed(currentRunId)}
                className="absolute top-3 right-3 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-all duration-200 hover:scale-110"
                aria-label="Close"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>

              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, ...SPRING_GENTLE }}
                className="w-20 h-20 bg-emerald-100 dark:bg-emerald-900/30 rounded-full flex items-center justify-center mx-auto mb-4"
              >
                <CheckCircle2 className="w-10 h-10 text-emerald-600 dark:text-emerald-400" />
              </motion.div>

              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Analysis Complete!
              </h2>

              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Found {progress.findingCounts?.total ?? 0} findings across{" "}
                {progress.totalDocuments ?? 0} documents
              </p>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setCompletionDismissed(currentRunId)} className="flex-1 transition-all duration-200 hover:scale-105 hover:shadow-md">
                  Back to DD
                </Button>
                <Button onClick={handleViewResults} className="flex-1 transition-all duration-200 hover:scale-105 hover:shadow-md">
                  View Results
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default DDProcessingDashboard;
