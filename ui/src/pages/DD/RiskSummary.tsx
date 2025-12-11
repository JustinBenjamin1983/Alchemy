// File: ui/src/pages/DD/RiskSummary.tsx
import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { DiligenceDashboard } from "./DiligenceDashboard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  CheckCircle,
  AlertCircle,
  Info,
  FileCheck2,
  MoreVertical,
  Filter,
  Download,
  Eye,
  EyeOff,
  AlertTriangle,
  FileText,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useGetDDRiskResults } from "@/hooks/useGetDDRiskResults";
import { useMutateGetLink } from "@/hooks/useMutateGetLink";
import Markdown from "react-markdown";
import { useMutatePerspectiveRiskFindingStatusChange } from "@/hooks/useMutatePerspectiveRiskFindingStatusChange";
import { useMutatePerspectiveRiskFindingSetIsReviewed } from "@/hooks/useMutatePerspectiveRiskFindingSetIsReviewed";
import { AlertCheckFor } from "@/components/AlertCheckFor";
import { useMutateDDRiskAdd } from "@/hooks/useMutateDDRiskAdd";
import SingleTextPrompt from "@/components/SingleTextPrompt";
import { useMutateDDRiskEdit } from "@/hooks/useMutateDDRiskEdit";
import { useGetDDRisks } from "@/hooks/useGetDDRisks";
import { useGetDD } from "@/hooks/useGetDD";
import EnhancedRiskManager from "./EnhancedRiskManager";
import { generateDDReport } from "@/utils/reportGenerator";

type DocRef = {
  id: string;
  original_file_name: string;
  folder: { path: string };
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
  action_items?: string; // JSON string
  missing_documents?: string; // JSON string
  document: DocRef;
  page_number?: number;
  finding_is_reviewed?: boolean;
  detail?: string;
  category?: string;
};

type CategoryGroup = {
  all: Finding[];
  positive: Finding[];
  negative: Finding[];
  neutral: Finding[];
  gaps: Finding[];
  questions: Record<string, Finding[]>;
};

// Helper functions
function getUnmatchedPerspectiveRisks(risks, findingsByCategory) {
  const allFindingIds = new Set();
  findingsByCategory.forEach((category) => {
    category.findings.forEach((finding) => {
      allFindingIds.add(finding.perspective_risk_id);
    });
  });
  return risks.filter((risk) => !allFindingIds.has(risk.perspective_risk_id));
}

function isEmptyFinding(finding) {
  return (
    !finding.phrase ||
    finding.phrase.trim() === "" ||
    finding.phrase.includes("Nothing useful found") ||
    finding.phrase.includes("No relevant content found") ||
    finding.phrase.includes("Unable to find relevant information")
  );
}

function filterFindings(findings, showEmptyFindings) {
  if (showEmptyFindings) {
    return findings;
  }
  return findings.filter((finding) => !isEmptyFinding(finding));
}

// Main component
export function RiskSummary() {
  const [selectedDDID, setSelectedDDID] = useState(() => {
    const query = new URLSearchParams(location.search);
    return query.get("id");
  });

  // State management
  const [viewMode, setViewMode] = useState<
    "dashboard" | "detailed" | "risks" | "compliance"
  >("dashboard");
  const [filterType, setFilterType] = useState<
    "all" | "positive" | "negative" | "gaps" | "neutral"
  >("all");
  const [filterConfidence, setFilterConfidence] = useState<
    "all" | "high" | "medium" | "low"
  >("all");
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [showEmptyFindings, setShowEmptyFindings] = useState(false);
  const [selectedFindingId, setSelectedFindingId] = useState(null);
  const [showAskToDelete, setShowAskToDelete] = useState(false);
  const [showEnhancedRiskManager, setShowEnhancedRiskManager] = useState(false);
  const [showEditRisk, setShowEditRisk] = useState(false);
  const [selectedRisk, setSelectedRisk] = useState(null);
  const [currentTab, setCurrentTab] = useState<string>(null);
  const [risksNotProcessed, setRisksNotProcessed] = useState(null);

  // Polling state
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Hooks
  const mutateRiskFindingSetIsReviewed =
    useMutatePerspectiveRiskFindingSetIsReviewed();
  const mutateGetLink = useMutateGetLink();
  const mutateChangeRiskStatus = useMutatePerspectiveRiskFindingStatusChange();
  const mutateAddRisk = useMutateDDRiskAdd();
  const mutateEditRisk = useMutateDDRiskEdit();
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  const handleGenerateReport = async () => {
    if (!dd || filteredFindings.length === 0) {
      alert("No findings available to generate report");
      return;
    }
    setIsGeneratingReport(true);
    try {
      await generateDDReport(dd.name, filteredFindings, categories);
    } catch (error) {
      console.error("Failed to generate report:", error);
      alert("Failed to generate report. Please try again.");
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const { data: risks, refetch: refetchRisks } = useGetDDRisks(selectedDDID);
  const {
    data: riskResultsRaw,
    isSuccess: ddRiskResultsSuccess,
    refetch: refetchRiskResults,
    isFetching: isRiskResultsFetching,
  } = useGetDDRiskResults(selectedDDID);

  const riskResults = (riskResultsRaw ?? []) as Array<{
    category?: string;
    findings?: Finding[];
  }>;

  const { data: dd } = useGetDD(selectedDDID);

  // Manual refresh function (same as your working refresh button)
  const handleManualRefresh = useCallback(async () => {
    try {
      await Promise.all([refetchRisks(), refetchRiskResults()]);
    } catch (error) {
      console.warn("Refresh error:", error);
    }
  }, [refetchRisks, refetchRiskResults]);

  // Start polling function
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    pollingIntervalRef.current = setInterval(() => {
      handleManualRefresh();
    }, 5000); // Poll every 5 seconds

    setIsPolling(true);
  }, [handleManualRefresh]);

  // Stop polling function
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Smart polling logic - start/stop based on processing status
  useEffect(() => {
    if (risks && riskResults) {
      const unprocessedRisks = getUnmatchedPerspectiveRisks(risks, riskResults);
      const hasUnprocessedRisks =
        unprocessedRisks && unprocessedRisks.length > 0;

      setRisksNotProcessed(unprocessedRisks);

      if (hasUnprocessedRisks && !isPolling) {
        // Start polling when we have unprocessed risks
        console.log(
          "Starting polling - unprocessed risks found:",
          unprocessedRisks.length
        );
        startPolling();
      } else if (!hasUnprocessedRisks && isPolling) {
        // Stop polling when processing is complete
        console.log("Stopping polling - all risks processed");
        stopPolling();

        // Do one final refresh after stopping
        setTimeout(() => {
          handleManualRefresh();
        }, 2000);
      }
    }
  }, [
    risks,
    riskResults,
    isPolling,
    startPolling,
    stopPolling,
    handleManualRefresh,
  ]);

  // Process and filter findings
  const allFindings: Finding[] = useMemo(() => {
    if (!riskResults) return [];
    return riskResults.flatMap((category) =>
      (category.findings ?? []).map((finding) => ({
        ...finding,
        category: category.category ?? "Uncategorized",
      }))
    );
  }, [riskResults]);

  const filteredFindings: Finding[] = useMemo(() => {
    let findings = [...allFindings];
    // Apply category filter
    if (filterCategory !== "all") {
      findings = findings.filter((f) => f.category === filterCategory);
    }
    // Apply type filter
    if (filterType !== "all") {
      findings = findings.filter((f) => {
        const findingType = f.finding_type || "neutral";
        if (filterType === "positive")
          return findingType === "positive" || f.finding_status === "Green";
        if (filterType === "negative")
          return (
            findingType === "negative" ||
            ["Red", "Amber"].includes(f.finding_status)
          );
        if (filterType === "gaps")
          return findingType === "gap" || f.finding_status === "Info";
        if (filterType === "neutral")
          return findingType === "neutral" || findingType === "informational";
        return true;
      });
    }
    // Apply confidence filter
    if (filterConfidence !== "all") {
      findings = findings.filter((f) => {
        const confidence = f.confidence_score || 0.5;
        if (filterConfidence === "high") return confidence >= 0.8;
        if (filterConfidence === "medium")
          return confidence >= 0.5 && confidence < 0.8;
        if (filterConfidence === "low") return confidence < 0.5;
        return true;
      });
    }
    // Apply empty findings filter
    if (!showEmptyFindings) {
      findings = findings.filter((f) => !isEmptyFinding(f));
    }
    return findings;
  }, [
    allFindings,
    filterType,
    filterConfidence,
    filterCategory,
    showEmptyFindings,
  ]);

  // Group findings by category and type
  const findingsByCategory = useMemo<Record<string, CategoryGroup>>(() => {
    const grouped: Record<string, CategoryGroup> = {};
    filteredFindings.forEach((finding) => {
      const category = finding.category ?? "Uncategorized";
      if (!grouped[category]) {
        grouped[category] = {
          all: [],
          positive: [],
          negative: [],
          neutral: [],
          gaps: [],
          questions: {},
        };
      }
      grouped[category].all.push(finding);
      const type = finding.finding_type ?? "neutral";
      if (type === "positive" || finding.finding_status === "Green") {
        grouped[category].positive.push(finding);
      } else if (
        type === "negative" ||
        ["Red", "Amber"].includes(finding.finding_status ?? "")
      ) {
        grouped[category].negative.push(finding);
      } else if (type === "gap" || finding.finding_status === "Info") {
        grouped[category].gaps.push(finding);
      } else {
        grouped[category].neutral.push(finding);
      }
      const questionKey = finding.detail ?? "Unknown Question";
      (grouped[category].questions[questionKey] ??= []).push(finding);
    });
    return grouped;
  }, [filteredFindings]);

  // Get unique categories
  const categories: string[] = useMemo(() => {
    if (!riskResults) return [];
    return Array.from(
      new Set(riskResults.map((r) => r.category ?? "Uncategorized"))
    );
  }, [riskResults]);

  const onFilterTypeChange = (v: string) =>
    setFilterType(v as "all" | "positive" | "negative" | "gaps" | "neutral");

  const onFilterConfidenceChange = (v: string) =>
    setFilterConfidence(v as "all" | "high" | "medium" | "low");

  // Effects
  useEffect(() => {
    if (!ddRiskResultsSuccess) return;
    setCurrentTab(riskResults?.[0]?.category);
  }, [ddRiskResultsSuccess]);

  useEffect(() => {
    if (!mutateGetLink.isSuccess) return;
    window.open(mutateGetLink.data.data.url, "_blank", "noopener,noreferrer");
  }, [mutateGetLink.isSuccess]);

  useEffect(() => {
    if (!mutateChangeRiskStatus.isSuccess) return;
    setTimeout(() => {
      document.body.style.pointerEvents = "auto";
    }, 500);
    setShowAskToDelete(false);
  }, [mutateChangeRiskStatus]);

  useEffect(() => {
    if (!mutateAddRisk.isSuccess) return;
    setShowEnhancedRiskManager(false);
  }, [mutateAddRisk.isSuccess]);

  useEffect(() => {
    if (!mutateEditRisk.isSuccess) return;
    setShowEditRisk(false);
    setSelectedRisk(null);
  }, [mutateEditRisk.isSuccess]);

  // Handlers
  const viewDoc = (perspective_risk_finding_id, doc_id) => {
    mutateRiskFindingSetIsReviewed.mutate({
      dd_id: selectedDDID,
      perspective_risk_finding_id,
    });
    mutateGetLink.mutate({ doc_id: doc_id, is_dd: true });
  };

  const changeRiskStatus = (perspective_risk_finding_id, status) => {
    if (status === "Deleted") {
      setSelectedFindingId(perspective_risk_finding_id);
      setShowAskToDelete(true);
    } else {
      mutateChangeRiskStatus.mutate({
        dd_id: selectedDDID,
        perspective_risk_finding_id,
        status,
      });
    }
  };

  const changeRiskStatusToDeleted = () => {
    mutateChangeRiskStatus.mutate({
      dd_id: selectedDDID,
      perspective_risk_finding_id: selectedFindingId,
      status: "Deleted",
    });
  };

  const handleEnhancedRiskManagerSubmit = (risks) => {
    const formattedRisks = risks.map((risk) => ({
      category: risk.category,
      detail: risk.detail,
      folder_scope: risk.folder_scope,
    }));
    mutateAddRisk.mutate(
      {
        dd_id: selectedDDID,
        risks: formattedRisks,
      },
      {
        onSuccess: () => {
          // Trigger immediate refresh and start polling
          handleManualRefresh();
          // Polling will start automatically when unprocessed risks are detected
        },
      }
    );
  };

  const handleEditRisk = (id, detail) => {
    setSelectedRisk({ id, detail });
    setShowEditRisk(true);
  };

  const closingEditRisk = (value) => {
    if (value == null) {
      setShowEditRisk(false);
    } else {
      mutateEditRisk.mutate({
        dd_id: selectedDDID,
        perspective_risk_id: selectedRisk.id,
        detail: value,
      });
    }
  };

  const copyInfo = (finding) => {
    const text = `Category: ${finding.category}\nQuestion: ${
      finding.detail
    }\n\nFinding: ${finding.phrase || finding.direct_answer}\nDocument: ${
      finding.document.original_file_name
    }\nPage: ${finding.page_number}\nLocation: ${
      finding.document.folder.path
    }\nConfidence: ${Math.round((finding.confidence_score || 0.5) * 100)}%`;
    navigator.clipboard.writeText(text);
  };

  const exportFindings = () => {
    const exportData = {
      exportDate: new Date().toISOString(),
      dueDiligence: dd?.name || selectedDDID,
      summary: {
        total: filteredFindings.length,
        positive: filteredFindings.filter((f) => f.finding_type === "positive")
          .length,
        negative: filteredFindings.filter((f) => f.finding_type === "negative")
          .length,
        gaps: filteredFindings.filter((f) => f.finding_type === "gap").length,
        requiresAction: filteredFindings.filter((f) => f.requires_action)
          .length,
      },
      findings: filteredFindings.map((f) => ({
        category: f.category,
        question: f.detail,
        type: f.finding_type,
        status: f.finding_status,
        confidence: f.confidence_score,
        answer: f.direct_answer || f.phrase,
        evidence: f.evidence_quote,
        document: f.document.original_file_name,
        page: f.page_number,
        requiresAction: f.requires_action,
        actionItems: f.action_items ? JSON.parse(f.action_items) : [],
      })),
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `due-diligence-findings-${selectedDDID}-${
      new Date().toISOString().split("T")[0]
    }.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Render finding card (keeping original implementation)
  const renderFindingCard = (finding, index) => {
    const findingType = finding.finding_type || "neutral";
    const confidence = finding.confidence_score || 0.5;
    const isDeleted = finding.finding_status === "Deleted";
    let bgColor = "bg-gray-50";
    let borderColor = "border-gray-200";
    let iconComponent = <Info className="w-5 h-5 text-gray-500" />;

    if (findingType === "positive" || finding.finding_status === "Green") {
      bgColor = "bg-green-50";
      borderColor = "border-green-200";
      iconComponent = <CheckCircle className="w-5 h-5 text-green-500" />;
    } else if (
      findingType === "negative" ||
      ["Red", "Amber"].includes(finding.finding_status)
    ) {
      bgColor = finding.finding_status === "Red" ? "bg-red-50" : "bg-orange-50";
      borderColor =
        finding.finding_status === "Red"
          ? "border-red-200"
          : "border-orange-200";
      iconComponent = (
        <AlertCircle
          className={`w-5 h-5 ${
            finding.finding_status === "Red"
              ? "text-red-500"
              : "text-orange-500"
          }`}
        />
      );
    } else if (findingType === "gap") {
      bgColor = "bg-blue-50";
      borderColor = "border-blue-200";
      iconComponent = <Info className="w-5 h-5 text-blue-500" />;
    }

    return (
      <div
        key={finding.finding_id || index}
        className={cn(
          "p-4 rounded-lg border transition-all",
          bgColor,
          borderColor,
          isDeleted && "opacity-50"
        )}
      >
        <div className="flex justify-between items-start gap-4">
          <div className="flex gap-3 flex-1">
            <div className="mt-1">{iconComponent}</div>
            <div className="flex-1 space-y-2">
              {/* Direct Answer if available */}
              {finding.direct_answer && (
                <div className="font-medium text-sm">
                  {finding.direct_answer}
                </div>
              )}
              {/* Main finding text */}
              {finding.phrase && !isEmptyFinding(finding) && (
                <div className="text-sm text-gray-700">
                  <Markdown className="prose prose-sm max-w-none">
                    {finding.phrase}
                  </Markdown>
                </div>
              )}
              {/* Evidence quote if available */}
              {finding.evidence_quote && (
                <blockquote className="border-l-4 border-gray-300 pl-3 italic text-sm text-gray-600">
                  "{finding.evidence_quote}"
                </blockquote>
              )}
              {/* Action items if required */}
              {finding.requires_action && finding.action_items && (
                <div className="mt-3 p-2 bg-yellow-50 rounded">
                  <p className="text-sm font-medium text-yellow-900 mb-1">
                    Required Actions:
                  </p>
                  <ul className="list-disc list-inside text-sm text-yellow-800">
                    {JSON.parse(finding.action_items || "[]").map(
                      (action, i) => (
                        <li key={i}>{action}</li>
                      )
                    )}
                  </ul>
                </div>
              )}
              {/* Missing documents */}
              {finding.missing_documents &&
                JSON.parse(finding.missing_documents || "[]").length > 0 && (
                  <div className="mt-2">
                    <p className="text-sm font-medium text-gray-700">
                      Missing Documents:
                    </p>
                    <ul className="list-disc list-inside text-sm text-gray-600">
                      {JSON.parse(finding.missing_documents).map((doc, i) => (
                        <li key={i}>{doc}</li>
                      ))}
                    </ul>
                  </div>
                )}
              {/* Metadata badges */}
              <div className="flex flex-wrap gap-2 mt-3">
                <Badge variant="outline" className="text-xs">
                  {finding.document.original_file_name}
                </Badge>
                {finding.page_number && (
                  <Badge variant="outline" className="text-xs">
                    Page {finding.page_number}
                  </Badge>
                )}
                <Badge variant="outline" className="text-xs">
                  Confidence: {Math.round(confidence * 100)}%
                </Badge>
                {finding.finding_status && finding.finding_status !== "New" && (
                  <Badge
                    className={cn(
                      "text-xs",
                      finding.finding_status === "Red" && "bg-red-600",
                      finding.finding_status === "Amber" && "bg-orange-500",
                      finding.finding_status === "Green" && "bg-green-600",
                      finding.finding_status === "Info" && "bg-blue-600"
                    )}
                  >
                    {finding.finding_status}
                  </Badge>
                )}
                {finding.finding_is_reviewed && (
                  <Badge variant="secondary" className="text-xs">
                    <FileCheck2 className="w-3 h-3 mr-1" />
                    Reviewed
                  </Badge>
                )}
              </div>
            </div>
          </div>
          {/* Actions dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                <MoreVertical className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuItem
                onClick={() => viewDoc(finding.finding_id, finding.document.id)}
              >
                View Document
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => copyInfo(finding)}>
                Copy Info
              </DropdownMenuItem>
              {finding.perspective_risk_id && (
                <DropdownMenuItem
                  onClick={() =>
                    handleEditRisk(finding.perspective_risk_id, finding.detail)
                  }
                >
                  Edit Question
                </DropdownMenuItem>
              )}
              {finding.finding_status === "Deleted" ? (
                <DropdownMenuItem
                  onClick={() => changeRiskStatus(finding.finding_id, "New")}
                >
                  Restore
                </DropdownMenuItem>
              ) : (
                <>
                  <DropdownMenuItem
                    onClick={() =>
                      changeRiskStatus(finding.finding_id, "Deleted")
                    }
                  >
                    Delete
                  </DropdownMenuItem>
                  {finding.finding_status !== "Green" && (
                    <DropdownMenuItem
                      onClick={() =>
                        changeRiskStatus(finding.finding_id, "Green")
                      }
                    >
                      Mark as Positive
                    </DropdownMenuItem>
                  )}
                  {finding.finding_status !== "Amber" && (
                    <DropdownMenuItem
                      onClick={() =>
                        changeRiskStatus(finding.finding_id, "Amber")
                      }
                    >
                      Mark as Amber Risk
                    </DropdownMenuItem>
                  )}
                  {finding.finding_status !== "Red" && (
                    <DropdownMenuItem
                      onClick={() =>
                        changeRiskStatus(finding.finding_id, "Red")
                      }
                    >
                      Mark as Red Risk
                    </DropdownMenuItem>
                  )}
                  {["Red", "Amber", "Green"].includes(
                    finding.finding_status
                  ) && (
                    <DropdownMenuItem
                      onClick={() =>
                        changeRiskStatus(finding.finding_id, "New")
                      }
                    >
                      Clear Status
                    </DropdownMenuItem>
                  )}
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 space-y-4">
      {/* Enhanced Processing Status with polling indicator */}
      {risksNotProcessed && risksNotProcessed.length > 0 && (
        <div className="text-sm pb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isPolling && (
              <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
            )}
            <span>
              You have <Badge>{risksNotProcessed.length}</Badge> question
              {risksNotProcessed.length > 1 ? "s" : ""} still being processed
            </span>
            {isPolling && (
              <span className="text-xs text-muted-foreground">(...)</span>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleManualRefresh}
            disabled={isRiskResultsFetching}
          >
            {isRiskResultsFetching ? "Refreshing..." : "Refresh"}
          </Button>
        </div>
      )}

      {/* Progress bar for processing */}
      {isPolling && risks && risksNotProcessed && (
        <div className="pb-4">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-500"
              style={{
                width: `${
                  ((risks.length - risksNotProcessed.length) / risks.length) *
                  100
                }%`,
              }}
            ></div>
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {risks.length - risksNotProcessed.length} of {risks.length}{" "}
            questions processed
          </div>
        </div>
      )}

      {/* Rest of component - modals, controls, view content */}
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
        label={`Question Detail`}
        warning={"Editing a question will invalidate all findings linked to it"}
      />

      <AlertCheckFor
        title="Delete Finding"
        blurb={`Are you sure you want to mark this finding as deleted?`}
        show={showAskToDelete}
        okText={"Yes, delete it"}
        onOK={changeRiskStatusToDeleted}
        cancelText={"No"}
        onCancel={() => {
          setShowAskToDelete(false);
          setTimeout(() => {
            document.body.style.pointerEvents = "auto";
          }, 500);
        }}
      />

      {/* Main Content */}
      {riskResults?.length > 0 ? (
        <>
          {/* Controls Bar */}
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
            {/* View Mode Buttons */}
            <div className="flex gap-2 flex-wrap">
              <Button
                variant={viewMode === "dashboard" ? "default" : "outline"}
                onClick={() => setViewMode("dashboard")}
                size="sm"
              >
                <TrendingUp className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
              <Button
                variant={viewMode === "detailed" ? "default" : "outline"}
                onClick={() => setViewMode("detailed")}
                size="sm"
              >
                <FileText className="w-4 h-4 mr-2" />
                Detailed
              </Button>
              <Button
                variant={viewMode === "risks" ? "default" : "outline"}
                onClick={() => setViewMode("risks")}
                size="sm"
              >
                <AlertTriangle className="w-4 h-4 mr-2" />
                Risks Only
              </Button>
              <Button
                variant={viewMode === "compliance" ? "default" : "outline"}
                onClick={() => setViewMode("compliance")}
                size="sm"
              >
                <CheckCircle className="w-4 h-4 mr-2" />
                Compliance
              </Button>
            </div>
            {/* Filters and Actions */}
            <div className="flex gap-2 items-center flex-wrap">
              <Filter className="w-4 h-4" />
              {/* Category Filter */}
              <Select value={filterCategory} onValueChange={setFilterCategory}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {categories.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {/* Type Filter */}
              <Select value={filterType} onValueChange={onFilterTypeChange}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="positive">Positive</SelectItem>
                  <SelectItem value="negative">Negative</SelectItem>
                  <SelectItem value="gaps">Gaps</SelectItem>
                  <SelectItem value="neutral">Neutral</SelectItem>
                </SelectContent>
              </Select>
              {/* Confidence Filter */}
              <Select
                value={filterConfidence}
                onValueChange={onFilterConfidenceChange}
              >
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Confidence" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Confidence</SelectItem>
                  <SelectItem value="high">High (80%+)</SelectItem>
                  <SelectItem value="medium">Medium (50-79%)</SelectItem>
                  <SelectItem value="low">Low (&lt;50%)</SelectItem>
                </SelectContent>
              </Select>
              {/* Empty Findings Toggle */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowEmptyFindings(!showEmptyFindings)}
                className="flex items-center gap-2"
              >
                {showEmptyFindings ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
                Empty
              </Button>
              {/* Add Questions Button */}
              <Button
                onClick={() => setShowEnhancedRiskManager(true)}
                size="sm"
              >
                Add Questions
              </Button>
              {/* Export Button */}
              <Button variant="outline" onClick={exportFindings} size="sm">
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            </div>
          </div>

          {/* View Content */}
          {viewMode === "dashboard" && (
            <DiligenceDashboard
              findings={filteredFindings}
              ddId={selectedDDID}
            />
          )}
          {viewMode === "detailed" && (
            <Tabs
              defaultValue={Object.keys(findingsByCategory)[0] || "all"}
              className="w-full"
            >
              <TabsList className="flex-wrap h-auto">
                {Object.keys(findingsByCategory).map((category) => {
                  const categoryFindings = findingsByCategory[category];
                  const totalCount = categoryFindings.all.length;
                  return (
                    <TabsTrigger
                      key={category}
                      value={category}
                      className="data-[state=active]:bg-primary"
                    >
                      {category}
                      <Badge className="ml-2" variant="secondary">
                        {totalCount}
                      </Badge>
                    </TabsTrigger>
                  );
                })}
              </TabsList>
              {Object.entries(findingsByCategory).map(
                ([category, categoryData]) => (
                  <TabsContent
                    key={category}
                    value={category}
                    className="space-y-4"
                  >
                    {/* Questions Overview */}
                    <Card>
                      <CardHeader>
                        <CardTitle>Questions in {category}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          {Object.entries(categoryData.questions).map(
                            ([question, questionFindings]) => (
                              <div
                                key={question}
                                className="border rounded-lg p-4"
                              >
                                <h3 className="font-medium mb-3">{question}</h3>
                                <div className="space-y-2">
                                  {questionFindings.map((finding, idx) =>
                                    renderFindingCard(finding, idx)
                                  )}
                                </div>
                              </div>
                            )
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>
                )
              )}
            </Tabs>
          )}
          {viewMode === "risks" && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-500" />
                    Risk Findings
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {/* Red Risks */}
                    {filteredFindings.filter((f) => f.finding_status === "Red")
                      .length > 0 && (
                      <div>
                        <h3 className="font-medium text-red-700 mb-2">
                          Critical Risks
                        </h3>
                        <div className="space-y-2">
                          {filteredFindings
                            .filter((f) => f.finding_status === "Red")
                            .map((finding, idx) =>
                              renderFindingCard(finding, idx)
                            )}
                        </div>
                      </div>
                    )}

                    {/* Amber Risks */}
                    {filteredFindings.filter(
                      (f) => f.finding_status === "Amber"
                    ).length > 0 && (
                      <div>
                        <h3 className="font-medium text-orange-700 mb-2">
                          Medium Risks
                        </h3>
                        <div className="space-y-2">
                          {filteredFindings
                            .filter((f) => f.finding_status === "Amber")
                            .map((finding, idx) =>
                              renderFindingCard(finding, idx)
                            )}
                        </div>
                      </div>
                    )}

                    {/* Other Negative Findings */}
                    {filteredFindings.filter(
                      (f) =>
                        f.finding_type === "negative" &&
                        !["Red", "Amber"].includes(f.finding_status as string)
                    ).length > 0 && (
                      <div>
                        <h3 className="font-medium text-gray-700 mb-2">
                          Other Risk Indicators
                        </h3>
                        <div className="space-y-2">
                          {filteredFindings
                            .filter(
                              (f) =>
                                f.finding_type === "negative" &&
                                !["Red", "Amber"].includes(
                                  f.finding_status as string
                                )
                            )
                            .map((finding, idx) =>
                              renderFindingCard(finding, idx)
                            )}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {viewMode === "compliance" && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    Compliance Confirmations
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Object.entries(findingsByCategory).map(
                      ([category, categoryData]) => {
                        if (categoryData.positive.length === 0) return null;
                        return (
                          <div key={category}>
                            <h3 className="font-medium text-green-700 mb-2">
                              {category}
                            </h3>
                            <div className="space-y-2">
                              {categoryData.positive.map((finding, idx) =>
                                renderFindingCard(finding, idx)
                              )}
                            </div>
                          </div>
                        );
                      }
                    )}

                    {filteredFindings.filter(
                      (f) =>
                        f.finding_type === "positive" ||
                        f.finding_status === "Green"
                    ).length === 0 && (
                      <p className="text-gray-500 text-center py-4">
                        No compliance confirmations found with current filters
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Information Gaps */}
              {filteredFindings.filter((f) => f.finding_type === "gap").length >
                0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Info className="w-5 h-5 text-blue-500" />
                      Information Gaps
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {filteredFindings
                        .filter((f) => f.finding_type === "gap")
                        .map((finding, idx) => renderFindingCard(finding, idx))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </>
      ) : (
        /* Empty State */
        <div className="text-center py-12">
          <div className="text-lg font-medium mb-2">
            No findings available for this due diligence
          </div>
          <div className="text-sm text-gray-600">
            {!dd?.has_in_progress_docs ? (
              <>
                This could be due to:
                <ul className="list-disc list-inside text-sm text-gray-600 mt-2 text-left max-w-md mx-auto">
                  <li>You haven't joined this due diligence yet</li>
                  <li>Questions are still being processed</li>
                  <li>No questions have been added</li>
                </ul>
                <Button
                  className="mt-4"
                  onClick={() => setShowEnhancedRiskManager(true)}
                >
                  Add Questions to Start
                </Button>
              </>
            ) : (
              <>Documents are still being processed. Please check back later.</>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
