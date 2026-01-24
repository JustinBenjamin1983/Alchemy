// File: ui/src/pages/DD/Processing/CheckpointADocListing.tsx
/**
 * Enhanced Document Listing for Checkpoint A
 *
 * Shows folder structure with inline blueprint requirements.
 * Displays expected documents per folder with MISSING indicators.
 * Allows moving unclassified documents from 99_Needs_Review.
 */

import { useEffect, useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileText,
  FolderOpen,
  Loader2,
  RefreshCw,
  Upload,
  XCircle,
} from "lucide-react";
import {
  useBlueprintRequirements,
  CategoryRequirements,
  FOLDER_CATEGORIES,
  getRelevanceColor,
  getRelevanceBadge,
} from "@/hooks/useBlueprintRequirements";
import {
  useDocumentReassign,
  useClassifyDocuments,
} from "@/hooks/useOrganisationProgress";
import { useGetDD } from "@/hooks/useGetDD";

interface CheckpointADocListingProps {
  ddId: string;
  transactionType: string;
  onReadabilityCheck: () => void;
}

export function CheckpointADocListing({
  ddId,
  transactionType,
  onReadabilityCheck,
}: CheckpointADocListingProps) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(
    new Set(["99_Needs_Review"])
  );

  // Fetch blueprint requirements with document matching
  const {
    data: requirements,
    isLoading: requirementsLoading,
    refetch: refetchRequirements,
  } = useBlueprintRequirements(transactionType, ddId);

  // Fetch DD data for folders
  const { data: dd, refetch: refetchDD } = useGetDD(ddId);

  // Document reassignment mutation
  const reassignDocument = useDocumentReassign();

  // Re-classify documents mutation
  const classifyDocuments = useClassifyDocuments();

  const toggleFolder = (code: string) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(code)) {
      newExpanded.delete(code);
    } else {
      newExpanded.add(code);
    }
    setExpandedFolders(newExpanded);
  };

  // Check if 99_Needs_Review is empty
  const needsReviewCount =
    requirements?.requirements?.["99_Needs_Review"]?.document_count || 0;
  const canProceedToReadability = needsReviewCount === 0;

  // Calculate overall progress
  const completionProgress = useMemo(() => {
    if (!requirements) return 0;
    const summary = requirements.summary;
    if (summary.total_expected === 0) return 100;
    return Math.round(
      ((summary.total_found - summary.needs_review_count) /
        Math.max(summary.total_expected, 1)) *
        100
    );
  }, [requirements]);

  const handleReassign = async (
    documentId: string,
    targetCategory: string
  ) => {
    try {
      await reassignDocument.mutateAsync({
        ddId,
        documentId,
        targetCategory,
        reason: "User manual classification during Checkpoint A",
      });
      refetchRequirements();
      refetchDD();
    } catch (error) {
      console.error("Failed to reassign document:", error);
    }
  };

  const handleReclassifyAll = async () => {
    try {
      await classifyDocuments.mutateAsync({ ddId, reset: false });
      refetchRequirements();
      refetchDD();
    } catch (error) {
      console.error("Failed to reclassify documents:", error);
    }
  };

  if (requirementsLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin mr-3" />
        <span>Loading document requirements...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Progress Summary */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Document Review Progress</CardTitle>
            <Badge
              variant={canProceedToReadability ? "default" : "secondary"}
              className={
                canProceedToReadability
                  ? "bg-green-600"
                  : "bg-amber-100 text-amber-800"
              }
            >
              {canProceedToReadability ? (
                <>
                  <Check className="h-3 w-3 mr-1" />
                  Ready
                </>
              ) : (
                <>
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  Action Required
                </>
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Documents Classified</span>
              <span>{completionProgress}%</span>
            </div>
            <Progress value={completionProgress} className="h-2" />
          </div>

          <div className="grid grid-cols-4 gap-4 text-center text-sm">
            <div className="bg-gray-50 rounded p-2">
              <div className="font-semibold text-lg">
                {requirements?.summary?.total_found || 0}
              </div>
              <div className="text-muted-foreground">Classified</div>
            </div>
            <div className="bg-amber-50 rounded p-2">
              <div className="font-semibold text-lg text-amber-700">
                {requirements?.summary?.needs_review_count || 0}
              </div>
              <div className="text-muted-foreground">Need Review</div>
            </div>
            <div className="bg-red-50 rounded p-2">
              <div className="font-semibold text-lg text-red-700">
                {requirements?.summary?.total_missing || 0}
              </div>
              <div className="text-muted-foreground">Missing</div>
            </div>
            <div className="bg-green-50 rounded p-2">
              <div className="font-semibold text-lg text-green-700">
                {requirements?.summary?.categories_complete || 0}/
                {requirements?.summary?.total_categories || 0}
              </div>
              <div className="text-muted-foreground">Complete</div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                refetchRequirements();
                refetchDD();
              }}
            >
              <RefreshCw className="h-4 w-4 mr-1" />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={onReadabilityCheck}
              disabled={!canProceedToReadability}
              className={
                canProceedToReadability
                  ? "bg-green-600 hover:bg-green-700"
                  : ""
              }
            >
              {canProceedToReadability ? (
                <>
                  <Check className="h-4 w-4 mr-1" />
                  Run Readability Check
                </>
              ) : (
                <>
                  <AlertTriangle className="h-4 w-4 mr-1" />
                  Resolve Issues First
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 99_Needs_Review Section - Always at top if has documents */}
      {needsReviewCount > 0 && (
        <Card className="border-amber-300 bg-amber-50/50">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              <CardTitle className="text-lg text-amber-800">
                Documents Requiring Classification ({needsReviewCount})
              </CardTitle>
            </div>
            <p className="text-sm text-amber-700">
              These documents could not be automatically classified. Please
              assign them to the correct folder or re-classify with AI.
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {requirements?.requirements?.["99_Needs_Review"]?.found_documents?.map(
                (doc) => (
                  <UnclassifiedDocumentRow
                    key={doc.id}
                    document={doc}
                    categories={FOLDER_CATEGORIES.filter(
                      (c) => c.code !== "99_Needs_Review"
                    )}
                    onReassign={handleReassign}
                    isReassigning={reassignDocument.isPending}
                  />
                )
              )}
            </div>
            <div className="flex justify-end mt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={handleReclassifyAll}
                disabled={classifyDocuments.isPending}
              >
                {classifyDocuments.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    Re-classifying...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Re-classify All with AI
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Category Folders */}
      <div className="space-y-2">
        {FOLDER_CATEGORIES.filter((cat) => cat.code !== "99_Needs_Review").map(
          (cat) => {
            const req = requirements?.requirements?.[cat.code];
            if (!req) return null;

            const isExpanded = expandedFolders.has(cat.code);
            const hasDocuments = req.document_count > 0;
            const hasMissing = req.missing_documents.length > 0;

            return (
              <Collapsible
                key={cat.code}
                open={isExpanded}
                onOpenChange={() => toggleFolder(cat.code)}
              >
                <Card
                  className={`${
                    req.is_complete
                      ? "border-green-200"
                      : hasMissing
                      ? "border-amber-200"
                      : ""
                  }`}
                >
                  <CollapsibleTrigger asChild>
                    <CardHeader className="cursor-pointer hover:bg-gray-50 py-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                          <FolderOpen className="h-5 w-5 text-amber-600" />
                          <span className="font-medium">{cat.name}</span>
                          <Badge variant="secondary" className="ml-2">
                            {req.document_count} documents
                          </Badge>
                          {req.relevance !== "n/a" && (
                            <Badge
                              variant="outline"
                              className={`text-xs ${getRelevanceColor(
                                req.relevance
                              )}`}
                            >
                              {getRelevanceBadge(req.relevance)}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {req.is_complete ? (
                            <CheckCircle2 className="h-5 w-5 text-green-600" />
                          ) : hasMissing ? (
                            <Badge
                              variant="outline"
                              className="bg-amber-50 text-amber-700 border-amber-200"
                            >
                              {req.missing_documents.length} missing
                            </Badge>
                          ) : null}
                        </div>
                      </div>
                    </CardHeader>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <CardContent className="pt-0">
                      <CategoryFolderContent
                        requirements={req}
                        transactionType={transactionType}
                      />
                    </CardContent>
                  </CollapsibleContent>
                </Card>
              </Collapsible>
            );
          }
        )}
      </div>
    </div>
  );
}

// Content for an expanded category folder
function CategoryFolderContent({
  requirements,
  transactionType,
}: {
  requirements: CategoryRequirements;
  transactionType: string;
}) {
  return (
    <div className="space-y-4">
      {/* Expected Documents Section */}
      {requirements.expected_documents.length > 0 && (
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-sm font-medium mb-2">
            Expected for {transactionType.replace(/_/g, " ")}:
          </p>
          <div className="grid grid-cols-2 gap-2">
            {requirements.expected_documents.map((docType) => {
              const isFound = requirements.found_documents.some(
                (d) => d.matched_type === docType
              );
              const isMissing = requirements.missing_documents.includes(docType);

              return (
                <div
                  key={docType}
                  className={`flex items-center gap-2 text-sm p-1 rounded ${
                    isFound
                      ? "text-green-700"
                      : isMissing
                      ? "text-amber-700 bg-amber-50"
                      : ""
                  }`}
                >
                  {isFound ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-amber-500" />
                  )}
                  <span>{docType}</span>
                  {isMissing && (
                    <span className="text-xs text-amber-600 ml-auto">
                      (drag file here)
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Found Documents */}
      {requirements.found_documents.length > 0 && (
        <div>
          <p className="text-sm font-medium mb-2">Documents:</p>
          <div className="space-y-1">
            {requirements.found_documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-2 p-2 bg-white border rounded hover:bg-gray-50"
              >
                <FileText className="h-4 w-4 text-gray-400" />
                <span className="text-sm flex-1 truncate">{doc.filename}</span>
                {doc.confidence !== null && (
                  <Badge
                    variant="outline"
                    className={`text-xs ${
                      doc.confidence >= 80
                        ? "bg-green-50 text-green-700 border-green-200"
                        : doc.confidence >= 60
                        ? "bg-blue-50 text-blue-700 border-blue-200"
                        : "bg-amber-50 text-amber-700 border-amber-200"
                    }`}
                  >
                    {doc.confidence}%
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {requirements.found_documents.length === 0 && (
        <div className="text-center py-4 text-muted-foreground">
          <FolderOpen className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No documents in this folder yet</p>
          <p className="text-xs">
            Drag documents here or upload new ones
          </p>
        </div>
      )}
    </div>
  );
}

// Row for an unclassified document
function UnclassifiedDocumentRow({
  document,
  categories,
  onReassign,
  isReassigning,
}: {
  document: any;
  categories: Array<{ code: string; name: string }>;
  onReassign: (docId: string, category: string) => void;
  isReassigning: boolean;
}) {
  const [selectedCategory, setSelectedCategory] = useState<string>("");

  const handleMove = () => {
    if (selectedCategory) {
      onReassign(document.id, selectedCategory);
      setSelectedCategory("");
    }
  };

  return (
    <div className="flex items-center gap-3 p-3 bg-white border border-amber-200 rounded-lg">
      <FileText className="h-5 w-5 text-amber-600 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{document.filename}</p>
        {document.document_type && (
          <p className="text-xs text-muted-foreground">
            AI suggested: {document.document_type}
          </p>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Select value={selectedCategory} onValueChange={setSelectedCategory}>
          <SelectTrigger className="w-[180px] h-8 text-sm">
            <SelectValue placeholder="Move to folder..." />
          </SelectTrigger>
          <SelectContent>
            {categories.map((cat) => (
              <SelectItem key={cat.code} value={cat.code}>
                {cat.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          size="sm"
          variant="outline"
          onClick={handleMove}
          disabled={!selectedCategory || isReassigning}
        >
          {isReassigning ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "Move"
          )}
        </Button>
      </div>
    </div>
  );
}

export default CheckpointADocListing;
