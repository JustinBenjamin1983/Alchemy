import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  UploadCloud,
  File,
  FileText,
  FileSpreadsheet,
  FileImage,
  X,
  Check,
  Loader2,
  RefreshCw,
  FolderOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useMutateClassifyDocument, ClassifyDocumentResponse } from "@/hooks/useMutateClassifyDocument";
import { useGetDocumentRegistry } from "@/hooks/useGetDocumentRegistry";
import { TransactionTypeCode } from "../Wizard/types";

interface UploadedFile {
  id: string;
  file: File;
  status: "pending" | "uploading" | "classifying" | "complete" | "error";
  progress: number;
  classification: ClassifyDocumentResponse | null;
  error?: string;
}

interface DocumentUploadWithClassificationProps {
  projectId: string;
  transactionType: TransactionTypeCode;
  onUploadComplete?: (files: UploadedFile[]) => void;
}

function getFileIcon(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "pdf":
      return <FileText className="h-5 w-5 text-red-500" />;
    case "doc":
    case "docx":
      return <FileText className="h-5 w-5 text-blue-500" />;
    case "xls":
    case "xlsx":
      return <FileSpreadsheet className="h-5 w-5 text-green-500" />;
    case "png":
    case "jpg":
    case "jpeg":
      return <FileImage className="h-5 w-5 text-purple-500" />;
    default:
      return <File className="h-5 w-5 text-gray-500" />;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.7) return "bg-green-100 text-green-800";
  if (confidence >= 0.4) return "bg-yellow-100 text-yellow-800";
  return "bg-gray-100 text-gray-600";
}

export function DocumentUploadWithClassification({
  projectId,
  transactionType,
  onUploadComplete,
}: DocumentUploadWithClassificationProps) {
  const [uploads, setUploads] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [reclassifyFile, setReclassifyFile] = useState<UploadedFile | null>(null);
  const [selectedFolder, setSelectedFolder] = useState<string>("");

  const classifyMutation = useMutateClassifyDocument();
  const { data: registry } = useGetDocumentRegistry(transactionType);

  const generateId = () => Math.random().toString(36).substr(2, 9);

  const updateUpload = (id: string, updates: Partial<UploadedFile>) => {
    setUploads((prev) =>
      prev.map((u) => (u.id === id ? { ...u, ...updates } : u))
    );
  };

  const processFile = async (upload: UploadedFile) => {
    updateUpload(upload.id, { status: "uploading", progress: 30 });

    // Simulate upload delay
    await new Promise((resolve) => setTimeout(resolve, 500));
    updateUpload(upload.id, { progress: 60 });

    // Classify the document
    updateUpload(upload.id, { status: "classifying", progress: 80 });

    try {
      const classification = await classifyMutation.mutateAsync({
        filename: upload.file.name,
        content_preview: "", // TODO: Extract text preview from file
        transaction_type: transactionType,
      });

      updateUpload(upload.id, {
        status: "complete",
        progress: 100,
        classification,
      });
    } catch (error) {
      updateUpload(upload.id, {
        status: "error",
        error: "Classification failed",
      });
    }
  };

  const handleFilesSelected = useCallback(
    async (files: FileList | File[]) => {
      const fileArray = Array.from(files);

      // Create upload entries
      const newUploads: UploadedFile[] = fileArray.map((file) => ({
        id: generateId(),
        file,
        status: "pending" as const,
        progress: 0,
        classification: null,
      }));

      setUploads((prev) => [...prev, ...newUploads]);

      // Process each file
      for (const upload of newUploads) {
        await processFile(upload);
      }

      // Notify parent
      if (onUploadComplete) {
        setUploads((current) => {
          onUploadComplete(current);
          return current;
        });
      }
    },
    [transactionType, onUploadComplete]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const { files } = e.dataTransfer;
      if (files.length > 0) {
        handleFilesSelected(files);
      }
    },
    [handleFilesSelected]
  );

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFilesSelected(e.target.files);
    }
  };

  const removeUpload = (id: string) => {
    setUploads((prev) => prev.filter((u) => u.id !== id));
  };

  const handleReclassify = (upload: UploadedFile) => {
    setReclassifyFile(upload);
    setSelectedFolder(upload.classification?.folder || "");
  };

  const confirmReclassify = () => {
    if (reclassifyFile && selectedFolder) {
      updateUpload(reclassifyFile.id, {
        classification: {
          ...reclassifyFile.classification!,
          folder: selectedFolder,
          confidence: 1.0, // Manual selection = 100% confidence
        },
      });
    }
    setReclassifyFile(null);
    setSelectedFolder("");
  };

  // Get unique folders from registry
  const availableFolders = registry?.documents
    .map((d) => d.folder)
    .filter((v, i, a) => a.indexOf(v) === i)
    .sort() || [];

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all",
          isDragging
            ? "border-alchemyPrimaryOrange bg-orange-50"
            : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <UploadCloud
          className={cn(
            "mx-auto h-12 w-12 mb-4",
            isDragging ? "text-alchemyPrimaryOrange" : "text-gray-400"
          )}
        />
        <p className="font-medium">
          <span className="underline">Click to upload</span> or drag and drop
        </p>
        <p className="text-sm text-muted-foreground mt-1">
          PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
        </p>
        <input
          id="file-input"
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt"
          className="hidden"
          onChange={handleFileInputChange}
        />
      </div>

      {/* Upload Progress & Classification Results */}
      {uploads.length > 0 && (
        <div className="space-y-2">
          {uploads.map((upload) => (
            <div
              key={upload.id}
              className="flex items-center gap-4 p-3 bg-white border rounded-lg"
            >
              {/* File icon */}
              {getFileIcon(upload.file.name)}

              {/* File info */}
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate">{upload.file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(upload.file.size)}
                </p>
                {upload.status !== "complete" && upload.status !== "error" && (
                  <Progress value={upload.progress} className="h-1 mt-1" />
                )}
              </div>

              {/* Status / Classification */}
              {upload.status === "uploading" && (
                <span className="text-sm text-blue-600 flex items-center gap-1">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Uploading...
                </span>
              )}
              {upload.status === "classifying" && (
                <span className="text-sm text-blue-600 flex items-center gap-1">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Classifying...
                </span>
              )}
              {upload.status === "complete" && upload.classification && (
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge
                    className={getConfidenceColor(upload.classification.confidence)}
                  >
                    {upload.classification.category}
                  </Badge>
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <FolderOpen className="h-3 w-3" />
                    {upload.classification.folder}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 text-xs"
                    onClick={() => handleReclassify(upload)}
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Change
                  </Button>
                </div>
              )}
              {upload.status === "error" && (
                <Badge variant="destructive">{upload.error || "Error"}</Badge>
              )}

              {/* Remove button */}
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8"
                onClick={() => removeUpload(upload.id)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Summary */}
      {uploads.length > 0 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            {uploads.filter((u) => u.status === "complete").length} of{" "}
            {uploads.length} files classified
          </span>
          {uploads.every((u) => u.status === "complete") && (
            <span className="text-green-600 flex items-center gap-1">
              <Check className="h-4 w-4" />
              All files ready
            </span>
          )}
        </div>
      )}

      {/* Reclassify Dialog */}
      <Dialog open={!!reclassifyFile} onOpenChange={() => setReclassifyFile(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change Document Classification</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm mb-4">
              Select the correct folder for:{" "}
              <span className="font-medium">{reclassifyFile?.file.name}</span>
            </p>
            <Select value={selectedFolder} onValueChange={setSelectedFolder}>
              <SelectTrigger className="bg-white">
                <SelectValue placeholder="Select folder" />
              </SelectTrigger>
              <SelectContent className="bg-white max-h-[300px]">
                {availableFolders.map((folder) => (
                  <SelectItem key={folder} value={folder}>
                    {folder}
                  </SelectItem>
                ))}
                <SelectItem value="99. Other Documents">
                  99. Other Documents
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReclassifyFile(null)}>
              Cancel
            </Button>
            <Button
              onClick={confirmReclassify}
              disabled={!selectedFolder}
              className="bg-alchemyPrimaryOrange hover:bg-alchemyPrimaryOrange/90"
            >
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default DocumentUploadWithClassification;
