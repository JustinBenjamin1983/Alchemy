import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMutateChat } from "@/hooks/useMutateChat";
import { Loader2, MoreVertical } from "lucide-react";
import { useEffect, useState } from "react";
import Markdown from "react-markdown";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useMutateGetLink } from "@/hooks/useMutateGetLink";
import { useQueryClient } from "@tanstack/react-query";

export default function QandA({
  show,
  onClosing,
  data,
}: {
  show: boolean;
  onClosing: any;
  data: {
    dd_id: string;
    folder_id?: string;
    doc_id?: string;
    folderName?: string;
    fileName?: string;
  } | null;
}) {
  const mutateChat = useMutateChat();
  const [question, setQuestion] = useState<string | null>("");
  const [currentTab, setCurrentTab] = useState<"Answer" | "ReferencedDocs">(
    "Answer"
  );
  const [uiState, setUIState] = useState<"Ask" | "Asked">("Ask");

  const handleClose = (closing) => {
    console.log("closing", closing);
    onClosing();
    setTimeout(() => {
      document.body.style.pointerEvents = "auto";
    }, 500);
  };

  const askQuestion = () => {
    if (!data) return;
    mutateChat.mutate({
      question: question,
      dd_id: data.dd_id,
      document_id: data.doc_id,
      folder_id: data.folder_id,
    });
  };

  const handleKeyDownOnSearchInput = (
    event: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (event.key === "Enter") {
      askQuestion();
    }
  };

  const mutateGetLink = useMutateGetLink();

  useEffect(() => {
    if (!mutateGetLink.isSuccess) return;
    window.open(mutateGetLink.data.data.url, "_blank", "noopener,noreferrer");
  }, [mutateGetLink.isSuccess]);

  const viewFile = (doc_id) => {
    mutateGetLink.mutate({ doc_id: doc_id, is_dd: true });
  };

  const copyInfo = (doc) => {
    navigator.clipboard.writeText(
      `Document name: ${doc.filename}\nPage number: ${doc.page_number}`
    );
  };

  const queryClient = useQueryClient();

  useEffect(() => {
    if (!mutateChat.isSuccess || !data) return;
    setUIState("Asked");
    // Refresh the questions list
    queryClient.invalidateQueries({ queryKey: ["dd-questions", data.dd_id] });
  }, [mutateChat.isSuccess, queryClient, data]);

  console.log("data", data);

  // Early return if data is null and dialog is not shown
  if (!data && !show) {
    return null;
  }

  return (
    <>
      <Dialog open={show} onOpenChange={handleClose}>
        <DialogContent className="w-[600px] max-h-[800px] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            {data?.fileName && (
              <DialogTitle>
                Chat with document <i>{data.fileName}</i>
              </DialogTitle>
            )}
            {data && !data?.fileName && (
              <DialogTitle>
                Chat with documents in folder <i>{data?.folderName}</i>
              </DialogTitle>
            )}
            {!data && <DialogTitle>Loading...</DialogTitle>}
            <DialogDescription></DialogDescription>
          </DialogHeader>

          {/* Main content area with proper flex sizing */}
          <div className="flex-1 overflow-hidden">
            {/* Only render content if data exists */}
            {data && (
              <>
                {uiState === "Ask" && (
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-3 items-center gap-4">
                      <Label htmlFor="name" className="text-right">
                        Your question
                      </Label>
                      <Input
                        value={question}
                        onChange={(evt) => setQuestion(evt.target.value)}
                        className="col-span-2"
                        onKeyDown={handleKeyDownOnSearchInput}
                      />
                    </div>
                  </div>
                )}

                {uiState === "Asked" && (
                  <div className="flex flex-col h-full">
                    {/* Question display */}
                    <div className="flex-shrink-0 mb-4">
                      <span className="text-2xl inline">&ldquo;</span>
                      {question}
                      <span className="text-2xl inline">&rdquo;</span>
                    </div>

                    {/* Tabs with flexible content area */}
                    <Tabs
                      value={currentTab}
                      className="flex flex-col flex-1 min-h-0"
                    >
                      <TabsList className="flex-shrink-0">
                        <TabsTrigger
                          value={"Answer"}
                          onClick={() => setCurrentTab("Answer")}
                        >
                          Your answer
                        </TabsTrigger>
                        <TabsTrigger
                          value={"ReferencedDocs"}
                          onClick={() => setCurrentTab("ReferencedDocs")}
                        >
                          Referenced documents
                        </TabsTrigger>
                      </TabsList>

                      <TabsContent
                        value={"Answer"}
                        className="flex-1 overflow-auto"
                      >
                        <div className="max-h-[500px] overflow-auto">
                          {mutateChat.data?.data?.answer != null && (
                            <div className="space-y-4">
                              {/* Enhanced Markdown with custom styling */}
                              <div className="prose prose-sm max-w-none">
                                <Markdown
                                  className="markdown"
                                  components={{
                                    // Custom rendering for confidence indicators
                                    strong: ({ children, ...props }) => {
                                      const text = children?.toString() || "";
                                      if (text.includes("High Confidence")) {
                                        return (
                                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 border border-green-200">
                                            🟢 {text}
                                          </span>
                                        );
                                      } else if (
                                        text.includes("Medium Confidence")
                                      ) {
                                        return (
                                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 border border-yellow-200">
                                            🟡 {text}
                                          </span>
                                        );
                                      } else if (
                                        text.includes("Low Confidence")
                                      ) {
                                        return (
                                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800 border border-orange-200">
                                            🟠 {text}
                                          </span>
                                        );
                                      } else if (text.includes("Uncertain")) {
                                        return (
                                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-200">
                                            🔴 {text}
                                          </span>
                                        );
                                      }
                                      return (
                                        <strong {...props}>{children}</strong>
                                      );
                                    },
                                    // Enhanced quote styling
                                    blockquote: ({ children, ...props }) => (
                                      <div className="border-l-4 border-blue-500 bg-blue-50 p-4 my-4 rounded-r-lg">
                                        <div className="flex items-start">
                                          <span className="text-blue-500 text-2xl mr-2">
                                            "
                                          </span>
                                          <div className="flex-1 italic text-blue-900">
                                            {children}
                                          </div>
                                        </div>
                                      </div>
                                    ),
                                    // Enhanced headers
                                    h2: ({ children, ...props }) => (
                                      <h2
                                        className="text-lg font-semibold text-gray-900 border-b border-gray-200 pb-2 mb-3 mt-6"
                                        {...props}
                                      >
                                        {children}
                                      </h2>
                                    ),
                                    // Enhanced list items
                                    li: ({ children, ...props }) => (
                                      <li
                                        className="mb-2 leading-relaxed"
                                        {...props}
                                      >
                                        {children}
                                      </li>
                                    ),
                                    // Enhanced code (for source references)
                                    code: ({ children, ...props }) => {
                                      const text = children?.toString() || "";
                                      if (
                                        text.includes("Source:") ||
                                        text.includes("Sources:")
                                      ) {
                                        return (
                                          <span className="inline-flex items-center px-2 py-1 rounded bg-gray-100 text-gray-700 text-xs font-mono border">
                                            📄 {text}
                                          </span>
                                        );
                                      }
                                      return (
                                        <code
                                          className="bg-gray-100 px-1 py-0.5 rounded text-sm"
                                          {...props}
                                        >
                                          {children}
                                        </code>
                                      );
                                    },
                                  }}
                                >
                                  {mutateChat.data.data.answer}
                                </Markdown>
                              </div>

                              {/* Quick confidence summary */}
                              <div className="mt-6 p-4 bg-gray-50 rounded-lg border">
                                <h4 className="font-semibold text-sm text-gray-700 mb-2">
                                  Response Quality Indicators:
                                </h4>
                                <div className="flex flex-wrap gap-2 text-xs">
                                  <div className="flex items-center gap-1">
                                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                                    <span>High Confidence (90-100%)</span>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
                                    <span>Medium Confidence (70-89%)</span>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                                    <span>Low Confidence (50-69%)</span>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                                    <span>Uncertain (&lt;50%)</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                          {mutateChat.data?.data?.answer == null && (
                            <div className="text-center py-8 text-gray-500">
                              <div className="text-4xl mb-4">🔍</div>
                              <p className="text-lg font-medium">
                                No meaningful answer found
                              </p>
                              <p className="text-sm mt-2">
                                The documents provided don't contain sufficient
                                information to answer your question.
                              </p>
                            </div>
                          )}
                        </div>
                      </TabsContent>

                      <TabsContent
                        value={"ReferencedDocs"}
                        className="flex-1 overflow-hidden"
                      >
                        <div className="max-h-[500px] overflow-auto border rounded-lg">
                          <Table>
                            <TableHeader className="sticky top-0 bg-white z-10">
                              <TableRow>
                                <TableHead>Document Name</TableHead>
                                <TableHead>Page Number</TableHead>
                                <TableHead>Actions</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {mutateChat.data?.data?.documents_referenced?.map(
                                (doc) => (
                                  <TableRow key={doc.doc_id}>
                                    <TableCell className="break-words max-w-xs">
                                      {doc.filename}
                                    </TableCell>
                                    <TableCell>{doc.page_number}</TableCell>
                                    <TableCell className="text-right">
                                      <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                          <Button variant="ghost" size="icon">
                                            <MoreVertical className="w-4 h-4" />
                                          </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                          <DropdownMenuItem
                                            onClick={() => viewFile(doc.doc_id)}
                                          >
                                            View File
                                          </DropdownMenuItem>
                                          <DropdownMenuItem
                                            onClick={() => copyInfo(doc)}
                                          >
                                            Copy Info
                                          </DropdownMenuItem>
                                        </DropdownMenuContent>
                                      </DropdownMenu>
                                    </TableCell>
                                  </TableRow>
                                )
                              )}
                            </TableBody>
                          </Table>
                        </div>
                      </TabsContent>
                    </Tabs>
                  </div>
                )}
              </>
            )}
          </div>

          <DialogFooter className="flex-shrink-0">
            {uiState === "Asked" && (
              <Button
                type="button"
                variant="default"
                onClick={() => setUIState("Ask")}
              >
                Ask another question
              </Button>
            )}
            {uiState === "Ask" && (
              <Button
                type="button"
                variant="default"
                onClick={askQuestion}
                disabled={
                  !question ||
                  question.length === 0 ||
                  mutateChat.isPending ||
                  !data
                }
              >
                {mutateChat.isPending && <Loader2 className="animate-spin" />}
                Ask
              </Button>
            )}
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setUIState("Ask");
                setCurrentTab("Answer");
                handleClose(true);
              }}
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
