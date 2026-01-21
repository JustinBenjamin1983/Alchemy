// Enhanced Questions.tsx - With new formatting in dialog
import React, { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  MessageSquare,
  FileText,
  Calendar,
  Folder,
  File,
  ExternalLink,
  Eye,
  MoreVertical,
  Copy,
  Download,
  Loader2,
} from "lucide-react";
import { formatDistance } from "date-fns";
import { useGetDDQuestions } from "@/hooks/useGetDDQuestions";
import { useMutateGetLink } from "@/hooks/useMutateGetLink";
import { useMutateExportQuestions } from "@/hooks/useMutateExportQuestions";
import { useEffect } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Markdown from "react-markdown";
import { useToast } from "@/components/ui/use-toast";

interface QuestionsProps {
  dd_id: string;
}

const Questions: React.FC<QuestionsProps> = ({ dd_id }) => {
  const { data: questions, isLoading, error } = useGetDDQuestions(dd_id);
  const mutateGetLink = useMutateGetLink();
  const { toast } = useToast();
  const [selectedQuestion, setSelectedQuestion] = useState<any>(null);
  const [showAnswerDialog, setShowAnswerDialog] = useState(false);
  const [currentTab, setCurrentTab] = useState<"Answer" | "ReferencedDocs">(
    "Answer"
  );

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

  const viewFile = (doc_id: string) => {
    mutateGetLink.mutate({ doc_id: doc_id, is_dd: true });
  };

  const copyInfo = (question: any) => {
    navigator.clipboard.writeText(
      `Question: ${question.question}\nAnswer: ${
        question.answer || "No answer"
      }`
    );
  };

  const mutateExportQuestions = useMutateExportQuestions();

  const handleExport = () => {
    mutateExportQuestions.mutate({ dd_id });
  };

  const viewAnswer = (question: any) => {
    setSelectedQuestion(question);
    setCurrentTab("Answer");
    setShowAnswerDialog(true);
  };

  const copyDocInfo = (doc: any) => {
    navigator.clipboard.writeText(
      `Document name: ${doc.filename}\nPage number: ${doc.page_number}`
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading questions...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-red-600">Error loading questions</div>
      </div>
    );
  }

  if (!questions || questions.length === 0) {
    return (
      <Card className="w-full">
        <CardContent className="flex flex-col items-center justify-center h-64">
          <MessageSquare className="h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-semibold text-gray-600 mb-2">
            No Questions Yet
          </h3>
          <p className="text-gray-500 text-center">
            Questions asked about documents and folders will appear here. Start
            by asking a question about a document or folder using the "Ask a
            question" button.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Questions & Answers Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {questions.length}
              </div>
              <div className="text-sm text-gray-600">Total Questions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {questions.filter((q) => q.answer).length}
              </div>
              <div className="text-sm text-gray-600">Answered</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {questions.filter((q) => !q.answer).length}
              </div>
              <div className="text-sm text-gray-600">No Answer Found</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Questions Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>All Questions</CardTitle>
            <Button
              onClick={handleExport}
              disabled={mutateExportQuestions.isPending}
              className="flex items-center gap-2"
              variant="outline"
            >
              {mutateExportQuestions.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              {mutateExportQuestions.isPending
                ? "Generating..."
                : "Export to Word"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Question</TableHead>
                <TableHead>Context</TableHead>
                <TableHead>Answer</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Referenced Docs</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {questions.map((question) => (
                <TableRow key={question.id}>
                  {/* Question */}
                  <TableCell className="max-w-xs">
                    <div className="break-words">
                      <span className="font-medium">{question.question}</span>
                    </div>
                  </TableCell>
                  {/* Context (Folder/Document) */}
                  <TableCell>
                    {question.document_name && (
                      <div className="flex items-center gap-1 text-sm">
                        <File className="h-4 w-4 text-blue-500" />
                        <span
                          className="truncate max-w-32"
                          title={question.document_name}
                        >
                          {question.document_name}
                        </span>
                      </div>
                    )}
                    {question.folder_name && !question.document_name && (
                      <div className="flex items-center gap-1 text-sm">
                        <Folder className="h-4 w-4 text-orange-500" />
                        <span
                          className="truncate max-w-32"
                          title={question.folder_name}
                        >
                          {question.folder_name}
                        </span>
                      </div>
                    )}
                  </TableCell>
                  {/* Answer - Now clickable */}
                  <TableCell className="max-w-md">
                    {question.answer ? (
                      <div
                        className="break-words text-sm bg-gray-50 p-2 rounded border-l-4 border-green-500 cursor-pointer hover:bg-gray-100 transition-colors"
                        onClick={() => viewAnswer(question)}
                        title="Click to view full answer"
                      >
                        <div className="flex items-center justify-between">
                          <span>
                            {question.answer.length > 100
                              ? `${question.answer.substring(0, 100)}...`
                              : question.answer}
                          </span>
                          <Eye className="h-4 w-4 text-gray-500 ml-2 flex-shrink-0" />
                        </div>
                      </div>
                    ) : (
                      <Badge
                        variant="outline"
                        className="text-orange-600 border-orange-300"
                      >
                        No answer found
                      </Badge>
                    )}
                  </TableCell>
                  {/* Date */}
                  <TableCell>
                    <div className="flex items-center gap-1 text-sm text-gray-600">
                      <Calendar className="h-4 w-4" />
                      <span>
                        {formatDistance(
                          new Date(question.created_at),
                          new Date(),
                          {
                            addSuffix: true,
                          }
                        )}
                      </span>
                    </div>
                  </TableCell>
                  {/* Referenced Documents */}
                  <TableCell>
                    {question.referenced_documents.length > 0 ? (
                      <div className="flex items-center gap-1">
                        <FileText className="h-4 w-4 text-blue-500" />
                        <Badge variant="outline">
                          {question.referenced_documents.length} sources
                        </Badge>
                      </div>
                    ) : (
                      <span className="text-gray-400 text-sm">None</span>
                    )}
                  </TableCell>
                  {/* Actions - Cleaned up to remove duplicates */}
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {/* Only show if there's an answer */}
                        {question.answer && (
                          <>
                            <DropdownMenuItem
                              onClick={() => viewAnswer(question)}
                            >
                              <Eye className="h-4 w-4 mr-2" />
                              View Full Answer
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                          </>
                        )}
                        {/* Copy question & answer */}
                        <DropdownMenuItem onClick={() => copyInfo(question)}>
                          <Copy className="h-4 w-4 mr-2" />
                          Copy Question & Answer
                        </DropdownMenuItem>
                        {/* Only show referenced documents if they exist */}
                        {question.referenced_documents.length > 0 && (
                          <>
                            <DropdownMenuSeparator />
                            {/* Create unique document entries */}
                            {Array.from(
                              new Map(
                                question.referenced_documents.map((doc) => [
                                  doc.doc_id,
                                  doc,
                                ])
                              ).values()
                            ).map((doc, index) => (
                              <DropdownMenuItem
                                key={doc.doc_id}
                                onClick={() => viewFile(doc.doc_id)}
                              >
                                <FileText className="h-4 w-4 mr-2" />
                                View {doc.filename}
                              </DropdownMenuItem>
                            ))}
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Enhanced Dialog with New Formatting */}
      <Dialog open={showAnswerDialog} onOpenChange={setShowAnswerDialog}>
        <DialogContent className="w-[600px] max-h-[800px] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle>Question & Answer</DialogTitle>
            <DialogDescription></DialogDescription>
          </DialogHeader>

          {/* Main content area with proper flex sizing */}
          <div className="flex-1 overflow-hidden">
            {selectedQuestion && (
              <div className="flex flex-col h-full">
                {/* Question */}
                <div className="flex-shrink-0 mb-4">
                  <span className="text-2xl inline">&ldquo;</span>
                  {selectedQuestion.question}
                  <span className="text-2xl inline">&rdquo;</span>
                </div>

                {/* Context Info */}
                <div className="flex-shrink-0 mb-4 text-sm text-gray-600">
                  {selectedQuestion.document_name && (
                    <div className="flex items-center gap-1">
                      <File className="h-4 w-4 text-blue-500" />
                      <span>Document: {selectedQuestion.document_name}</span>
                    </div>
                  )}
                  {selectedQuestion.folder_name &&
                    !selectedQuestion.document_name && (
                      <div className="flex items-center gap-1">
                        <Folder className="h-4 w-4 text-orange-500" />
                        <span>Folder: {selectedQuestion.folder_name}</span>
                      </div>
                    )}
                  <div className="flex items-center gap-1 mt-1">
                    <Calendar className="h-4 w-4" />
                    <span>
                      Asked{" "}
                      {formatDistance(
                        new Date(selectedQuestion.created_at),
                        new Date(),
                        { addSuffix: true }
                      )}
                    </span>
                  </div>
                </div>

                {/* Tabs with flexible content area */}
                <Tabs
                  value={currentTab}
                  onValueChange={(value) => setCurrentTab(value as any)}
                  className="flex flex-col flex-1 min-h-0"
                >
                  <TabsList className="flex-shrink-0">
                    <TabsTrigger value="Answer">Your Answer</TabsTrigger>
                    <TabsTrigger value="ReferencedDocs">
                      Referenced Documents (
                      {selectedQuestion.referenced_documents.length})
                    </TabsTrigger>
                  </TabsList>

                  {/* Enhanced Answer Tab with New Formatting */}
                  <TabsContent value="Answer" className="flex-1 overflow-auto">
                    <div className="max-h-[500px] overflow-auto">
                      {selectedQuestion.answer ? (
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
                                  } else if (text.includes("Low Confidence")) {
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
                                  return <strong {...props}>{children}</strong>;
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
                              {selectedQuestion.answer}
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
                      ) : (
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
                    value="ReferencedDocs"
                    className="flex-1 overflow-hidden"
                  >
                    {selectedQuestion.referenced_documents.length > 0 ? (
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
                            {selectedQuestion.referenced_documents.map(
                              (doc, index) => (
                                <TableRow key={index}>
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
                                          onClick={() => copyDocInfo(doc)}
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
                    ) : (
                      <div className="text-gray-500 text-center py-8">
                        No referenced documents for this question.
                      </div>
                    )}
                  </TabsContent>
                </Tabs>
              </div>
            )}
          </div>

          <DialogFooter className="flex-shrink-0">
            <Button
              variant="secondary"
              onClick={() => setShowAnswerDialog(false)}
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Questions;
