// Create a new file: components/DocumentUploadReport.tsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, XCircle, FileText, Folder } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

interface Document {
  document_id: string;
  original_file_name: string;
  type: string;
  uploaded_at: string;
  processing_status: string;
  size_in_bytes: number;
  is_original: boolean;
}

interface Folder {
  folder_id: string;
  folder_name: string;
  level: number;
  hierarchy: string;
  documents: Document[];
}

interface DocumentUploadReportProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  ddData: {
    folders?: Folder[];
    name?: string;
  } | null;
}

export function DocumentUploadReport({
  open,
  onOpenChange,
  ddData,
}: DocumentUploadReportProps) {
  if (!ddData?.folders) return null;

  // Extract all documents with issues
  const allDocs = ddData.folders.flatMap(
    (folder) =>
      folder.documents?.map((doc) => ({
        ...doc,
        folder_name: folder.folder_name,
        folder_id: folder.folder_id,
      })) ?? []
  );

  const failedDocs = allDocs.filter(
    (doc) => doc.processing_status?.toLowerCase() === "failed"
  );

  const unsupportedDocs = allDocs.filter(
    (doc) => doc.processing_status?.toLowerCase() === "unsupported"
  );

  const completeDocs = allDocs.filter(
    (doc) => doc.processing_status?.toLowerCase() === "complete"
  );

  const inProgressDocs = allDocs.filter(
    (doc) => doc.processing_status?.toLowerCase() === "in progress"
  );

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "failed":
        return (
          <Badge variant="destructive" className="gap-1">
            <XCircle className="h-3 w-3" />
            Failed
          </Badge>
        );
      case "unsupported":
        return (
          <Badge
            variant="outline"
            className="gap-1 border-orange-500 text-orange-700 bg-orange-50"
          >
            <AlertTriangle className="h-3 w-3" />
            Unsupported
          </Badge>
        );
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Document Processing Report
          </DialogTitle>
          <DialogDescription>
            Detailed analysis of document processing for {ddData.name}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-green-600">
                  Complete
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{completeDocs.length}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-blue-600">
                  In Progress
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {inProgressDocs.length}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-orange-600">
                  Unsupported
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {unsupportedDocs.length}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-red-600">
                  Failed
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{failedDocs.length}</div>
              </CardContent>
            </Card>
          </div>

          {/* Failed Documents Section */}
          {failedDocs.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <XCircle className="h-5 w-5 text-red-500" />
                <h3 className="text-lg font-semibold text-red-600">
                  Failed Documents ({failedDocs.length})
                </h3>
              </div>
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>File Name</TableHead>
                        <TableHead>Folder</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Size</TableHead>
                        <TableHead>Uploaded</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {failedDocs.map((doc) => (
                        <TableRow key={doc.document_id}>
                          <TableCell className="font-medium break-words max-w-xs">
                            {doc.original_file_name}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <Folder className="h-4 w-4 text-gray-500" />
                              {doc.folder_name}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {doc.type.toUpperCase()}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {formatFileSize(doc.size_in_bytes)}
                          </TableCell>
                          <TableCell>{formatDate(doc.uploaded_at)}</TableCell>
                          <TableCell>
                            {getStatusBadge(doc.processing_status)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Unsupported Documents Section */}
          {unsupportedDocs.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-5 w-5 text-orange-500" />
                <h3 className="text-lg font-semibold text-orange-600">
                  Unsupported Documents ({unsupportedDocs.length})
                </h3>
              </div>
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>File Name</TableHead>
                        <TableHead>Folder</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Size</TableHead>
                        <TableHead>Uploaded</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {unsupportedDocs.map((doc) => (
                        <TableRow key={doc.document_id}>
                          <TableCell className="font-medium break-words max-w-xs">
                            {doc.original_file_name}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <Folder className="h-4 w-4 text-gray-500" />
                              {doc.folder_name}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {doc.type.toUpperCase()}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {formatFileSize(doc.size_in_bytes)}
                          </TableCell>
                          <TableCell>{formatDate(doc.uploaded_at)}</TableCell>
                          <TableCell>
                            {getStatusBadge(doc.processing_status)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              {/* Helpful info for unsupported files */}
              <div className="mt-3 p-3 bg-orange-50 border border-orange-200 rounded-md">
                <p className="text-sm text-orange-800">
                  <strong>Note:</strong> Currently supported file types are PDF
                  and DOCX. Unsupported files include images (PNG, JPG),
                  spreadsheets (XLSX), presentations (PPTX), and other formats.
                </p>
              </div>
            </div>
          )}

          {/* No Issues Message */}
          {failedDocs.length === 0 && unsupportedDocs.length === 0 && (
            <div className="text-center py-8">
              <div className="text-green-600 text-lg font-semibold mb-2">
                🎉 All documents processed successfully!
              </div>
              <p className="text-gray-600">
                No failed or unsupported documents found in this due diligence.
              </p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
