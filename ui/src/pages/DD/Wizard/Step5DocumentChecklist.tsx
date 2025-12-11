import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Download,
  Copy,
  ChevronDown,
  ChevronRight,
  Folder,
  FileText,
  Loader2,
  Upload,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { useGetDocumentRegistry, DocumentRegistryDocument } from "@/hooks/useGetDocumentRegistry";
import { useGetDocumentRequestList } from "@/hooks/useGetDocumentRequestList";
import { DDProjectSetup, TRANSACTION_TYPE_INFO } from "./types";

interface Step5Props {
  data: DDProjectSetup;
  onChange: (updates: Partial<DDProjectSetup>) => void;
}

type Priority = "critical" | "required" | "recommended" | "optional";

const PRIORITY_ORDER: Priority[] = ["critical", "required", "recommended", "optional"];

const PRIORITY_STYLES: Record<Priority, { badge: string; label: string }> = {
  critical: { badge: "bg-red-100 text-red-800", label: "CRITICAL" },
  required: { badge: "bg-orange-100 text-orange-800", label: "REQUIRED" },
  recommended: { badge: "bg-yellow-100 text-yellow-800", label: "RECOMMENDED" },
  optional: { badge: "bg-gray-100 text-gray-600", label: "OPTIONAL" },
};

function groupByCategory(documents: DocumentRegistryDocument[]) {
  return documents.reduce((acc, doc) => {
    const category = doc.category;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(doc);
    return acc;
  }, {} as Record<string, DocumentRegistryDocument[]>);
}

interface FolderTreeProps {
  folders: { name: string; subfolders?: { name: string }[] }[];
}

function FolderTree({ folders }: FolderTreeProps) {
  return (
    <div className="pl-4 space-y-1">
      {folders.map((folder) => (
        <div key={folder.name}>
          <div className="flex items-center gap-2 py-1">
            <Folder className="h-4 w-4 text-alchemyPrimaryGoldenWeb" />
            <span className="text-sm">{folder.name}</span>
          </div>
          {folder.subfolders && folder.subfolders.length > 0 && (
            <div className="pl-4">
              {folder.subfolders.map((sub) => (
                <div key={sub.name} className="flex items-center gap-2 py-1">
                  <Folder className="h-3 w-3 text-gray-400" />
                  <span className="text-xs text-muted-foreground">{sub.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

interface DocumentCategoryCardProps {
  category: string;
  documents: DocumentRegistryDocument[];
}

function DocumentCategoryCard({ category, documents }: DocumentCategoryCardProps) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-gray-50 py-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                {isOpen ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                {category}
              </CardTitle>
              <Badge variant="secondary">{documents.length} documents</Badge>
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="pt-0 pb-4">
            <div className="space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.name}
                  className="flex items-start gap-3 p-2 rounded hover:bg-gray-50"
                >
                  <FileText className="h-4 w-4 mt-1 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge
                        className={`text-xs ${PRIORITY_STYLES[doc.priority].badge}`}
                      >
                        {PRIORITY_STYLES[doc.priority].label}
                      </Badge>
                      <span className="font-medium text-sm">{doc.name}</span>
                    </div>
                    {doc.description && (
                      <p className="text-xs text-muted-foreground mt-1 italic">
                        {doc.description}
                      </p>
                    )}
                    {doc.request_template && (
                      <p className="text-xs text-gray-600 mt-1">
                        <span className="font-medium">Request:</span>{" "}
                        {doc.request_template}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      → {doc.folder}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

export function Step5DocumentChecklist({ data, onChange }: Step5Props) {
  const [priorityFilter, setPriorityFilter] = useState<Priority>("required");
  const [copiedToast, setCopiedToast] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: registry, isLoading, isError } = useGetDocumentRegistry(
    data.transactionType
  );

  const { data: requestList } = useGetDocumentRequestList(
    data.transactionType,
    priorityFilter
  );

  const handleFileSelect = (file: File) => {
    if (!file.name.endsWith(".zip")) {
      setUploadError("Only .zip files are supported. Please upload a valid ZIP file.");
      onChange({ uploadedFile: null });
      return;
    }
    setUploadError(null);
    onChange({ uploadedFile: file });
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  // Filter documents by priority (only if registry available)
  const filteredDocuments = registry?.documents
    ? registry.documents.filter(
        (doc) => PRIORITY_ORDER.indexOf(doc.priority) <= PRIORITY_ORDER.indexOf(priorityFilter)
      )
    : [];

  const groupedByCategory = groupByCategory(filteredDocuments);

  const copyRequestEmail = () => {
    if (requestList?.markdown) {
      navigator.clipboard.writeText(requestList.markdown);
      setCopiedToast(true);
      setTimeout(() => setCopiedToast(false), 2000);
    }
  };

  const downloadChecklist = () => {
    if (requestList?.markdown) {
      const blob = new Blob([requestList.markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dd-checklist-${data.transactionType}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="space-y-6">
      {/* File Upload Section - Always visible */}
      <Card className={`border-2 ${data.uploadedFile ? 'border-green-500 bg-green-50' : isDragging ? 'border-alchemyPrimaryOrange bg-orange-50' : 'border-dashed border-gray-300'}`}>
        <CardContent className="pt-6">
          <div
            className="flex flex-col items-center justify-center py-6 cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            {data.uploadedFile ? (
              <>
                <CheckCircle2 className="h-12 w-12 text-green-600 mb-3" />
                <p className="font-semibold text-green-700">File Ready for Upload</p>
                <p className="text-sm text-green-600 mt-1">{data.uploadedFile.name}</p>
                <p className="text-xs text-muted-foreground mt-2">
                  ({(data.uploadedFile.size / 1024 / 1024).toFixed(2)} MB)
                </p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2 text-gray-500"
                  onClick={(e) => {
                    e.stopPropagation();
                    onChange({ uploadedFile: null });
                  }}
                >
                  Change file
                </Button>
              </>
            ) : (
              <>
                <Upload className={`h-12 w-12 mb-3 ${isDragging ? 'text-alchemyPrimaryOrange' : 'text-gray-400'}`} />
                <p className="font-semibold">Upload Data Room Documents</p>
                <p className="text-sm text-muted-foreground mt-1">
                  <span className="text-alchemyPrimaryOrange underline">Click to browse</span> or drag & drop your ZIP file
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  ZIP file containing your due diligence documents
                </p>
              </>
            )}
            {uploadError && (
              <div className="flex items-center gap-2 mt-3 text-red-600">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm">{uploadError}</span>
              </div>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={handleFileInputChange}
          />
        </CardContent>
      </Card>

      {/* Document Checklist Section - Shows loading, error, or content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
          <span className="text-muted-foreground">Loading document checklist...</span>
        </div>
      ) : isError || !registry ? (
        <Card className="bg-gray-50">
          <CardContent className="pt-6">
            <div className="text-center py-4 text-muted-foreground">
              <AlertCircle className="h-8 w-8 mx-auto mb-2 text-gray-400" />
              <p className="font-medium">Document checklist unavailable</p>
              <p className="text-sm mt-1">
                {data.transactionType
                  ? "Unable to load the document checklist. You can still upload your files and proceed."
                  : "Please select a transaction type in Step 1 to see the document checklist."}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h2 className="text-xl font-semibold">Document Checklist</h2>
              <p className="text-sm text-muted-foreground">
                {filteredDocuments.length} documents expected for{" "}
                {TRANSACTION_TYPE_INFO[data.transactionType!]?.name || data.transactionType}{" "}
                transaction
              </p>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={downloadChecklist}>
                <Download className="h-4 w-4 mr-1" />
                Export List
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={copyRequestEmail}
                className="relative"
              >
                <Copy className="h-4 w-4 mr-1" />
                {copiedToast ? "Copied!" : "Copy Request Email"}
              </Button>
            </div>
          </div>

          {/* Priority Filter */}
          <ToggleGroup
            type="single"
            value={priorityFilter}
            onValueChange={(v) => v && setPriorityFilter(v as Priority)}
            className="justify-start"
          >
            <ToggleGroupItem value="critical" className="text-xs">
              Critical Only ({registry.priority_counts.critical})
            </ToggleGroupItem>
            <ToggleGroupItem value="required" className="text-xs">
              + Required ({registry.priority_counts.required})
            </ToggleGroupItem>
            <ToggleGroupItem value="recommended" className="text-xs">
              + Recommended ({registry.priority_counts.recommended})
            </ToggleGroupItem>
            <ToggleGroupItem value="optional" className="text-xs">
              All
            </ToggleGroupItem>
          </ToggleGroup>

          {/* Document List by Category */}
          <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
            {Object.entries(groupedByCategory)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([category, docs]) => (
                <DocumentCategoryCard
                  key={category}
                  category={category}
                  documents={docs}
                />
              ))}
          </div>

          {/* Folder Structure Preview */}
          {registry.folder_structure && registry.folder_structure.length > 0 && (
            <Collapsible>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" className="w-full justify-start">
                  <ChevronRight className="h-4 w-4 mr-2" />
                  View Data Room Folder Structure
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <Card className="mt-2">
                  <CardContent className="pt-4">
                    <FolderTree folders={registry.folder_structure} />
                  </CardContent>
                </Card>
              </CollapsibleContent>
            </Collapsible>
          )}
        </>
      )}
    </div>
  );
}
