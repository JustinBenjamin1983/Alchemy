/**
 * ReportVersionManager - Version Control & Refinement for DD Reports
 *
 * Provides:
 * - Version selector dropdown
 * - Side-by-side version comparison
 * - Download any version
 * - Open version in new tab
 * - AI-powered refinement with proposal/accept/reject flow
 * - Version history with change summaries
 */

import React, { useState, useMemo, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Download,
  ExternalLink,
  GitCompare,
  History,
  Sparkles,
  Check,
  X,
  Edit3,
  Loader2,
  Clock,
  User,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  FileText,
  AlertCircle,
} from "lucide-react";

import {
  useReportVersions,
  useReportVersion,
  useCompareVersions,
  useProposeRefinement,
  useMergeRefinement,
  useDownloadVersion,
  ReportVersionSummary,
  RefinementProposal,
  VersionDiff,
} from "@/hooks/useReportVersions";

// ============================================
// Types
// ============================================

interface ReportVersionManagerProps {
  runId: string;
  ddId: string;
  projectName?: string;
  onVersionChange?: (version: number) => void;
  className?: string;
}

interface VersionSelectorProps {
  versions: ReportVersionSummary[];
  selectedVersion: number | null;
  onSelect: (version: number) => void;
  isLoading?: boolean;
}

interface VersionHistoryProps {
  versions: ReportVersionSummary[];
  currentVersion: number | null;
  onSelect: (version: number) => void;
  onCompare: (v1: number, v2: number) => void;
}

interface CompareDialogProps {
  open: boolean;
  onClose: () => void;
  runId: string;
  version1: number;
  version2: number;
}

interface RefinementDialogProps {
  open: boolean;
  onClose: () => void;
  runId: string;
  currentVersion: number;
  onSuccess: () => void;
}

interface ProposalReviewProps {
  proposal: RefinementProposal;
  onAccept: () => void;
  onReject: () => void;
  onEdit: (editedText: string) => void;
  isSubmitting: boolean;
}

// ============================================
// Helper Components
// ============================================

function formatDate(dateString?: string): string {
  if (!dateString) return "Unknown";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-ZA", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function VersionBadge({ version, isCurrent }: { version: number; isCurrent: boolean }) {
  return (
    <Badge
      variant={isCurrent ? "default" : "outline"}
      className={isCurrent ? "bg-green-600" : ""}
    >
      v{version}
      {isCurrent && " (Current)"}
    </Badge>
  );
}

// ============================================
// Version Selector Dropdown
// ============================================

function VersionSelector({ versions, selectedVersion, onSelect, isLoading }: VersionSelectorProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading versions...
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        No versions available
      </div>
    );
  }

  return (
    <Select
      value={selectedVersion?.toString() || ""}
      onValueChange={(v) => onSelect(parseInt(v, 10))}
    >
      <SelectTrigger className="w-[200px]">
        <SelectValue placeholder="Select version" />
      </SelectTrigger>
      <SelectContent>
        {versions.map((v) => (
          <SelectItem key={v.version} value={v.version.toString()}>
            <div className="flex items-center gap-2">
              <span>Version {v.version}</span>
              {v.is_current && (
                <Badge variant="secondary" className="text-xs py-0">
                  Current
                </Badge>
              )}
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

// ============================================
// Version History Panel
// ============================================

function VersionHistory({ versions, currentVersion, onSelect, onCompare }: VersionHistoryProps) {
  const [expandedVersion, setExpandedVersion] = useState<number | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compareSelection, setCompareSelection] = useState<number[]>([]);

  const handleVersionClick = (version: number) => {
    if (compareMode) {
      if (compareSelection.includes(version)) {
        setCompareSelection(compareSelection.filter((v) => v !== version));
      } else if (compareSelection.length < 2) {
        const newSelection = [...compareSelection, version];
        setCompareSelection(newSelection);
        if (newSelection.length === 2) {
          onCompare(Math.min(...newSelection), Math.max(...newSelection));
          setCompareMode(false);
          setCompareSelection([]);
        }
      }
    } else {
      onSelect(version);
    }
  };

  const toggleExpand = (version: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedVersion(expandedVersion === version ? null : version);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold flex items-center gap-2">
          <History className="h-4 w-4" />
          Version History
        </h4>
        <Button
          variant={compareMode ? "default" : "outline"}
          size="sm"
          onClick={() => {
            setCompareMode(!compareMode);
            setCompareSelection([]);
          }}
          className="text-xs"
        >
          <GitCompare className="h-3 w-3 mr-1" />
          {compareMode ? "Cancel Compare" : "Compare"}
        </Button>
      </div>

      {compareMode && (
        <div className="text-xs text-muted-foreground bg-blue-50 dark:bg-blue-900/20 p-2 rounded">
          Select 2 versions to compare ({compareSelection.length}/2 selected)
        </div>
      )}

      <div className="space-y-2 max-h-[400px] overflow-y-auto">
        {versions.map((v) => {
          const isSelected = currentVersion === v.version;
          const isCompareSelected = compareSelection.includes(v.version);

          return (
            <div
              key={v.version}
              onClick={() => handleVersionClick(v.version)}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                isSelected
                  ? "border-alchemyPrimaryOrange bg-orange-50 dark:bg-orange-900/20"
                  : isCompareSelected
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                  : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <VersionBadge version={v.version} isCurrent={v.is_current} />
                  {compareMode && (
                    <div
                      className={`w-4 h-4 rounded border-2 ${
                        isCompareSelected
                          ? "bg-blue-500 border-blue-500"
                          : "border-gray-400"
                      }`}
                    >
                      {isCompareSelected && <Check className="h-3 w-3 text-white" />}
                    </div>
                  )}
                </div>
                <button
                  onClick={(e) => toggleExpand(v.version, e)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  {expandedVersion === v.version ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </button>
              </div>

              <div className="mt-2 text-xs text-muted-foreground flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatDate(v.created_at)}
                </span>
                {v.created_by && (
                  <span className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    {v.created_by.split("@")[0]}
                  </span>
                )}
              </div>

              {expandedVersion === v.version && (
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                  {v.refinement_prompt && (
                    <div className="mb-2">
                      <span className="text-xs font-medium text-muted-foreground">
                        Refinement Request:
                      </span>
                      <p className="text-sm mt-1 italic">"{v.refinement_prompt}"</p>
                    </div>
                  )}
                  {v.change_summary && (
                    <div>
                      <span className="text-xs font-medium text-muted-foreground">
                        Changes:
                      </span>
                      <p className="text-sm mt-1">{v.change_summary}</p>
                    </div>
                  )}
                  {!v.refinement_prompt && !v.change_summary && v.version === 1 && (
                    <p className="text-sm text-muted-foreground">
                      Initial version from analysis run
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================
// Compare Dialog
// ============================================

function CompareDialog({ open, onClose, runId, version1, version2 }: CompareDialogProps) {
  const compareMutation = useCompareVersions();

  React.useEffect(() => {
    if (open) {
      compareMutation.mutate({ runId, version1, version2 });
    }
  }, [open, runId, version1, version2]);

  const renderDiff = (diff: VersionDiff) => {
    return (
      <div
        key={`${diff.section}-${diff.change_type}`}
        className="p-3 rounded-lg border border-gray-200 dark:border-gray-700"
      >
        <div className="flex items-center gap-2 mb-2">
          <Badge
            variant="outline"
            className={
              diff.change_type === "added"
                ? "bg-green-50 text-green-700 border-green-200"
                : diff.change_type === "removed"
                ? "bg-red-50 text-red-700 border-red-200"
                : "bg-yellow-50 text-yellow-700 border-yellow-200"
            }
          >
            {diff.change_type}
          </Badge>
          <span className="text-sm font-medium">{diff.section}</span>
        </div>

        {diff.diff && (
          <pre className="text-xs bg-gray-50 dark:bg-gray-900 p-2 rounded overflow-x-auto">
            {diff.diff}
          </pre>
        )}

        {diff.old_item && diff.new_item && (
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-red-50 dark:bg-red-900/20 p-2 rounded">
              <span className="font-medium text-red-700 dark:text-red-400">Before:</span>
              <pre className="mt-1 whitespace-pre-wrap">
                {JSON.stringify(diff.old_item, null, 2)}
              </pre>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 p-2 rounded">
              <span className="font-medium text-green-700 dark:text-green-400">After:</span>
              <pre className="mt-1 whitespace-pre-wrap">
                {JSON.stringify(diff.new_item, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitCompare className="h-5 w-5" />
            Compare Versions
          </DialogTitle>
          <DialogDescription>
            Comparing Version {version1} with Version {version2}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-4">
          {compareMutation.isPending ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">Comparing versions...</span>
            </div>
          ) : compareMutation.isError ? (
            <div className="text-center py-8 text-red-500">
              <AlertCircle className="h-8 w-8 mx-auto mb-2" />
              <p>Failed to compare versions</p>
            </div>
          ) : compareMutation.data ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>{compareMutation.data.total_changes} change(s) found</span>
              </div>

              {compareMutation.data.total_changes === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Check className="h-8 w-8 mx-auto mb-2 text-green-500" />
                  <p>These versions are identical</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {compareMutation.data.diffs.map(renderDiff)}
                </div>
              )}
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============================================
// Proposal Review Component
// ============================================

function ProposalReview({ proposal, onAccept, onReject, onEdit, isSubmitting }: ProposalReviewProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(proposal.proposed_text);

  const handleSaveEdit = () => {
    onEdit(editedText);
    setIsEditing(false);
  };

  return (
    <div className="space-y-4">
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-2">
          AI Proposal
        </h4>
        <p className="text-sm text-blue-700 dark:text-blue-400 mb-3">
          {proposal.reasoning}
        </p>
        <div className="flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400">
          <Badge variant="outline" className="text-xs">
            Section: {proposal.section}
          </Badge>
          <Badge variant="outline" className="text-xs">
            Action: {proposal.change_type}
          </Badge>
        </div>
      </div>

      {proposal.current_text && (
        <div>
          <Label className="text-xs text-muted-foreground mb-1 block">Current Text</Label>
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
            <p className="text-sm line-through text-red-700 dark:text-red-400">
              {proposal.current_text}
            </p>
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-1">
          <Label className="text-xs text-muted-foreground">Proposed Text</Label>
          {!isEditing && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsEditing(true)}
              className="h-6 text-xs"
            >
              <Edit3 className="h-3 w-3 mr-1" />
              Edit
            </Button>
          )}
        </div>
        {isEditing ? (
          <div className="space-y-2">
            <Textarea
              value={editedText}
              onChange={(e) => setEditedText(e.target.value)}
              className="min-h-[120px]"
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={handleSaveEdit}>
                Save Edit
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setIsEditing(false);
                  setEditedText(proposal.proposed_text);
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
            <p className="text-sm text-green-700 dark:text-green-400">
              {editedText}
            </p>
          </div>
        )}
      </div>

      <div className="flex gap-3 pt-2">
        <Button
          onClick={onAccept}
          disabled={isSubmitting}
          className="bg-green-600 hover:bg-green-700"
        >
          {isSubmitting ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Check className="h-4 w-4 mr-2" />
          )}
          Accept & Create New Version
        </Button>
        <Button
          variant="outline"
          onClick={onReject}
          disabled={isSubmitting}
          className="border-red-300 text-red-600 hover:bg-red-50"
        >
          <X className="h-4 w-4 mr-2" />
          Discard
        </Button>
      </div>
    </div>
  );
}

// ============================================
// Refinement Dialog
// ============================================

function RefinementDialog({ open, onClose, runId, currentVersion, onSuccess }: RefinementDialogProps) {
  const [prompt, setPrompt] = useState("");
  const [proposal, setProposal] = useState<RefinementProposal | null>(null);
  const [editedText, setEditedText] = useState<string | null>(null);

  const proposeMutation = useProposeRefinement();
  const mergeMutation = useMergeRefinement();

  const handlePropose = async () => {
    if (!prompt.trim()) return;

    try {
      const result = await proposeMutation.mutateAsync({ runId, prompt });
      setProposal(result.proposal);
    } catch (error) {
      console.error("Failed to propose refinement:", error);
    }
  };

  const handleAccept = async () => {
    if (!proposal) return;

    try {
      const action = editedText ? "edit" : "merge";
      await mergeMutation.mutateAsync({
        runId,
        proposal,
        action,
        editedText: editedText || undefined,
      });
      onSuccess();
      handleClose();
    } catch (error) {
      console.error("Failed to merge refinement:", error);
    }
  };

  const handleReject = async () => {
    if (!proposal) return;

    try {
      await mergeMutation.mutateAsync({
        runId,
        proposal,
        action: "discard",
      });
      setProposal(null);
      setEditedText(null);
    } catch (error) {
      console.error("Failed to discard refinement:", error);
    }
  };

  const handleEdit = (text: string) => {
    setEditedText(text);
  };

  const handleClose = () => {
    setPrompt("");
    setProposal(null);
    setEditedText(null);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-yellow-500" />
            AI-Powered Refinement
          </DialogTitle>
          <DialogDescription>
            Refining Version {currentVersion}. Describe what changes you'd like to make.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {!proposal ? (
            <>
              <div>
                <Label htmlFor="refinement-prompt" className="text-sm font-medium mb-2 block">
                  What would you like to change?
                </Label>
                <Textarea
                  id="refinement-prompt"
                  placeholder="e.g., Expand on the environmental risk section with more detail about water use licenses..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="min-h-[120px]"
                />
              </div>

              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                <h4 className="text-xs font-semibold text-muted-foreground mb-2">
                  Example refinement prompts:
                </h4>
                <ul className="text-xs text-muted-foreground space-y-1">
                  <li>• "Add more detail about the change of control cascade risk"</li>
                  <li>• "Strengthen the recommendation around BEE compliance"</li>
                  <li>• "Remove the reference to outdated mining regulations"</li>
                  <li>• "Clarify the financial exposure calculation for Eskom contract"</li>
                </ul>
              </div>
            </>
          ) : (
            <ProposalReview
              proposal={proposal}
              onAccept={handleAccept}
              onReject={handleReject}
              onEdit={handleEdit}
              isSubmitting={mergeMutation.isPending}
            />
          )}
        </div>

        <DialogFooter>
          {!proposal ? (
            <>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                onClick={handlePropose}
                disabled={!prompt.trim() || proposeMutation.isPending}
                className="bg-alchemyPrimaryOrange hover:bg-alchemyPrimaryOrange/90"
              >
                {proposeMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate Proposal
                  </>
                )}
              </Button>
            </>
          ) : (
            <Button variant="outline" onClick={handleClose}>
              Close
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============================================
// Main Component
// ============================================

export function ReportVersionManager({
  runId,
  ddId,
  projectName,
  onVersionChange,
  className = "",
}: ReportVersionManagerProps) {
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [showRefinement, setShowRefinement] = useState(false);
  const [compareVersions, setCompareVersions] = useState<{ v1: number; v2: number } | null>(null);

  // Fetch versions
  const { data: versionsData, isLoading, refetch } = useReportVersions(runId);
  const downloadMutation = useDownloadVersion();

  const versions = versionsData?.versions || [];
  const currentVersionObj = versions.find((v) => v.is_current);
  const currentVersion = selectedVersion || currentVersionObj?.version || null;

  // Initialize selected version to current
  React.useEffect(() => {
    if (currentVersionObj && !selectedVersion) {
      setSelectedVersion(currentVersionObj.version);
    }
  }, [currentVersionObj, selectedVersion]);

  const handleVersionSelect = useCallback((version: number) => {
    setSelectedVersion(version);
    onVersionChange?.(version);
  }, [onVersionChange]);

  const handleCompare = useCallback((v1: number, v2: number) => {
    setCompareVersions({ v1, v2 });
    setShowCompare(true);
  }, []);

  const handleDownload = useCallback(() => {
    if (currentVersion) {
      const filename = `${projectName || "dd-report"}-v${currentVersion}.json`;
      downloadMutation.mutate({ runId, version: currentVersion, filename });
    }
  }, [runId, currentVersion, projectName, downloadMutation]);

  const handleOpenInNewTab = useCallback(() => {
    // Create a new window with the report content
    // This could be enhanced to open a dedicated report view page
    const url = `/dd/${ddId}/report?version=${currentVersion}`;
    window.open(url, "_blank");
  }, [ddId, currentVersion]);

  const handleRefinementSuccess = useCallback(() => {
    refetch();
  }, [refetch]);

  return (
    <TooltipProvider>
      <div className={`space-y-4 ${className}`}>
        {/* Header with Version Selector */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <FileText className="h-5 w-5 text-muted-foreground" />
            <h3 className="text-sm font-semibold">Report Version</h3>
            <VersionSelector
              versions={versions}
              selectedVersion={currentVersion}
              onSelect={handleVersionSelect}
              isLoading={isLoading}
            />
          </div>

          <div className="flex items-center gap-2">
            {/* Refresh */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => refetch()}
                  className="h-8 w-8"
                >
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Refresh versions</TooltipContent>
            </Tooltip>

            {/* History Toggle */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant={showHistory ? "default" : "ghost"}
                  size="icon"
                  onClick={() => setShowHistory(!showHistory)}
                  className="h-8 w-8"
                >
                  <History className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Version history</TooltipContent>
            </Tooltip>

            {/* AI Refinement */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowRefinement(true)}
                  className="h-8 w-8"
                  disabled={!currentVersion}
                >
                  <Sparkles className="h-4 w-4 text-yellow-500" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>AI refinement</TooltipContent>
            </Tooltip>

            {/* Download */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleDownload}
                  className="h-8 w-8"
                  disabled={!currentVersion || downloadMutation.isPending}
                >
                  {downloadMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Download version</TooltipContent>
            </Tooltip>

            {/* Open in new tab */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleOpenInNewTab}
                  className="h-8 w-8"
                  disabled={!currentVersion}
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Open in new tab</TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Version Info Summary */}
        {currentVersionObj && (
          <div className="text-xs text-muted-foreground flex items-center gap-4 flex-wrap">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDate(currentVersionObj.created_at)}
            </span>
            {currentVersionObj.created_by && (
              <span className="flex items-center gap-1">
                <User className="h-3 w-3" />
                {currentVersionObj.created_by}
              </span>
            )}
            {currentVersionObj.change_summary && (
              <span className="flex items-center gap-1 max-w-[300px] truncate">
                <Edit3 className="h-3 w-3" />
                {currentVersionObj.change_summary}
              </span>
            )}
          </div>
        )}

        {/* Version History Panel (Collapsible) */}
        {showHistory && versions.length > 0 && (
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <VersionHistory
              versions={versions}
              currentVersion={currentVersion}
              onSelect={handleVersionSelect}
              onCompare={handleCompare}
            />
          </div>
        )}

        {/* Compare Dialog */}
        {showCompare && compareVersions && (
          <CompareDialog
            open={showCompare}
            onClose={() => {
              setShowCompare(false);
              setCompareVersions(null);
            }}
            runId={runId}
            version1={compareVersions.v1}
            version2={compareVersions.v2}
          />
        )}

        {/* Refinement Dialog */}
        {showRefinement && currentVersion && (
          <RefinementDialog
            open={showRefinement}
            onClose={() => setShowRefinement(false)}
            runId={runId}
            currentVersion={currentVersion}
            onSuccess={handleRefinementSuccess}
          />
        )}
      </div>
    </TooltipProvider>
  );
}

export default ReportVersionManager;
