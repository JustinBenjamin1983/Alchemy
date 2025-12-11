import { useEffect, useState } from "react";
import Markdown from "react-markdown";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  Sparkles,
  Loader2,
  Send,
  Bot,
  User,
  Zap,
  Save,
  MessageCircle,
  Maximize2,
  Minimize2,
  X as CloseIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAlchemioChat } from "@/hooks/useAlchemioChat";
import {
  AlchemioChatProps,
  ChatMessage,
  PendingChange,
  ChangesuggestionItem,
} from "./types";

export const AlchemioChat = ({
  opinionText,
  opinionVersionInfo,
  selectedOpinionId,
  onOpinionChange,
}: AlchemioChatProps) => {
  // Enhanced state management
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [pendingChanges, setPendingChanges] = useState<PendingChange[]>([]);
  const [showChangePreview, setShowChangePreview] = useState(false);
  const [previewText, setPreviewText] = useState<string>("");
  const [activeChangeId, setActiveChangeId] = useState<string | null>(null);

  // New state for floating dialog
  const [isFloatingMode, setIsFloatingMode] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);

  const alchemioChat = useAlchemioChat();

  // Initialize with welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          id: "1",
          role: "assistant",
          content: `Hi! I'm Alchemio, your legal opinion assistant. I can help you refine and improve your opinion. You can ask me to make specific changes like "make the conclusion more concise" or "add a risk analysis section." What would you like to work on?`,
          timestamp: new Date(),
        },
      ]);
    }
  }, []);

  const sendMessage = async () => {
    if (!inputMessage.trim() || alchemioChat.isPending) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = inputMessage;
    setInputMessage("");
    setIsTyping(true);

    try {
      const chatHistoryForAPI = messages
        .filter((msg) => msg.id !== "1")
        .map((msg) => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp.toISOString(),
        }));

      const response = await alchemioChat.mutateAsync({
        opinion_id: selectedOpinionId,
        message: currentInput,
        opinion_text: opinionText,
        chat_history: chatHistoryForAPI,
        request_changes: true,
      });

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.response,
        timestamp: new Date(response.timestamp),
        changeSuggestions: response.changes || undefined,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (response.changes && response.changes.changes.length > 0) {
        const newPendingChanges = response.changes.changes.map((change) => ({
          ...change,
          applied: false,
          previewMode: false,
        }));
        setPendingChanges((prev) => [...prev, ...newPendingChanges]);
      }
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          "I apologize, but I encountered an error processing your request. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const applyChange = (changeId: string) => {
    const change = pendingChanges.find((c) => c.id === changeId);
    if (!change) return;

    let newText = opinionText;
    switch (change.type) {
      case "replace":
        newText =
          opinionText.substring(0, change.startIndex) +
          change.newText +
          opinionText.substring(change.endIndex);
        break;
      case "insert":
        newText =
          opinionText.substring(0, change.startIndex) +
          change.newText +
          opinionText.substring(change.startIndex);
        break;
      case "delete":
        newText =
          opinionText.substring(0, change.startIndex) +
          opinionText.substring(change.endIndex);
        break;
    }

    // Pass the change metadata along with the new text
    onOpinionChange(newText, {
      id: change.id,
      type: change.type,
      startIndex: change.startIndex,
      endIndex: change.endIndex,
      originalText: change.originalText,
      newText: change.newText,
      reasoning: change.reasoning,
    });

    setPendingChanges((prev) =>
      prev.map((c) => (c.id === changeId ? { ...c, applied: true } : c))
    );
  };

  const previewChange = (changeId: string) => {
    const change = pendingChanges.find((c) => c.id === changeId);
    if (!change) return;

    let newText = opinionText;

    switch (change.type) {
      case "replace":
        newText =
          opinionText.substring(0, change.startIndex) +
          change.newText +
          opinionText.substring(change.endIndex);
        break;
      case "insert":
        newText =
          opinionText.substring(0, change.startIndex) +
          change.newText +
          opinionText.substring(change.startIndex);
        break;
      case "delete":
        newText =
          opinionText.substring(0, change.startIndex) +
          opinionText.substring(change.endIndex);
        break;
    }

    setPreviewText(newText);
    setActiveChangeId(changeId);
    setShowChangePreview(true);
  };

  const applyAllChanges = () => {
    let newText = opinionText;
    const sortedChanges = [...pendingChanges]
      .filter((c) => !c.applied)
      .sort((a, b) => b.startIndex - a.startIndex);

    // Apply all changes to get the final text
    sortedChanges.forEach((change) => {
      switch (change.type) {
        case "replace":
          newText =
            newText.substring(0, change.startIndex) +
            change.newText +
            newText.substring(change.endIndex);
          break;
        case "insert":
          newText =
            newText.substring(0, change.startIndex) +
            change.newText +
            newText.substring(change.startIndex);
          break;
        case "delete":
          newText =
            newText.substring(0, change.startIndex) +
            newText.substring(change.endIndex);
          break;
      }
    });

    // Prepare changes for tracking
    const changesToApply = sortedChanges.reverse().map((change) => ({
      id: change.id,
      type: change.type,
      startIndex: change.startIndex,
      endIndex: change.endIndex,
      originalText: change.originalText,
      newText: change.newText,
      reasoning: change.reasoning,
    }));

    // Pass all changes to parent
    onOpinionChange(newText, changesToApply);

    setPendingChanges((prev) => prev.map((c) => ({ ...c, applied: true })));
  };

  const clearPendingChanges = () => {
    setPendingChanges([]);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const suggestionPrompts = [
    "Make the executive summary more concise",
    "Add stronger legal precedents to the analysis",
    "Improve the conclusion section",
    "Simplify the complex legal language in paragraph 3",
    "Add a risk analysis section before the conclusion",
    "Restructure the background section for better flow",
  ];

  const useSuggestion = (prompt: string) => {
    setInputMessage(prompt);
  };

  // Render the chat interface (used in both normal and floating mode)
  const renderChatInterface = (isFloating: boolean = false) => {
    const chatHeight = isFloating
      ? isMaximized
        ? "calc(100vh - 280px)"
        : "calc(90vh - 280px)"
      : "400px";

    return (
      <div className="space-y-4">
        {/* Chat Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-4 text-white">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-lg">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold">Alchemio</h3>
                <p className="text-sm opacity-90">Legal Opinion Assistant</p>
              </div>
            </div>
            {isFloating ? (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsMaximized(!isMaximized)}
                  className="h-8 w-8 p-0 hover:bg-white/20 text-white"
                >
                  {isMaximized ? (
                    <Minimize2 className="w-4 h-4" />
                  ) : (
                    <Maximize2 className="w-4 h-4" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsFloatingMode(false)}
                  className="h-8 w-8 p-0 hover:bg-white/20 text-white"
                >
                  <CloseIcon className="w-4 h-4" />
                </Button>
              </div>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsFloatingMode(true)}
                className="h-8 px-3 hover:bg-white/20 text-white flex items-center gap-2"
              >
                <Maximize2 className="w-4 h-4" />
                <span className="text-xs font-medium">Expand</span>
              </Button>
            )}
          </div>
          <div className="text-xs opacity-80">
            {opinionVersionInfo
              ? `Working on v${opinionVersionInfo.version} (${opinionVersionInfo.name})`
              : "Ready to help improve your opinion"}
          </div>
          {pendingChanges.filter((c) => !c.applied).length > 0 && (
            <div className="mt-2 p-2 bg-white/10 rounded-lg">
              <div className="text-xs font-medium">
                {pendingChanges.filter((c) => !c.applied).length} pending
                change(s)
              </div>
            </div>
          )}
        </div>

        {/* Pending Changes Section */}
        {pendingChanges.filter((c) => !c.applied).length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-amber-800 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Suggested Changes
              </h4>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={applyAllChanges}
                  className="bg-amber-600 hover:bg-amber-700 text-white"
                >
                  Apply All
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={clearPendingChanges}
                >
                  Clear
                </Button>
              </div>
            </div>
            <div
              className={cn(
                "space-y-2 overflow-y-auto",
                isFloating ? "max-h-64" : "max-h-48"
              )}
            >
              {pendingChanges
                .filter((c) => !c.applied)
                .map((change) => (
                  <div
                    key={change.id}
                    className="bg-white border border-amber-200 rounded-lg p-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded text-xs font-medium",
                              change.priority === "high"
                                ? "bg-red-100 text-red-700"
                                : change.priority === "medium"
                                ? "bg-yellow-100 text-yellow-700"
                                : "bg-green-100 text-green-700"
                            )}
                          >
                            {change.type}
                          </span>
                          {change.section && (
                            <span className="text-xs text-gray-500">
                              {change.section}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-700 mb-1">
                          {change.reasoning}
                        </p>
                        {change.originalText && (
                          <div className="text-xs">
                            <span className="text-red-600 line-through">
                              {change.originalText.substring(0, 50)}
                              {change.originalText.length > 50 ? "..." : ""}
                            </span>
                            {change.newText && (
                              <>
                                <span className="mx-1">→</span>
                                <span className="text-green-600">
                                  {change.newText.substring(0, 50)}
                                  {change.newText.length > 50 ? "..." : ""}
                                </span>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => previewChange(change.id)}
                          className="h-8 px-2"
                        >
                          Preview
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => applyChange(change.id)}
                          className="h-8 px-2"
                        >
                          Apply
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Chat Messages */}
        <div className="bg-white rounded-xl border">
          <div
            className="overflow-y-auto p-4 space-y-4"
            style={{ height: chatHeight }}
          >
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3",
                  message.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {message.role === "assistant" && (
                  <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-[80%] rounded-lg px-3 py-2 text-sm",
                    message.role === "user"
                      ? "bg-blue-600 text-white ml-auto"
                      : "bg-gray-100 text-gray-900"
                  )}
                >
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  {message.changeSuggestions && (
                    <div className="mt-2 pt-2 border-t border-gray-200">
                      <div className="text-xs text-gray-600 flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        {message.changeSuggestions.changes.length} change(s)
                        suggested
                        <span className="ml-1 bg-blue-100 text-blue-700 px-1 rounded">
                          {Math.round(
                            message.changeSuggestions.confidence * 100
                          )}
                          % confident
                        </span>
                      </div>
                    </div>
                  )}
                  <div
                    className={cn(
                      "text-xs mt-1 opacity-70",
                      message.role === "user"
                        ? "text-blue-100"
                        : "text-gray-500"
                    )}
                  >
                    {message.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
                {message.role === "user" && (
                  <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                    <User className="w-4 h-4 text-gray-600" />
                  </div>
                )}
              </div>
            ))}
            {isTyping && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="bg-gray-100 rounded-lg px-3 py-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.1s" }}
                    ></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    ></div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Quick Suggestions */}
          {messages.length <= 1 && (
            <div className="border-t p-4">
              <div className="text-xs text-gray-500 mb-3 flex items-center gap-1">
                <Zap className="w-3 h-3" />
                Quick suggestions for changes:
              </div>
              <div className="grid grid-cols-1 gap-2">
                {suggestionPrompts.slice(0, 3).map((prompt, index) => (
                  <button
                    key={index}
                    onClick={() => useSuggestion(prompt)}
                    className="text-left text-xs bg-gray-50 hover:bg-gray-100 rounded-lg p-2 transition-colors border"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Chat Input */}
          <div className="border-t p-4">
            <div className="flex gap-2">
              <Textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask me to make specific changes to your opinion..."
                className="flex-1 min-h-[40px] max-h-[100px] resize-none text-sm"
                disabled={alchemioChat.isPending}
              />
              <Button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || alchemioChat.isPending}
                size="sm"
                className="h-[40px] px-3"
              >
                {alchemioChat.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
            <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
              <span>
                Ask for specific changes like "make paragraph 2 more concise"
              </span>
              <div className="flex items-center gap-1">
                <MessageCircle className="w-3 h-3" />
                {messages.length - 1} messages
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="space-y-2">
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={applyAllChanges}
            disabled={pendingChanges.filter((c) => !c.applied).length === 0}
          >
            <Save className="w-4 h-4 mr-2" />
            Apply All Suggestions (
            {pendingChanges.filter((c) => !c.applied).length})
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="w-full text-xs h-8"
            onClick={() => setMessages(messages.slice(0, 1))}
          >
            Clear Chat
          </Button>
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Normal inline mode */}
      <div className="relative">
        {renderChatInterface(false)}

        {/* Expand button */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsFloatingMode(true)}
          className="w-full mt-2 flex items-center gap-2"
        >
          <Maximize2 className="w-4 h-4" />
          Expand Chat
        </Button>
      </div>

      {/* Floating Dialog Mode */}
      <Dialog open={isFloatingMode} onOpenChange={setIsFloatingMode}>
        <DialogContent
          className={cn(
            "transition-all duration-300 ease-in-out",
            isMaximized
              ? "w-screen h-screen max-w-none m-0 rounded-none"
              : "w-[90vw] h-[90vh] max-w-[1400px]"
          )}
        >
          <div className="h-full flex flex-col overflow-hidden">
            {renderChatInterface(true)}
          </div>
        </DialogContent>
      </Dialog>

      {/* Change Preview Dialog */}
      <Dialog open={showChangePreview} onOpenChange={setShowChangePreview}>
        <DialogContent className="max-w-4xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>Preview Change</DialogTitle>
            <DialogDescription>
              Review the proposed change before applying it to your opinion.
            </DialogDescription>
          </DialogHeader>
          <div className="overflow-y-auto max-h-[60vh] p-4 bg-gray-50 rounded-lg">
            <Markdown className="prose prose-sm max-w-none">
              {previewText}
            </Markdown>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowChangePreview(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (activeChangeId) {
                  applyChange(activeChangeId);
                  setShowChangePreview(false);
                }
              }}
            >
              Apply Change
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};
