import {
  BadgeCheck,
  MoreHorizontal,
  PlusCircle,
  RefreshCcw,
  Clock,
  XCircle,
  AlertTriangle,
  Circle,
} from "lucide-react";

import { formatDistance } from "date-fns";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useMutateGetLink } from "@/hooks/useMutateGetLink";
import { Badge } from "@/components/ui/badge";
import FolderPicker from "../FolderPicker";
import { useMutateDDFileMove } from "@/hooks/useMutateDDFileMove";
import SingleTextPrompt from "../../../components/SingleTextPrompt";
import { cn } from "@/lib/utils";
import { useMutateDDFileRename } from "@/hooks/useMutateDDFileRename";
import { Input } from "@/components/ui/input";
import { useGetDD } from "@/hooks/useGetDD";
import { useToast } from "@/components/ui/use-toast";

export default function FileLister({
  dd_id,
  subHeader,
  folderId,
  folderName,
  files,
  addAnotherDoc,
  chatWithDoc,
  chatWithFolder,
}) {
  const mutateGetLink = useMutateGetLink();
  const mutateMoveFile = useMutateDDFileMove();
  const { data: _, refetch: refetchDD } = useGetDD(dd_id);
  const { toast } = useToast();

  useEffect(() => {
    setSelectedDocumentAndFolder(null);
  }, [folderId]);
  useEffect(() => {
    if (!mutateGetLink.isSuccess) return;
    console.log(mutateGetLink.data);
    window.open(mutateGetLink.data.data.url, "_blank", "noopener,noreferrer");
  }, [mutateGetLink.isSuccess]);

  useEffect(() => {
    if (!mutateGetLink.isError) return;
    const errorMessage = (mutateGetLink.error as any)?.response?.data?.message || "Failed to open document";
    toast({
      title: "Failed to open document",
      description: errorMessage,
      variant: "destructive",
    });
  }, [mutateGetLink.isError, mutateGetLink.error, toast]);
  const [showFolderPicker, setShowFolderPicker] = useState<boolean>(false);
  const [selectedFolder, setSelectedFolder] = useState<{
    folder_id: string;
    folder_name: string;
  } | null>(null);

  const [selectedDocumentAndFolder, setSelectedDocumentAndFolder] = useState<{
    doc_id: string;
    doc_file_name: string;
    folder_from_id: string;
    folder_name: string;
  } | null>(null);

  const viewFile = (doc_id) => {
    mutateGetLink.mutate({ doc_id: doc_id, is_dd: true });
  };

  const mutateFileRename = useMutateDDFileRename();

  const refresh = () => {
    refetchDD();
  };
  const copyInfo = (doc) => {
    navigator.clipboard.writeText(
      `Document name: ${doc.original_file_name}\nFolder: ${folderName}`
    );
  };
  useEffect(() => {
    if (!selectedFolder) return;

    if (selectedDocumentAndFolder.folder_from_id === selectedFolder.folder_id) {
      setShowFolderPicker(false);
      return;
    }
    mutateMoveFile.mutate({
      dd_id: dd_id,
      doc_id: selectedDocumentAndFolder.doc_id,
      folder_from_id: selectedDocumentAndFolder.folder_from_id,
      folder_to_id: selectedFolder.folder_id,
    });
  }, [selectedFolder]);
  useEffect(() => {
    if (!mutateMoveFile.isSuccess) return;
    setShowFolderPicker(false);
  }, [mutateMoveFile.isSuccess]);

  const moveDoc = (doc_id, doc_file_name, folder_from_id, folderName) => {
    setSelectedDocumentAndFolder({
      doc_id,
      doc_file_name,
      folder_from_id,
      folder_name: folderName,
    });
    setShowFolderPicker(true);
  };
  const renameDoc = (doc_id, doc_file_name, folder_from_id, folderName) => {
    setSelectedDocumentAndFolder({
      doc_id,
      doc_file_name,
      folder_from_id,
      folder_name: folderName,
    });
    setShowDocRenamer(true);
  };
  const [showDocRenamer, setShowDocRenamer] = useState<boolean>(false);
  const [searchText, setSearchText] = useState("");

  const docRenamerClosing = (value) => {
    setShowDocRenamer(false);
    mutateFileRename.mutate({
      dd_id: dd_id,
      doc_id: selectedDocumentAndFolder.doc_id,
      new_doc_name: value,
    });
  };
  return (
    <div>
      <SingleTextPrompt
        show={showDocRenamer}
        header={`Rename document from ${selectedDocumentAndFolder?.doc_file_name} in folder ${selectedDocumentAndFolder?.folder_name}`}
        label={"New document name"}
        onClosing={docRenamerClosing}
      />
      <FolderPicker
        header={"Please select a new destination folder for "}
        selectedFolderId={folderId}
        show={showFolderPicker}
        dd_id={dd_id}
        onSelected={({
          folder_id,
          folder_name,
        }: {
          folder_id: string;
          folder_name: string;
        }) => {
          setSelectedFolder({ folder_id: folder_id, folder_name: folder_name });
        }}
        onClosing={() => setShowFolderPicker(false)}
        askBefore
      />
      <div className="flex items-center">
        {subHeader && (
          <div className="text-xs flex">
            <div>
              <BadgeCheck />
            </div>
            <div className="pt-1 pl-2">{subHeader}</div>
          </div>
        )}
        <div className="ml-auto flex items-center gap-2 pb-2">
          {files?.length !== 0 && (
            <>
              <div className="text-sm">Search Criteria</div>
              <div>
                <Input
                  className="w-[200px] text-sm"
                  onChange={(evt) => setSearchText(evt.target.value)}
                  value={searchText}
                  placeholder="Search for a file name"
                ></Input>
              </div>
            </>
          )}

          <Button
            size="sm"
            className="h-8 gap-1"
            variant="outline"
            onClick={() => {
              addAnotherDoc();
            }}
          >
            <PlusCircle className="h-3.5 w-3.5" />
            <span className="sr-only sm:not-sr-only sm:whitespace-nowrap">
              Add another document
            </span>
          </Button>
          <Button
            size="sm"
            className="h-8 gap-1"
            variant="outline"
            onClick={() => {
              refresh();
            }}
          >
            <RefreshCcw className="h-3.5 w-3.5" />
            <span className="sr-only sm:not-sr-only sm:whitespace-nowrap">
              Refresh
            </span>
          </Button>
        </div>
      </div>
      <Card x-chunk="dashboard-06-chunk-0">
        <CardContent className="py-2">
          {files?.length === 0 && (
            <div className="text-sm">No files in this folder</div>
          )}
          {files?.length !== 0 && (
            <div className="max-h-[600px] overflow-y-auto overflow-x-auto relative">
              <Table className="table-fixed w-full">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[40%]">File name</TableHead>
                    <TableHead className="w-[20%]">Added</TableHead>
                    <TableHead className="w-[25%]">Status</TableHead>
                    <TableHead className="w-[15%]">
                      <span className="sr-only">Actions</span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {files
                    ?.filter((f) =>
                      searchText
                        ? f.original_file_name
                            .toLowerCase()
                            .indexOf(searchText.toLowerCase()) != -1
                        : true
                    )
                    ?.map((f) => {
                      return (
                        <TableRow
                          key={f.document_id}
                          className={cn(
                            selectedDocumentAndFolder?.doc_id ===
                              f.document_id && "font-bold"
                          )}
                        >
                          <TableCell className="break-words">
                            <div className="max-w-full overflow-hidden">
                              {!searchText && (
                                <span className="break-all">
                                  {f.original_file_name}
                                </span>
                              )}
                              {searchText && (
                                <div className="break-all">
                                  {f.original_file_name
                                    .split(new RegExp(`(${searchText})`, "gi"))
                                    .map((part, index) =>
                                      part
                                        .toLowerCase()
                                        .indexOf(searchText.toLowerCase()) !=
                                      -1 ? (
                                        <span
                                          key={index}
                                          className="bg-yellow-300"
                                        >
                                          {part}
                                        </span>
                                      ) : (
                                        <span key={index}>{part}</span>
                                      )
                                    )}
                                </div>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="whitespace-nowrap">
                            {formatDistance(
                              new Date(f.uploaded_at),
                              new Date(),
                              {
                                addSuffix: true,
                              }
                            )}
                          </TableCell>
                          <TableCell>
                            {f.processing_status === "Queued" && (
                              <Badge
                                variant="destructive"
                                className="gap-1 w-28 justify-center"
                              >
                                Not started
                              </Badge>
                            )}
                            {f.processing_status === "In progress" && (
                              <Badge
                                variant="secondary"
                                className="gap-1 w-28 justify-center"
                              >
                                <Clock className="h-4 w-4" />
                                In progress
                              </Badge>
                            )}
                            {f.processing_status === "Complete" && (
                              <Badge
                                variant="default"
                                className="gap-1 w-28 justify-center"
                              >
                                <BadgeCheck className="h-4 w-4" />
                                Complete
                              </Badge>
                            )}
                            {f.processing_status === "Failed" && (
                              <Badge
                                variant="destructive"
                                className="gap-1 w-28 justify-center"
                              >
                                <XCircle className="h-4 w-4" />
                                Failed
                              </Badge>
                            )}
                            {f.processing_status === "Unsupported" && (
                              <Badge
                                variant="outline"
                                className="gap-1 w-28 justify-center border-orange-500 text-orange-700 bg-orange-50"
                              >
                                <AlertTriangle className="h-4 w-4" />
                                Unsupported
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  aria-haspopup="true"
                                  size="icon"
                                  variant="ghost"
                                >
                                  <MoreHorizontal className="h-4 w-4" />
                                  <span className="sr-only">Toggle menu</span>
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                <DropdownMenuItem
                                  onClick={() => {
                                    moveDoc(
                                      f.document_id,
                                      f.original_file_name,
                                      folderId,
                                      folderName
                                    );
                                  }}
                                >
                                  Move
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={() => {
                                    renameDoc(
                                      f.document_id,
                                      f.original_file_name,
                                      folderId,
                                      folderName
                                    );
                                  }}
                                >
                                  Rename
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={() => viewFile(f.document_id)}
                                >
                                  View
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => copyInfo(f)}>
                                  Copy Info
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
