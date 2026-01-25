// File: ui/src/pages/DD/Processing/ClassificationProgressModal.tsx
/**
 * Classification Progress Modal - Checkpoint A Phase 1 & 2
 *
 * Phase 1: Shows classification progress with spinner and progress bar
 * Phase 2: Shows classification results with issues or success summary
 */

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Check,
  Loader2,
  AlertTriangle,
  FolderOpen,
  FileText,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import {
  useOrganisationProgress,
  useCancelOrganisation,
  OrganisationProgress,
} from "@/hooks/useOrganisationProgress";
import {
  useBlueprintRequirements,
  BlueprintRequirements,
  FOLDER_CATEGORIES,
  getRelevanceColor,
} from "@/hooks/useBlueprintRequirements";

interface ClassificationProgressModalProps {
  open: boolean;
  ddId: string | null;
  transactionType: string | undefined;
  onComplete: () => void;
  onReviewDocuments: () => void;
  onCancel?: () => void;
}

type ModalPhase = "classifying" | "complete" | "issues" | "cancelled";

export function ClassificationProgressModal({
  open,
  ddId,
  transactionType,
  onComplete,
  onReviewDocuments,
  onCancel,
}: ClassificationProgressModalProps) {
  const [phase, setPhase] = useState<ModalPhase>("classifying");
  const cancelOrganisation = useCancelOrganisation();

  // Poll organisation progress
  const { data: progress, isLoading: progressLoading } = useOrganisationProgress(
    ddId ?? undefined,
    open
  );

  // Fetch blueprint requirements when classification is done
  const { data: requirements } = useBlueprintRequirements(
    transactionType,
    ddId,
    progress?.status === "classified" || progress?.status === "organised"
  );

  // Determine phase based on progress status
  useEffect(() => {
    if (!progress) return;

    if (progress.status === "classifying" || progress.status === "pending") {
      setPhase("classifying");
    } else if (progress.status === "cancelled") {
      setPhase("cancelled");
    } else if (
      progress.status === "classified" ||
      progress.status === "organised" ||
      progress.status === "completed"
    ) {
      // Check if there are issues
      const hasIssues =
        (progress.lowConfidenceCount > 0) ||
        (progress.categoryCounts?.["99_Needs_Review"] || 0) > 0 ||
        (requirements?.summary?.total_missing || 0) > 0;

      setPhase(hasIssues ? "issues" : "complete");
    } else if (progress.status === "failed") {
      setPhase("issues");
    }
  }, [progress, requirements]);

  // Handle cancel
  const handleCancel = () => {
    if (ddId) {
      cancelOrganisation.mutate(ddId, {
        onSuccess: () => {
          onCancel?.();
        },
      });
    }
  };

  if (!open || !ddId) return null;

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent
        className="max-w-2xl"
        onPointerDownOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        {phase === "classifying" && (
          <ClassifyingPhase
            progress={progress}
            isLoading={progressLoading}
            onCancel={handleCancel}
            isCancelling={cancelOrganisation.isPending}
          />
        )}
        {phase === "cancelled" && (
          <CancelledPhase onClose={onCancel} />
        )}
        {phase === "complete" && (
          <CompletePhase
            progress={progress}
            requirements={requirements}
            onContinue={onComplete}
          />
        )}
        {phase === "issues" && (
          <IssuesPhase
            progress={progress}
            requirements={requirements}
            onReviewDocuments={onReviewDocuments}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

// Phase 1: Classification In Progress
function ClassifyingPhase({
  progress,
  isLoading,
  onCancel,
  isCancelling,
}: {
  progress: OrganisationProgress | undefined;
  isLoading: boolean;
  onCancel?: () => void;
  isCancelling?: boolean;
}) {
  const percent = progress?.percentComplete || 0;
  const classified = progress?.classifiedCount || 0;
  const total = progress?.totalDocuments || 0;

  return (
    <>
      <DialogHeader>
        <DialogTitle>Document Classification</DialogTitle>
        <DialogDescription>
          Please wait while your documents are automatically classified into
          their category folders.
        </DialogDescription>
      </DialogHeader>

      <div className="flex flex-col items-center py-8 space-y-6">
        <Loader2 className="h-16 w-16 text-blue-600 animate-spin" />

        <div className="w-full space-y-2">
          <Progress value={percent} className="h-3" />
          <p className="text-center text-sm text-muted-foreground">
            {isLoading ? (
              "Starting classification..."
            ) : (
              <>
                Classifying: {classified} of {total} documents...
              </>
            )}
          </p>
        </div>

        <p className="text-sm text-muted-foreground text-center max-w-md">
          This process typically takes 1-2 minutes depending on the number of
          documents.
        </p>

        {onCancel && (
          <Button
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={isCancelling}
            className="text-red-600 border-red-300 hover:bg-red-50"
          >
            {isCancelling ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Cancelling...
              </>
            ) : (
              "Cancel Classification"
            )}
          </Button>
        )}
      </div>
    </>
  );
}

// Phase: Classification Cancelled
function CancelledPhase({ onClose }: { onClose?: () => void }) {
  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <XCircle className="h-6 w-6 text-amber-500" />
          Classification Cancelled
        </DialogTitle>
      </DialogHeader>

      <div className="space-y-6 py-4">
        <div className="flex items-center gap-2 text-amber-700 bg-amber-50 p-3 rounded-lg">
          <AlertTriangle className="h-5 w-5" />
          <span>Document classification was cancelled.</span>
        </div>

        <p className="text-sm text-muted-foreground">
          You can restart classification at any time using the Classify button
          in the control bar.
        </p>

        <div className="flex justify-end">
          <Button onClick={onClose} variant="outline">
            Close
          </Button>
        </div>
      </div>
    </>
  );
}

// Phase 2: Classification Complete - No Issues
function CompletePhase({
  progress,
  requirements,
  onContinue,
}: {
  progress: OrganisationProgress | undefined;
  requirements: BlueprintRequirements | undefined;
  onContinue: () => void;
}) {
  const total = progress?.totalDocuments || 0;
  const categoryCounts = progress?.categoryCounts || {};

  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <CheckCircle2 className="h-6 w-6 text-green-600" />
          Classification Complete
        </DialogTitle>
      </DialogHeader>

      <div className="space-y-6 py-4">
        <div className="flex items-center gap-2 text-green-700 bg-green-50 p-3 rounded-lg">
          <Check className="h-5 w-5" />
          <span className="font-medium">
            All {total} documents successfully classified
          </span>
        </div>

        <div className="border-t pt-4">
          <p className="text-sm text-muted-foreground mb-3">
            Your documents have been organised into the following category
            folders:
          </p>

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {FOLDER_CATEGORIES.filter(
              (cat) =>
                cat.code !== "99_Needs_Review" &&
                (categoryCounts[cat.code] || 0) > 0
            ).map((cat) => (
              <div
                key={cat.code}
                className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded"
              >
                <div className="flex items-center gap-2">
                  <FolderOpen className="h-4 w-4 text-amber-600" />
                  <span className="text-sm font-medium">{cat.name}</span>
                </div>
                <Badge variant="secondary">
                  {categoryCounts[cat.code] || 0} documents
                </Badge>
              </div>
            ))}
          </div>
        </div>

        <div className="border-t pt-4 text-sm text-muted-foreground">
          <p>
            Please review the folder structure and confirm documents are
            correctly categorised. You can manually move any mis-classified
            documents by dragging them to the correct folder.
          </p>
          <p className="mt-2">
            When ready, click the <strong>Readability Check</strong> button to
            validate document formats and proceed to the next stage.
          </p>
        </div>

        <div className="flex justify-end">
          <Button onClick={onContinue} className="bg-blue-600 hover:bg-blue-700">
            Continue to Review
          </Button>
        </div>
      </div>
    </>
  );
}

// Phase 2: Classification Complete - Issues Found
function IssuesPhase({
  progress,
  requirements,
  onReviewDocuments,
}: {
  progress: OrganisationProgress | undefined;
  requirements: BlueprintRequirements | undefined;
  onReviewDocuments: () => void;
}) {
  const total = progress?.totalDocuments || 0;
  const classified = progress?.classifiedCount || 0;
  const failed = progress?.failedCount || 0;
  const needsReview = progress?.categoryCounts?.["99_Needs_Review"] || 0;
  const lowConfidence = progress?.lowConfidenceCount || 0;

  const missingDocs = requirements?.summary?.total_missing || 0;
  const missingCritical: string[] = [];
  const missingHigh: string[] = [];
  const missingOther: string[] = [];

  // Categorize missing documents by relevance
  if (requirements?.requirements) {
    for (const [category, req] of Object.entries(requirements.requirements)) {
      if (category === "99_Needs_Review") continue;

      for (const missing of req.missing_documents) {
        if (req.relevance === "critical") {
          missingCritical.push(missing);
        } else if (req.relevance === "high") {
          missingHigh.push(missing);
        } else {
          missingOther.push(missing);
        }
      }
    }
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <AlertTriangle className="h-6 w-6 text-amber-500" />
          Classification Complete
        </DialogTitle>
      </DialogHeader>

      <div className="space-y-6 py-4">
        <div className="flex items-center gap-2 text-green-700 bg-green-50 p-3 rounded-lg">
          <Check className="h-5 w-5" />
          <span>{classified} documents successfully classified</span>
        </div>

        {/* Action Required Section */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-4">
          <div className="flex items-center gap-2 text-amber-800 font-medium">
            <AlertTriangle className="h-5 w-5" />
            ACTION REQUIRED
          </div>

          {/* Missing Documents */}
          {missingDocs > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-amber-900">
                Missing Documents ({missingDocs})
              </p>
              <p className="text-sm text-amber-800">
                The following documents are typically required for this
                transaction type but were not found:
              </p>
              <ul className="text-sm space-y-1 ml-4">
                {missingCritical.slice(0, 3).map((doc) => (
                  <li key={doc} className="flex items-center gap-2">
                    <XCircle className="h-3 w-3 text-red-600" />
                    <span>{doc}</span>
                    <Badge
                      variant="outline"
                      className="text-xs bg-red-50 text-red-700 border-red-200"
                    >
                      Critical
                    </Badge>
                  </li>
                ))}
                {missingHigh.slice(0, 3).map((doc) => (
                  <li key={doc} className="flex items-center gap-2">
                    <XCircle className="h-3 w-3 text-orange-600" />
                    <span>{doc}</span>
                    <Badge
                      variant="outline"
                      className="text-xs bg-orange-50 text-orange-700 border-orange-200"
                    >
                      High
                    </Badge>
                  </li>
                ))}
                {missingOther.slice(0, 2).map((doc) => (
                  <li key={doc} className="flex items-center gap-2">
                    <XCircle className="h-3 w-3 text-gray-500" />
                    <span>{doc}</span>
                    <Badge
                      variant="outline"
                      className="text-xs bg-gray-50 text-gray-600 border-gray-200"
                    >
                      Medium
                    </Badge>
                  </li>
                ))}
                {missingCritical.length + missingHigh.length + missingOther.length > 8 && (
                  <li className="text-muted-foreground">
                    ... and {missingCritical.length + missingHigh.length + missingOther.length - 8} more
                  </li>
                )}
              </ul>
            </div>
          )}

          {/* Unclassified Documents */}
          {needsReview > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-amber-900">
                Unclassified Documents ({needsReview})
              </p>
              <p className="text-sm text-amber-800">
                These documents require manual classification before you can
                proceed:
              </p>
              {requirements?.requirements?.["99_Needs_Review"]?.found_documents
                ?.slice(0, 5)
                .map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-2 text-sm ml-4"
                  >
                    <FileText className="h-3 w-3 text-amber-600" />
                    <span className="truncate">{doc.filename}</span>
                  </div>
                ))}
              {needsReview > 5 && (
                <p className="text-sm text-muted-foreground ml-4">
                  ... and {needsReview - 5} more
                </p>
              )}
            </div>
          )}

          {/* Classification Failures */}
          {failed > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-amber-900">
                Classification Errors ({failed})
              </p>
              <p className="text-sm text-amber-800">
                Some documents could not be classified due to errors.
              </p>
            </div>
          )}

          {/* Low Confidence */}
          {lowConfidence > 0 && needsReview === 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-amber-900">
                Low Confidence Classifications ({lowConfidence})
              </p>
              <p className="text-sm text-amber-800">
                Some documents were classified with low confidence and should be
                reviewed.
              </p>
            </div>
          )}
        </div>

        <div className="text-sm text-muted-foreground">
          Please resolve these issues in the Documents panel before proceeding
          to the Readability Check.
        </div>

        <div className="flex justify-end">
          <Button
            onClick={onReviewDocuments}
            className="bg-blue-600 hover:bg-blue-700"
          >
            Review Documents
          </Button>
        </div>
      </div>
    </>
  );
}

export default ClassificationProgressModal;
