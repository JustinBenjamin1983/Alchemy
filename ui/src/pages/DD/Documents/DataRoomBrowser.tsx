import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
  Folder,
  FolderOpen,
  FileText,
  File,
  FileSpreadsheet,
  Search,
  Upload,
  Move,
  Trash2,
  ChevronRight,
  MoreVertical,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useGetDocumentRegistry, FolderStructure } from "@/hooks/useGetDocumentRegistry";
import { TransactionTypeCode } from "../Wizard/types";

interface DataRoomDocument {
  id: string;
  name: string;
  folder: string;
  type: string;
  size: number;
  uploadedAt: Date;
  classification?: {
    category: string;
    confidence: number;
  };
}

interface DataRoomBrowserProps {
  projectId: string;
  transactionType: TransactionTypeCode;
  documents: DataRoomDocument[];
  onUploadClick?: () => void;
  onMoveDocuments?: (docIds: string[], targetFolder: string) => void;
  onDeleteDocuments?: (docIds: string[]) => void;
  onOpenDocument?: (docId: string) => void;
}

function getFileIcon(type: string) {
  switch (type.toLowerCase()) {
    case "pdf":
      return <FileText className="h-4 w-4 text-red-500" />;
    case "doc":
    case "docx":
      return <FileText className="h-4 w-4 text-blue-500" />;
    case "xls":
    case "xlsx":
      return <FileSpreadsheet className="h-4 w-4 text-green-500" />;
    default:
      return <File className="h-4 w-4 text-gray-500" />;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatDate(date: Date): string {
  return new Intl.DateTimeFormat("en-ZA", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

interface FolderTreeItemProps {
  folder: FolderStructure;
  path: string;
  currentPath: string;
  onNavigate: (path: string) => void;
  documentCounts: Record<string, number>;
  level?: number;
}

function FolderTreeItem({
  folder,
  path,
  currentPath,
  onNavigate,
  documentCounts,
  level = 0,
}: FolderTreeItemProps) {
  const [isExpanded, setIsExpanded] = useState(level < 2);
  const fullPath = path ? `${path}/${folder.name}` : folder.name;
  const isActive = currentPath === fullPath;
  const hasSubfolders = folder.subfolders && folder.subfolders.length > 0;
  const docCount = documentCounts[fullPath] || 0;

  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-1 py-1 px-2 rounded cursor-pointer text-sm",
          isActive ? "bg-alchemyPrimaryOrange/10 text-alchemyPrimaryOrange" : "hover:bg-gray-100"
        )}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={() => onNavigate(fullPath)}
      >
        {hasSubfolders && (
          <ChevronRight
            className={cn(
              "h-3 w-3 transition-transform cursor-pointer",
              isExpanded && "rotate-90"
            )}
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
          />
        )}
        {!hasSubfolders && <span className="w-3" />}
        {isActive ? (
          <FolderOpen className="h-4 w-4 text-alchemyPrimaryGoldenWeb" />
        ) : (
          <Folder className="h-4 w-4 text-gray-400" />
        )}
        <span className="flex-1 truncate">{folder.name}</span>
        {docCount > 0 && (
          <Badge variant="secondary" className="h-5 text-xs">
            {docCount}
          </Badge>
        )}
      </div>
      {hasSubfolders && isExpanded && (
        <div>
          {folder.subfolders!.map((sub) => (
            <FolderTreeItem
              key={sub.name}
              folder={sub}
              path={fullPath}
              currentPath={currentPath}
              onNavigate={onNavigate}
              documentCounts={documentCounts}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function DataRoomBrowser({
  projectId,
  transactionType,
  documents,
  onUploadClick,
  onMoveDocuments,
  onDeleteDocuments,
  onOpenDocument,
}: DataRoomBrowserProps) {
  const [currentPath, setCurrentPath] = useState("");
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  const { data: registry } = useGetDocumentRegistry(transactionType);

  // Calculate document counts per folder
  const documentCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    documents.forEach((doc) => {
      counts[doc.folder] = (counts[doc.folder] || 0) + 1;
    });
    return counts;
  }, [documents]);

  // Filter documents for current path
  const currentDocs = useMemo(() => {
    return documents.filter((doc) => {
      const inFolder = currentPath ? doc.folder.startsWith(currentPath) : true;
      const matchesSearch = searchQuery
        ? doc.name.toLowerCase().includes(searchQuery.toLowerCase())
        : true;

      // If we're in a folder, only show docs directly in that folder
      if (currentPath) {
        const relativePath = doc.folder.replace(currentPath, "").replace(/^\//, "");
        const isDirectChild = !relativePath || !relativePath.includes("/");
        return inFolder && isDirectChild && matchesSearch;
      }

      return inFolder && matchesSearch;
    });
  }, [documents, currentPath, searchQuery]);

  // Build breadcrumb from path
  const breadcrumbParts = currentPath ? currentPath.split("/") : [];

  const toggleDocSelection = (docId: string) => {
    setSelectedDocs((prev) =>
      prev.includes(docId)
        ? prev.filter((id) => id !== docId)
        : [...prev, docId]
    );
  };

  const toggleSelectAll = () => {
    if (selectedDocs.length === currentDocs.length) {
      setSelectedDocs([]);
    } else {
      setSelectedDocs(currentDocs.map((d) => d.id));
    }
  };

  const navigateToBreadcrumb = (index: number) => {
    if (index < 0) {
      setCurrentPath("");
    } else {
      setCurrentPath(breadcrumbParts.slice(0, index + 1).join("/"));
    }
    setSelectedDocs([]);
  };

  return (
    <div className="flex h-[600px] border rounded-lg overflow-hidden">
      {/* Sidebar - Folder Tree */}
      <div className="w-64 border-r bg-gray-50 overflow-y-auto">
        <div className="p-3 border-b bg-white">
          <h3 className="font-semibold text-sm">Data Room</h3>
        </div>
        <div className="p-2">
          {/* Root folder */}
          <div
            className={cn(
              "flex items-center gap-2 py-1 px-2 rounded cursor-pointer text-sm",
              currentPath === "" ? "bg-alchemyPrimaryOrange/10 text-alchemyPrimaryOrange" : "hover:bg-gray-100"
            )}
            onClick={() => setCurrentPath("")}
          >
            <FolderOpen className="h-4 w-4 text-alchemyPrimaryGoldenWeb" />
            <span>All Documents</span>
            <Badge variant="secondary" className="ml-auto h-5 text-xs">
              {documents.length}
            </Badge>
          </div>

          {/* Folder tree from registry */}
          {registry?.folder_structure.map((folder) => (
            <FolderTreeItem
              key={folder.name}
              folder={folder}
              path=""
              currentPath={currentPath}
              onNavigate={setCurrentPath}
              documentCounts={documentCounts}
            />
          ))}

          {/* Other Documents folder */}
          <div
            className={cn(
              "flex items-center gap-2 py-1 px-2 rounded cursor-pointer text-sm mt-2",
              currentPath === "99. Other Documents" ? "bg-alchemyPrimaryOrange/10 text-alchemyPrimaryOrange" : "hover:bg-gray-100"
            )}
            onClick={() => setCurrentPath("99. Other Documents")}
          >
            <Folder className="h-4 w-4 text-gray-400" />
            <span>99. Other Documents</span>
            <Badge variant="secondary" className="ml-auto h-5 text-xs">
              {documentCounts["99. Other Documents"] || 0}
            </Badge>
          </div>
        </div>
      </div>

      {/* Main Content - Document List */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="p-3 border-b bg-white flex items-center gap-3">
          {/* Breadcrumb */}
          <Breadcrumb className="flex-1">
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink
                  className="cursor-pointer"
                  onClick={() => navigateToBreadcrumb(-1)}
                >
                  Data Room
                </BreadcrumbLink>
              </BreadcrumbItem>
              {breadcrumbParts.map((part, index) => (
                <BreadcrumbItem key={index}>
                  <BreadcrumbSeparator />
                  {index === breadcrumbParts.length - 1 ? (
                    <BreadcrumbPage>{part}</BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink
                      className="cursor-pointer"
                      onClick={() => navigateToBreadcrumb(index)}
                    >
                      {part}
                    </BreadcrumbLink>
                  )}
                </BreadcrumbItem>
              ))}
            </BreadcrumbList>
          </Breadcrumb>

          {/* Search */}
          <div className="relative w-64">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search documents..."
              className="pl-8 h-8"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Actions Bar */}
        <div className="p-2 border-b bg-gray-50 flex items-center gap-2">
          {onUploadClick && (
            <Button size="sm" onClick={onUploadClick}>
              <Upload className="h-4 w-4 mr-1" />
              Upload
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            disabled={selectedDocs.length === 0}
            onClick={() => onMoveDocuments?.(selectedDocs, currentPath)}
          >
            <Move className="h-4 w-4 mr-1" />
            Move Selected
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={selectedDocs.length === 0}
            onClick={() => onDeleteDocuments?.(selectedDocs)}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Delete
          </Button>
          <span className="ml-auto text-sm text-muted-foreground">
            {selectedDocs.length > 0
              ? `${selectedDocs.length} selected`
              : `${currentDocs.length} documents`}
          </span>
        </div>

        {/* Document Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {currentDocs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <FolderOpen className="h-12 w-12 mb-2" />
              <p className="font-medium">No documents in this folder</p>
              <p className="text-sm">Upload documents or move existing ones here</p>
              {onUploadClick && (
                <Button className="mt-4" onClick={onUploadClick}>
                  <Upload className="h-4 w-4 mr-1" />
                  Upload Documents
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              {/* Select All */}
              <div className="flex items-center gap-2 pb-2 border-b">
                <Checkbox
                  checked={selectedDocs.length === currentDocs.length && currentDocs.length > 0}
                  onCheckedChange={toggleSelectAll}
                />
                <span className="text-sm text-muted-foreground">Select all</span>
              </div>

              {/* Document List */}
              {currentDocs.map((doc) => (
                <ContextMenu key={doc.id}>
                  <ContextMenuTrigger>
                    <Card
                      className={cn(
                        "cursor-pointer transition-colors",
                        selectedDocs.includes(doc.id)
                          ? "bg-blue-50 border-blue-200"
                          : "hover:bg-gray-50"
                      )}
                      onClick={() => onOpenDocument?.(doc.id)}
                    >
                      <CardContent className="p-3 flex items-center gap-3">
                        <Checkbox
                          checked={selectedDocs.includes(doc.id)}
                          onCheckedChange={() => toggleDocSelection(doc.id)}
                          onClick={(e) => e.stopPropagation()}
                        />
                        {getFileIcon(doc.type)}
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{doc.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatFileSize(doc.size)} • {formatDate(doc.uploadedAt)}
                          </p>
                        </div>
                        {doc.classification && (
                          <Badge variant="secondary" className="text-xs">
                            {doc.classification.category}
                          </Badge>
                        )}
                        <Button size="icon" variant="ghost" className="h-8 w-8">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </CardContent>
                    </Card>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => onOpenDocument?.(doc.id)}>
                      Open
                    </ContextMenuItem>
                    <ContextMenuItem
                      onClick={() => onMoveDocuments?.([doc.id], "")}
                    >
                      Move to...
                    </ContextMenuItem>
                    <ContextMenuItem
                      className="text-destructive"
                      onClick={() => onDeleteDocuments?.([doc.id])}
                    >
                      Delete
                    </ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default DataRoomBrowser;
