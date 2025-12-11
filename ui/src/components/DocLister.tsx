import { useMutateToggleGlobalOpinionDoc } from "@/hooks/useMutateToggleGlobalOpinionDoc";
import { useMutateToggleOpinionDoc } from "@/hooks/useMutateToggleOpinionDoc";
import {
  CheckCircle,
  Circle,
  Ellipsis,
  MoreHorizontal,
  RefreshCw,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Button } from "./ui/button";
import { useMutateDeleteOpinionDoc } from "@/hooks/useMutateDeleteOpinionDoc";
import { AlertCheckFor } from "./AlertCheckFor";
import { useMutateDeleteGlobalOpinionDoc } from "@/hooks/useMutateDeleteGlobalOpinionDoc";
import { useMutateGetLink } from "@/hooks/useMutateGetLink";
import { cn } from "@/lib/utils";

import { DocTags } from "./DocTags";

export function DocLister({
  title,
  opinionId,
  docs,
  refresh,
  isGlobal,
  globalDocs,
  allowToggling = true,
}: {
  title: string;
  opinionId: string;
  docs: any;
  refresh?: any;
  isGlobal: boolean;
  globalDocs?: any;
  allowToggling?: boolean;
}) {
  const mutateToggleDoc = useMutateToggleOpinionDoc();
  const mutateToggleGlobalDoc = useMutateToggleGlobalOpinionDoc();
  const mutateDeleteDoc = useMutateDeleteOpinionDoc();
  const mutateDeleteGlobalDoc = useMutateDeleteGlobalOpinionDoc();
  const mutateGetLink = useMutateGetLink();
  const WAIT_ICON = () => <Ellipsis className="animate-pulse text-blue-500" />;

  const [pendingDocId, setPendingDocId] = useState<string>(null);
  const [showPromptToCheckForDeleteDoc, setShowPromptToCheckForDeleteDoc] =
    useState<boolean>(false);
  const [selectedDoc, setSelectedDoc] = useState<{}>(null);

  const [isRequestingToDeleteGlobalDoc, setIsRequestingToDeleteGlobalDoc] =
    useState<boolean>(false);

  const [docsRefreshing, setDocsRefreshing] = useState(false);

  const handleRefreshClick = () => {
    setDocsRefreshing(true);
    refresh();

    // stop spinning after 1 second
    setTimeout(() => setDocsRefreshing(false), 1000);
  };

  const toggleDoc = (docId, docName, is_global) => {
    setPendingDocId(docId);
    if (!is_global) {
      mutateToggleDoc.mutate({
        opinion_id: opinionId,
        doc_id: docId,
      });
    } else {
      mutateToggleGlobalDoc.mutate({
        opinion_id: opinionId,
        doc_id: docId,
        doc_name: docName,
      });
    }
  };
  useEffect(() => {
    if (!mutateToggleDoc.isSuccess) return; // TODO
    setPendingDocId(null);
    refresh && refresh();
  }, [mutateToggleDoc.isSuccess]);

  useEffect(() => {
    if (!mutateToggleGlobalDoc.isSuccess) return; // TODO
    setPendingDocId(null);
    refresh && refresh();
  }, [mutateToggleGlobalDoc.isSuccess]);

  useEffect(() => {
    if (!mutateDeleteDoc.isSuccess) return;
    reset();
    refresh && refresh();
  }, [mutateDeleteDoc.isSuccess]);
  const reset = () => {
    setSelectedDoc(null);
    setShowPromptToCheckForDeleteDoc(false);
    setIsRequestingToDeleteGlobalDoc(false);
  };
  useEffect(() => {
    if (!mutateDeleteGlobalDoc.isSuccess) return;
    reset();
    refresh && refresh();
  }, [mutateDeleteGlobalDoc.isSuccess]);
  useEffect(() => {
    if (!mutateGetLink.isSuccess) return;

    console.log(mutateGetLink.data);

    window.open(mutateGetLink.data.data.url, "_blank", "noopener,noreferrer");

    reset();
  }, [mutateGetLink.isSuccess]);
  const getLink = (doc) => {
    setSelectedDoc(doc);
    mutateGetLink.mutate({ doc_id: doc.doc_id });
  };
  const deleteDoc = () => {
    mutateDeleteDoc.mutate({
      opinion_id: opinionId,
      doc_id: (selectedDoc as any).doc_id,
    });
  };
  const deleteGlobalDoc = () => {
    mutateDeleteGlobalDoc.mutate({
      opinion_id: opinionId,
      doc_id: (selectedDoc as any).doc_id,
    });
  };
  return (
    <>
      <AlertCheckFor
        title="Delete document"
        blurb={`Are you sure you want to delete [${
          (selectedDoc as any)?.doc_name
        }]? ${
          isRequestingToDeleteGlobalDoc
            ? "This document is a global document."
            : ""
        }`}
        show={showPromptToCheckForDeleteDoc}
        okText={"Yes, delete it"}
        onOK={isRequestingToDeleteGlobalDoc ? deleteGlobalDoc : deleteDoc}
        cancelText={"No"}
        onCancel={() => setShowPromptToCheckForDeleteDoc(false)}
      />
      <div className="flex">
        <div>
          <h2 className="text-xl font-semibold mb-4">{title}</h2>
        </div>
        <div className="ml-auto">
          <Button
            title="Click to reload available documents"
            variant="ghost"
            onClick={handleRefreshClick}
          >
            <RefreshCw className={docsRefreshing ? "animate-spin" : ""} />
          </Button>
        </div>
      </div>

      <div
        className={cn(
          "py-2 overflow-y-scroll h-64",
          ((!isGlobal && docs?.length > 4) ||
            (isGlobal && globalDocs?.length > 4)) &&
            "scrollbar-always"
        )}
      >
        {((!isGlobal && docs?.length > 0) ||
          (isGlobal && globalDocs?.length > 0)) && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Document name</TableHead>
                {allowToggling && <TableHead>Active</TableHead>}
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {!isGlobal &&
                docs
                  // ?.filter((d) => !d.is_global)
                  ?.map((doc) => (
                    <TableRow key={doc.doc_id}>
                      <TableCell>
                        <>
                          <div>
                            {doc.doc_name} {doc.is_global && <>(global doc)</>}
                          </div>

                          <DocTags tags={doc.tags} />
                        </>
                      </TableCell>
                      {allowToggling && (
                        <TableCell
                          className="cursor-pointer"
                          title={
                            doc.enabled ? "Click to disable" : "Click to enable"
                          }
                        >
                          <div
                            onClick={() =>
                              toggleDoc(doc.doc_id, doc.doc_name, doc.is_global)
                            }
                          >
                            {pendingDocId === doc.doc_id ? (
                              <WAIT_ICON />
                            ) : doc.enabled ? (
                              <CheckCircle className="text-green-600 hover:text-green-800" />
                            ) : (
                              <Circle className="text-gray-400 hover:text-gray-600" />
                            )}
                          </div>
                        </TableCell>
                      )}
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
                              className="cursor-pointer"
                              onClick={() => {
                                getLink(doc);
                              }}
                            >
                              View
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="cursor-pointer"
                              disabled={doc.is_global}
                              onClick={() => {
                                setSelectedDoc(doc);
                                setShowPromptToCheckForDeleteDoc(true);
                              }}
                            >
                              {!doc.is_global
                                ? "Delete"
                                : "Can't delete, this is a global document"}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}

              {isGlobal &&
                globalDocs?.map((doc) => (
                  <TableRow key={doc.doc_id}>
                    <TableCell>
                      <div className="flex gap-4">
                        <div>
                          {doc.doc_name} {doc.is_global && <>(global doc)</>}
                        </div>

                        <div title="This file is busy being indexed">
                          {!doc.was_indexed && <WAIT_ICON />}
                        </div>
                      </div>

                      <DocTags tags={doc.tags} />
                    </TableCell>
                    {allowToggling && (
                      <TableCell
                        className="cursor-pointer"
                        title={
                          docs?.find(
                            (d) => d.doc_id == doc.doc_id && d.enabled
                          ) != null
                            ? "Click to disable"
                            : "Click to enable"
                        }
                      >
                        <div
                          onClick={() =>
                            toggleDoc(doc.doc_id, doc.doc_name, true)
                          }
                        >
                          {pendingDocId === doc.doc_id ? (
                            <WAIT_ICON />
                          ) : docs?.find(
                              (d) => d.doc_id == doc.doc_id && d.enabled
                            ) != null ? (
                            <CheckCircle className="text-green-600 hover:text-green-800" />
                          ) : (
                            <Circle className="text-gray-400 hover:text-gray-600" />
                          )}
                        </div>
                      </TableCell>
                    )}
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            aria-haspopup="true"
                            size="icon"
                            variant="ghost"
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuItem
                            className="cursor-pointer"
                            onClick={() => {
                              getLink(doc);
                            }}
                          >
                            View
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="cursor-pointer"
                            onClick={() => {
                              setIsRequestingToDeleteGlobalDoc(true);
                              setSelectedDoc(doc);
                              setShowPromptToCheckForDeleteDoc(true);
                            }}
                          >
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        )}
        {((!isGlobal && !docs?.length) ||
          (isGlobal && !globalDocs?.length)) && (
          <div className="flex items-center justify-center">
            <div className="text-center text-sm font-medium">No documents</div>
          </div>
        )}
      </div>
    </>
  );
}

{
  /* ; */
}
