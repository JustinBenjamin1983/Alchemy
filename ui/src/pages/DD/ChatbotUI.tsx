import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  MessageCircle,
  X,
  Send,
  Minimize2,
  Folder,
  FileText,
  Maximize2,
  Loader2,
  MoreVertical,
  AlertTriangle,
  AlertCircle,
  Info,
} from "lucide-react";
import { useMutateChat } from "@/hooks/useMutateChat";
import Markdown from "react-markdown";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { useMutateGetLink } from "@/hooks/useMutateGetLink";

interface Document {
  document_id: string;
  original_file_name: string;
  type: string;
}

interface Folder {
  folder_id: string;
  folder_name: string;
  documents: Document[];
}

interface Risk {
  level: "red" | "amber" | "yellow";
  category: string;
  description: string;
  impact: string;
  recommendation: string;
  confidence: "high" | "medium" | "low";
  supporting_docs: string[];
}

interface ChatMessage {
  id: number;
  type: "user" | "bot";
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  referencedDocs?: Array<{
    doc_id: string;
    filename: string;
    page_number: number;
    folder_path: string;
  }>;
  risks?: Risk[];
  searchScope?: string;
}

interface ChatbotUIProps {
  folders?: Folder[];
  dd_id?: string;
}

// Interface for tracking selected references
interface SelectedReference {
  id: string;
  name: string;
  type: "folder" | "document";
  textMarker: string; // The actual text in the message like "@1. Corporate"
}

export default function ChatbotUI({ folders = [], dd_id }: ChatbotUIProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [message, setMessage] = useState("");
  const [showCommandPopup, setShowCommandPopup] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [popupPosition, setPopupPosition] = useState({ x: 0, y: 0 });

  // NEW: Track selected references with their IDs
  const [selectedReferences, setSelectedReferences] = useState<
    SelectedReference[]
  >([]);

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mutateChat = useMutateChat();
  const mutateGetLink = useMutateGetLink();

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      type: "bot",
      content:
        "Hello! I'm your AI legal assistant. How can I help you with your due diligence today?",
      timestamp: new Date(),
    },
  ]);

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle file viewing
  useEffect(() => {
    if (!mutateGetLink.isSuccess) return;
    window.open(mutateGetLink.data.data.url, "_blank", "noopener,noreferrer");
  }, [mutateGetLink.isSuccess]);

  const viewFile = (doc_id: string) => {
    mutateGetLink.mutate({ doc_id: doc_id, is_dd: true });
  };

  const copyInfo = (doc: any) => {
    navigator.clipboard.writeText(
      `Document name: ${doc.filename}\nPage number: ${doc.page_number}`
    );
  };

  // Handle successful chat response
  useEffect(() => {
    if (!mutateChat.isSuccess || !mutateChat.data?.data) return;

    const response = mutateChat.data.data;
    const botResponse: ChatMessage = {
      id: Date.now(),
      type: "bot",
      content:
        response.answer ||
        "I couldn't find a meaningful answer to your question in the provided documents.",
      timestamp: new Date(),
      referencedDocs: response.documents_referenced || [],
      risks: response.risks || [],
      searchScope: response.search_scope,
    };

    setMessages((prev) => {
      const withoutLoading = prev.filter((msg) => !msg.isLoading);
      return [...withoutLoading, botResponse];
    });

    mutateChat.reset();
  }, [mutateChat.isSuccess, mutateChat.data]);

  // Handle chat errors
  useEffect(() => {
    if (!mutateChat.isError) return;

    const errorResponse: ChatMessage = {
      id: Date.now(),
      type: "bot",
      content:
        "I'm sorry, there was an error processing your request. Please try again.",
      timestamp: new Date(),
    };

    setMessages((prev) => {
      const withoutLoading = prev.filter((msg) => !msg.isLoading);
      return [...withoutLoading, errorResponse];
    });

    mutateChat.reset();
  }, [mutateChat.isError]);

  // Flatten folders and documents for the command popup
  const getAllItems = () => {
    const items: Array<{
      id: string;
      name: string;
      type: "folder" | "document";
      parentFolder?: string;
    }> = [];

    folders.forEach((folder) => {
      items.push({
        id: folder.folder_id,
        name: folder.folder_name,
        type: "folder",
      });

      folder.documents.forEach((doc) => {
        items.push({
          id: doc.document_id,
          name: doc.original_file_name,
          type: "document",
          parentFolder: folder.folder_name,
        });
      });
    });

    return items;
  };

  const getFilteredItems = () => {
    const allItems = getAllItems();
    if (!commandQuery) return allItems.slice(0, 10);

    return allItems
      .filter(
        (item) =>
          item.name.toLowerCase().includes(commandQuery.toLowerCase()) ||
          (item.parentFolder &&
            item.parentFolder
              .toLowerCase()
              .includes(commandQuery.toLowerCase()))
      )
      .slice(0, 10);
  };

  const getCursorPosition = () => {
    const textarea = inputRef.current;
    if (!textarea) return { x: 0, y: 0 };

    const rect = textarea.getBoundingClientRect();
    const style = window.getComputedStyle(textarea);
    const paddingLeft = parseInt(style.paddingLeft);

    return {
      x: rect.left + paddingLeft,
      y: rect.top - 250,
    };
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    const cursorPosition = e.target.selectionStart || 0;
    setMessage(value);

    const textarea = e.target;
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 128) + "px";

    // Clean up selectedReferences if @ mentions are removed from the text
    updateSelectedReferencesFromText(value);

    const textBeforeCursor = value.substring(0, cursorPosition);
    const commandMatch = textBeforeCursor.match(/\/>([^/>]*)$/);

    if (commandMatch) {
      const query = commandMatch[1];
      setCommandQuery(query);
      setShowCommandPopup(true);
      setSelectedIndex(0);
      setPopupPosition(getCursorPosition());
    } else {
      setShowCommandPopup(false);
      setCommandQuery("");
    }
  };

  // NEW: Function to clean up selectedReferences when text is modified
  const updateSelectedReferencesFromText = (currentText: string) => {
    setSelectedReferences((prev) =>
      prev.filter((ref) => currentText.includes(ref.textMarker))
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showCommandPopup) {
      const filteredItems = getFilteredItems();
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          Math.min(prev + 1, filteredItems.length - 1)
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredItems[selectedIndex]) {
          insertReference(filteredItems[selectedIndex]);
        }
      } else if (e.key === "Escape") {
        setShowCommandPopup(false);
      }
    } else if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // UPDATED: Store the ID mapping when inserting reference
  const insertReference = (item: {
    id: string;
    name: string;
    type: "folder" | "document";
  }) => {
    const textarea = inputRef.current;
    if (!textarea) return;

    const cursorPosition = textarea.selectionStart || 0;
    const textBeforeCursor = message.substring(0, cursorPosition);
    const textAfterCursor = message.substring(cursorPosition);

    const beforeCommand = textBeforeCursor.replace(/\/>([^/>]*)$/, "");
    const reference = `@${item.name}`;
    const newMessage = beforeCommand + reference + textAfterCursor;

    setMessage(newMessage);
    setShowCommandPopup(false);

    // NEW: Store the reference with its ID
    const newReference: SelectedReference = {
      id: item.id,
      name: item.name,
      type: item.type,
      textMarker: reference,
    };

    setSelectedReferences((prev) => {
      // Remove any existing reference with the same textMarker
      const filtered = prev.filter((ref) => ref.textMarker !== reference);
      return [...filtered, newReference];
    });

    console.log(
      `Stored reference: ${reference} -> ID: ${item.id} (${item.type})`
    );

    setTimeout(() => {
      textarea.focus();
      const newCursorPosition = beforeCommand.length + reference.length;
      textarea.setSelectionRange(newCursorPosition, newCursorPosition);
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 128) + "px";
    }, 0);
  };

  const handleSendMessage = () => {
    if (!message.trim() || !dd_id) return;

    const newUserMessage: ChatMessage = {
      id: Date.now(),
      type: "user",
      content: message,
      timestamp: new Date(),
    };

    const loadingMessage: ChatMessage = {
      id: Date.now() + 1,
      type: "bot",
      content: "Analyzing your question...",
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages((prev) => [...prev, newUserMessage, loadingMessage]);

    // NEW: Use stored IDs instead of parsing text
    const referencedItems = getStoredReferences();

    console.log("Sending with stored references:", referencedItems);

    // Call the chat API with enhanced parameters
    mutateChat.mutate({
      question: message,
      dd_id: dd_id,
      document_ids: referencedItems.document_ids,
      folder_ids: referencedItems.folder_ids,
    });

    // Clear message and references after sending
    setMessage("");
    setSelectedReferences([]);
    setShowCommandPopup(false);

    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
  };

  // NEW: Get references from stored IDs instead of parsing text
  const getStoredReferences = () => {
    const document_ids: string[] = [];
    const folder_ids: string[] = [];

    // Filter references that are still present in the current message
    const activeReferences = selectedReferences.filter((ref) =>
      message.includes(ref.textMarker)
    );

    for (const ref of activeReferences) {
      if (ref.type === "document" && !document_ids.includes(ref.id)) {
        document_ids.push(ref.id);
      } else if (ref.type === "folder" && !folder_ids.includes(ref.id)) {
        folder_ids.push(ref.id);
      }
    }

    console.log("Active references:", {
      total: activeReferences.length,
      folders: folder_ids.length,
      documents: document_ids.length,
    });

    return { document_ids, folder_ids };
  };

  const handleFullScreenToggle = () => {
    setIsFullScreen(!isFullScreen);
    setIsMinimized(false);
  };

  // Risk component
  const RiskIndicator = ({ risk }: { risk: Risk }) => {
    const getRiskColor = (level: string) => {
      switch (level) {
        case "red":
          return "bg-red-100 text-red-800 border-red-200";
        case "amber":
          return "bg-orange-100 text-orange-800 border-orange-200";
        case "yellow":
          return "bg-yellow-100 text-yellow-800 border-yellow-200";
        default:
          return "bg-gray-100 text-gray-800 border-gray-200";
      }
    };

    const getRiskIcon = (level: string) => {
      switch (level) {
        case "red":
          return <AlertTriangle className="w-4 h-4" />;
        case "amber":
          return <AlertCircle className="w-4 h-4" />;
        case "yellow":
          return <Info className="w-4 h-4" />;
        default:
          return <Info className="w-4 h-4" />;
      }
    };

    return (
      <div className={`p-3 rounded-lg border ${getRiskColor(risk.level)} mb-2`}>
        <div className="flex items-start gap-2">
          {getRiskIcon(risk.level)}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-sm">{risk.category}</span>
              <Badge variant="outline" className="text-xs">
                {risk.level.toUpperCase()}
              </Badge>
              <Badge variant="secondary" className="text-xs">
                {risk.confidence} confidence
              </Badge>
            </div>
            <p className="text-sm mb-2">{risk.description}</p>
            {risk.impact && (
              <p className="text-xs text-gray-600 mb-1">
                <strong>Impact:</strong> {risk.impact}
              </p>
            )}
            {risk.recommendation && (
              <p className="text-xs text-gray-600">
                <strong>Recommendation:</strong> {risk.recommendation}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Close popup when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        popupRef.current &&
        !popupRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowCommandPopup(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!dd_id) return null;

  const handleExpand = () => {
    setIsExpanded(true);
  };

  if (!isExpanded) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <Button
          onClick={handleExpand}
          className="h-16 w-16 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 border-2 border-white text-white"
          style={{ backgroundColor: "#0a1845" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "#1a2755";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "#0a1845";
          }}
        >
          <MessageCircle className="h-7 w-7 text-white" />
        </Button>
      </div>
    );
  }

  const filteredItems = getFilteredItems();

  return (
    <>
      {/* Command Popup */}
      {showCommandPopup && (
        <div
          ref={popupRef}
          className="fixed z-[60] bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto w-80"
          style={{
            left: `${popupPosition.x}px`,
            top: `${popupPosition.y}px`,
          }}
        >
          <div className="p-2">
            <div className="text-xs text-gray-500 mb-2 px-2">
              Reference files and folders
            </div>
            {filteredItems.length === 0 ? (
              <div className="px-2 py-3 text-sm text-gray-500">
                No files or folders found
              </div>
            ) : (
              filteredItems.map((item, index) => (
                <div
                  key={`${item.type}-${item.id}`}
                  className={`flex items-center gap-2 px-2 py-2 rounded cursor-pointer text-sm ${
                    index === selectedIndex
                      ? "bg-blue-50 text-blue-700"
                      : "hover:bg-gray-50"
                  }`}
                  onClick={() => insertReference(item)}
                >
                  {item.type === "folder" ? (
                    <Folder className="w-4 h-4 text-blue-600" />
                  ) : (
                    <FileText className="w-4 h-4 text-gray-600" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="truncate font-medium">{item.name}</div>
                    {item.parentFolder && (
                      <div className="text-xs text-gray-500 truncate">
                        in {item.parentFolder}
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-gray-400">
                    {item.type === "folder" ? "Folder" : "File"}
                  </div>
                </div>
              ))
            )}
            <div className="border-t border-gray-100 mt-2 pt-2 px-2">
              <div className="text-xs text-gray-400">
                Type "/{">"}" to reference files and folders
              </div>
            </div>
          </div>
        </div>
      )}

      {/* NEW: Debug panel showing stored references (remove in production) */}
      {selectedReferences.length > 0 && (
        <div className="fixed bottom-20 right-6 bg-blue-50 border border-blue-200 rounded-lg p-2 text-xs max-w-80">
          <div className="font-medium text-blue-800 mb-1">
            Selected References:
          </div>
          {selectedReferences.map((ref, index) => (
            <div key={index} className="text-blue-600">
              {ref.textMarker} → {ref.type}: {ref.id}
            </div>
          ))}
        </div>
      )}

      {/* Chatbot Container */}
      <div
        className={`fixed z-50 transition-all duration-300 ${
          isFullScreen
            ? "inset-4 top-8 bottom-8 left-8 right-8"
            : "bottom-6 right-6"
        }`}
      >
        <Card
          className={`bg-white shadow-2xl border-2 border-blue-200 transition-all duration-300 ${
            isFullScreen
              ? "w-full h-full max-w-none"
              : `w-[500px] ${isMinimized ? "h-16" : "h-[600px]"}`
          }`}
        >
          {/* Header */}
          <CardHeader
            className="text-white p-4 rounded-t-lg"
            style={{ backgroundColor: "#0a1845" }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
                  <MessageCircle className="w-6 h-6" />
                </div>
                <div>
                  <CardTitle className="text-lg font-semibold">
                    AI Legal Assistant
                  </CardTitle>
                  <p className="text-blue-100 text-sm">Due Diligence Support</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsMinimized(!isMinimized)}
                  className="text-white hover:bg-white hover:bg-opacity-20 h-8 w-8 p-0"
                  disabled={isFullScreen}
                >
                  <Minimize2 className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleFullScreenToggle}
                  className="text-white hover:bg-white hover:bg-opacity-20 h-8 w-8 p-0"
                  title={
                    isFullScreen ? "Exit full screen" : "Enter full screen"
                  }
                >
                  <Maximize2 className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setIsExpanded(false);
                    setIsFullScreen(false);
                  }}
                  className="text-white hover:bg-white hover:bg-opacity-20 h-8 w-8 p-0"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardHeader>

          {/* Chat Content */}
          {!isMinimized && (
            <CardContent
              className={`flex flex-col p-0 ${
                isFullScreen
                  ? "h-[calc(100vh-88px-4rem)]"
                  : "h-[calc(600px-88px)]"
              }`}
            >
              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${
                      msg.type === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`${
                        isFullScreen ? "max-w-[60%]" : "max-w-[80%]"
                      } p-3 rounded-lg ${
                        msg.type === "user"
                          ? "bg-gradient-to-r from-yellow-400 to-yellow-500 text-gray-900 ml-4"
                          : "bg-white border border-gray-200 text-gray-800 mr-4 shadow-sm"
                      }`}
                    >
                      {msg.isLoading ? (
                        <div className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <p className="text-sm">{msg.content}</p>
                        </div>
                      ) : (
                        <>
                          {/* Search Scope Indicator */}
                          {msg.searchScope && msg.type === "bot" && (
                            <div className="mb-2">
                              <Badge variant="outline" className="text-xs">
                                {msg.searchScope === "entire_dd" &&
                                  "🔍 Searched entire due diligence"}
                                {msg.searchScope === "single_reference" &&
                                  "📄 Searched specific reference"}
                                {msg.searchScope === "multiple_references" &&
                                  "📚 Searched multiple references"}
                              </Badge>
                            </div>
                          )}

                          <div className="text-sm leading-relaxed">
                            <Markdown
                              components={{
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
                                blockquote: ({ children, ...props }) => (
                                  <div className="border-l-4 border-blue-500 bg-blue-50 p-2 my-2 rounded-r">
                                    <div className="flex items-start">
                                      <span className="text-blue-500 text-lg mr-2">
                                        "
                                      </span>
                                      <div className="flex-1 italic text-blue-900 text-sm">
                                        {children}
                                      </div>
                                    </div>
                                  </div>
                                ),
                                h2: ({ children, ...props }) => (
                                  <h2
                                    className="text-base font-semibold text-gray-900 border-b border-gray-200 pb-1 mb-2 mt-3"
                                    {...props}
                                  >
                                    {children}
                                  </h2>
                                ),
                                li: ({ children, ...props }) => (
                                  <li
                                    className="mb-1 leading-relaxed text-sm"
                                    {...props}
                                  >
                                    {children}
                                  </li>
                                ),
                                code: ({ children, ...props }) => {
                                  const text = children?.toString() || "";
                                  if (text.includes("Source:")) {
                                    return (
                                      <span className="inline-flex items-center px-1 py-0.5 rounded bg-gray-100 text-gray-700 text-xs font-mono border">
                                        📄 {text}
                                      </span>
                                    );
                                  }
                                  return (
                                    <code
                                      className="bg-gray-100 px-1 py-0.5 rounded text-xs"
                                      {...props}
                                    >
                                      {children}
                                    </code>
                                  );
                                },
                              }}
                            >
                              {msg.content}
                            </Markdown>
                          </div>

                          {/* Risk Assessment */}
                          {msg.risks && msg.risks.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-gray-200">
                              <div className="text-xs font-medium text-gray-600 mb-2">
                                ⚠️ Risk Assessment ({msg.risks.length} risk
                                {msg.risks.length !== 1 ? "s" : ""} identified)
                              </div>
                              <div className="space-y-2 max-h-32 overflow-y-auto">
                                {msg.risks.slice(0, 3).map((risk, index) => (
                                  <RiskIndicator key={index} risk={risk} />
                                ))}
                                {msg.risks.length > 3 && (
                                  <div className="text-xs text-gray-500 text-center py-1">
                                    ... and {msg.risks.length - 3} more risk
                                    {msg.risks.length - 3 !== 1 ? "s" : ""}
                                  </div>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Referenced Documents */}
                          {msg.referencedDocs &&
                            msg.referencedDocs.length > 0 && (
                              <div className="mt-3 pt-3 border-t border-gray-200">
                                <div className="text-xs font-medium text-gray-600 mb-2">
                                  📚 Referenced Documents (
                                  {msg.referencedDocs.length})
                                </div>
                                <div className="space-y-2">
                                  {msg.referencedDocs
                                    .slice(0, 3)
                                    .map((doc, index) => (
                                      <div
                                        key={index}
                                        className="flex items-center justify-between text-xs bg-gray-50 rounded p-2"
                                      >
                                        <div className="flex-1 min-w-0">
                                          <div className="font-medium truncate">
                                            {doc.filename}
                                          </div>
                                          <div className="text-gray-500">
                                            Page {doc.page_number}
                                          </div>
                                        </div>
                                        <DropdownMenu>
                                          <DropdownMenuTrigger asChild>
                                            <Button
                                              variant="ghost"
                                              size="icon"
                                              className="h-6 w-6"
                                            >
                                              <MoreVertical className="w-3 h-3" />
                                            </Button>
                                          </DropdownMenuTrigger>
                                          <DropdownMenuContent align="end">
                                            <DropdownMenuItem
                                              onClick={() =>
                                                viewFile(doc.doc_id)
                                              }
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
                                      </div>
                                    ))}
                                  {msg.referencedDocs.length > 3 && (
                                    <div className="text-xs text-gray-500 text-center">
                                      ... and {msg.referencedDocs.length - 3}{" "}
                                      more documents
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                        </>
                      )}
                      <p className="text-xs opacity-70 mt-2">
                        {msg.timestamp.toLocaleTimeString("en-ZA", {
                          hour: "2-digit",
                          minute: "2-digit",
                          timeZone: "Africa/Johannesburg",
                        })}
                      </p>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="p-4 bg-white border-t border-gray-200 relative">
                <div className="flex gap-2 items-end">
                  <Textarea
                    ref={inputRef}
                    placeholder="Ask about documents, risks, or legal matters... (type '/>' to reference files, Shift+Enter for new line)"
                    value={message}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    className="flex-1 min-h-[50px] max-h-45 resize-none border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                    rows={1}
                    disabled={mutateChat.isPending}
                  />
                  <Button
                    onClick={handleSendMessage}
                    disabled={!message.trim() || mutateChat.isPending || !dd_id}
                    className="text-white px-6 h-10"
                    style={{
                      backgroundColor: "#0a1845",
                    }}
                    onMouseEnter={(e) => {
                      if (!e.currentTarget.disabled) {
                        e.currentTarget.style.backgroundColor = "#1a2755";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!e.currentTarget.disabled) {
                        e.currentTarget.style.backgroundColor = "#0a1845";
                      }
                    }}
                  >
                    {mutateChat.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    </>
  );
}
