import React, { useEffect, useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { MoreVertical } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useGetDDDocsHistory } from "@/hooks/useGetDDDocsHistory";
import { formatDistance } from "date-fns";
import { useMutateGetLink } from "@/hooks/useMutateGetLink";
import QandA from "./QandA";
import { useToast } from "@/components/ui/use-toast";

export default function DocumentChanges({ dd_id }) {
  const { data: docsHistory, refetch: refetchDocsHistory } =
    useGetDDDocsHistory(dd_id);

  const mutateGetLink = useMutateGetLink();
  const { toast } = useToast();

  useEffect(() => {
    if (!mutateGetLink.isSuccess) return;
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

  const viewFile = (doc_id) => {
    mutateGetLink.mutate({ doc_id: doc_id, is_dd: true });
  };

  const [showQandA, setShowQandA] = useState<boolean>(false);
  const [qandAData, setQandAData] = useState<{
    dd_id: string;
    folder_id?: string;
    doc_id?: string;
    folderName?: string;
    fileName?: string;
  }>(null);

  useEffect(() => {
    if (!dd_id) return;

    refetchDocsHistory();
  }, [dd_id]);

  const handleAction = (type, doc) => {
    switch (type) {
      case "remove":
        // Remove notification for doc
        break;
      case "copy":
        navigator.clipboard.writeText(
          `Document name: ${doc.original_file_name}\nPrevious folder: ${doc.previous_folder}\nCurrent folder: ${doc.current_folder}\nAction: ${doc.action}\nBy User: ${doc.by_user}`
        );
        break;
      case "ask_questions":
        setQandAData({ dd_id: doc.dd_id, doc_id: doc.doc_id });
        setShowQandA(true);
        break;
      case "view":
        viewFile(doc.doc_id);
        break;
      default:
        break;
    }
  };

  return (
    <div className="p-6 mx-auto">
      <QandA
        onClosing={() => setShowQandA(false)}
        show={showQandA}
        data={qandAData}
      />
      <div className="bg-white shadow-md rounded-lg p-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Document Name</TableHead>
              <TableHead>Previous Folder</TableHead>
              <TableHead>Current Folder</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>By User</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {docsHistory?.history?.map((doc) => (
              <TableRow key={doc.doc_id}>
                <TableCell>{doc.original_file_name}</TableCell>
                <TableCell>{doc.previous_folder}</TableCell>
                <TableCell>{doc.current_folder}</TableCell>
                <TableCell>{doc.action}</TableCell>
                <TableCell>{doc.by_user}</TableCell>
                <TableCell>
                  {formatDistance(new Date(doc.action_at), new Date(), {
                    addSuffix: true,
                  })}
                </TableCell>
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreVertical className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      {/* <DropdownMenuItem
                        onClick={() => handleAction("remove", doc)}
                      >
                        Remove Notification
                      </DropdownMenuItem> */}
                      <DropdownMenuItem
                        onClick={() => handleAction("copy", doc)}
                      >
                        Copy Info
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => handleAction("view", doc)}
                      >
                        View Document
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
