import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
  AlertTriangle,
  PieChart,
  ChevronDown,
  ChevronRight,
  Copy,
  Download,
  FileText,
  Loader2,
} from "lucide-react";
import { useGetMissingDocuments, MissingDocument } from "@/hooks/useGetMissingDocuments";
import { useGetDocumentRequestList } from "@/hooks/useGetDocumentRequestList";
import { TransactionTypeCode } from "../Wizard/types";

interface MissingDocumentsTrackerProps {
  projectId: string;
  transactionType: TransactionTypeCode;
  uploadedDocuments: string[];
}

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  alert?: boolean;
}

function StatCard({ label, value, icon, alert }: StatCardProps) {
  return (
    <Card className={alert ? "border-red-200 bg-red-50" : ""}>
      <CardContent className="p-4 flex items-center gap-3">
        {icon}
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

interface MissingDocumentRowProps {
  document: MissingDocument;
  onCopyRequest: (text: string) => void;
}

function MissingDocumentRow({ document, onCopyRequest }: MissingDocumentRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const priorityStyles = {
    critical: "bg-red-100 text-red-800",
    required: "bg-orange-100 text-orange-800",
    recommended: "bg-yellow-100 text-yellow-800",
    optional: "bg-gray-100 text-gray-600",
  };

  return (
    <div className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
      <div className="flex items-start gap-3">
        <FileText className="h-4 w-4 mt-1 text-muted-foreground" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className={`text-xs ${priorityStyles[document.priority]}`}>
              {document.priority.toUpperCase()}
            </Badge>
            <span className="font-medium text-sm">{document.name}</span>
          </div>
          {document.description && (
            <p className="text-xs text-muted-foreground mt-1">
              {document.description}
            </p>
          )}
          <p className="text-xs text-gray-500 mt-1">
            Folder: {document.folder}
          </p>
        </div>
        {document.request_template && (
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-xs"
            onClick={() => onCopyRequest(document.request_template)}
          >
            <Copy className="h-3 w-3 mr-1" />
            Copy
          </Button>
        )}
      </div>
    </div>
  );
}

export function MissingDocumentsTracker({
  projectId,
  transactionType,
  uploadedDocuments,
}: MissingDocumentsTrackerProps) {
  const [priorityFilter, setPriorityFilter] = useState<
    "critical" | "required" | "recommended" | "optional"
  >("required");
  const [copiedToast, setCopiedToast] = useState(false);
  const [isListOpen, setIsListOpen] = useState(true);

  const { data: missingDocs, isLoading } = useGetMissingDocuments(
    transactionType,
    uploadedDocuments,
    priorityFilter
  );

  const { data: requestList } = useGetDocumentRequestList(
    transactionType,
    priorityFilter
  );

  // Categorize missing documents
  const criticalMissing = useMemo(
    () => missingDocs?.filter((d) => d.priority === "critical") || [],
    [missingDocs]
  );

  const requiredMissing = useMemo(
    () => missingDocs?.filter((d) => d.priority === "required") || [],
    [missingDocs]
  );

  const totalExpected = useMemo(() => {
    if (!missingDocs) return 0;
    return uploadedDocuments.length + missingDocs.length;
  }, [missingDocs, uploadedDocuments]);

  const coverage = useMemo(() => {
    if (totalExpected === 0) return 0;
    return Math.round((uploadedDocuments.length / totalExpected) * 100);
  }, [uploadedDocuments, totalExpected]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToast(true);
    setTimeout(() => setCopiedToast(false), 2000);
  };

  const generateRequestList = () => {
    if (requestList?.markdown) {
      const blob = new Blob([requestList.markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `missing-documents-${transactionType}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Document Status</h3>
        <Button
          variant="outline"
          size="sm"
          onClick={generateRequestList}
          disabled={!missingDocs?.length}
        >
          <Download className="h-4 w-4 mr-1" />
          Generate Request List
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Uploaded"
          value={uploadedDocuments.length}
          icon={<CheckCircle className="h-8 w-8 text-green-500" />}
        />
        <StatCard
          label="Critical Missing"
          value={criticalMissing.length}
          icon={<AlertCircle className="h-8 w-8 text-red-500" />}
          alert={criticalMissing.length > 0}
        />
        <StatCard
          label="Required Missing"
          value={requiredMissing.length}
          icon={<AlertTriangle className="h-8 w-8 text-amber-500" />}
        />
        <StatCard
          label="Coverage"
          value={`${coverage}%`}
          icon={<PieChart className="h-8 w-8 text-blue-500" />}
        />
      </div>

      {/* Critical Missing Alert */}
      {criticalMissing.length > 0 && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Critical Documents Missing</AlertTitle>
          <AlertDescription>
            <ul className="mt-2 space-y-1">
              {criticalMissing.slice(0, 5).map((doc) => (
                <li key={doc.name} className="flex items-center gap-2">
                  <span>• {doc.name}</span>
                  {doc.request_template && (
                    <Button
                      size="sm"
                      variant="link"
                      className="h-auto p-0 text-xs"
                      onClick={() => copyToClipboard(doc.request_template)}
                    >
                      {copiedToast ? "Copied!" : "Copy request"}
                    </Button>
                  )}
                </li>
              ))}
              {criticalMissing.length > 5 && (
                <li className="text-muted-foreground">
                  ... and {criticalMissing.length - 5} more
                </li>
              )}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Priority Filter */}
      <div className="flex items-center gap-4">
        <span className="text-sm font-medium">Show priority:</span>
        <Select value={priorityFilter} onValueChange={(v: any) => setPriorityFilter(v)}>
          <SelectTrigger className="w-[200px] bg-white">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-white">
            <SelectItem value="critical">Critical only</SelectItem>
            <SelectItem value="required">Critical + Required</SelectItem>
            <SelectItem value="recommended">+ Recommended</SelectItem>
            <SelectItem value="optional">All</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Full Missing List */}
      <Collapsible open={isListOpen} onOpenChange={setIsListOpen}>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" className="w-full justify-between">
            <span>
              All Missing Documents ({missingDocs?.length || 0})
            </span>
            {isListOpen ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="space-y-2 mt-2 max-h-[400px] overflow-y-auto pr-2">
            {missingDocs?.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <CheckCircle className="h-12 w-12 mx-auto mb-2 text-green-500" />
                <p>All expected documents have been uploaded!</p>
              </div>
            ) : (
              missingDocs?.map((doc) => (
                <MissingDocumentRow
                  key={doc.name}
                  document={doc}
                  onCopyRequest={copyToClipboard}
                />
              ))
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

export default MissingDocumentsTracker;
