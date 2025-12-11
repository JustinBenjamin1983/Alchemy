import { useEffect, useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  Bot,
  User,
  Send,
  Loader2,
  Sparkles,
  MessageCircle,
  Zap,
} from "lucide-react";

type Msg = {
  id: string;
  role: "assistant" | "user";
  content: string;
  ts: Date;
};

export function AgreementChat({
  contextTitle,
  contextPreview,
}: {
  contextTitle?: string;
  contextPreview?: string;
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);

  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          id: "intro",
          role: "assistant",
          ts: new Date(),
          content:
            `Hi! I'm your Agreement Assistant. I can *suggest clauses*, *rephrase sections*, and *outline structure*. ` +
            `This is a preview-only chat (no server calls yet).`,
        },
        ...(contextTitle
          ? [
              {
                id: "ctx-title",
                role: "assistant",
                ts: new Date(),
                content: `Context • Working title: **${contextTitle}**`,
              } as Msg,
            ]
          : []),
        ...(contextPreview
          ? [
              {
                id: "ctx-prev",
                role: "assistant",
                ts: new Date(),
                content:
                  "Context • Client brief (snippet):\n\n" +
                  "```\n" +
                  contextPreview.slice(0, 280) +
                  (contextPreview.length > 280 ? "…\n" : "\n") +
                  "```",
              } as Msg,
            ]
          : []),
      ]);
    }
  }, [messages.length, contextTitle, contextPreview]);

  const send = () => {
    if (!input.trim() || typing) return;
    const u: Msg = {
      id: String(Date.now()),
      role: "user",
      content: input,
      ts: new Date(),
    };
    setMessages((m) => [...m, u]);
    setInput("");
    setTyping(true);

    setTimeout(() => {
      const a: Msg = {
        id: String(Date.now() + 1),
        role: "assistant",
        ts: new Date(),
        content:
          `Got it. (Preview mode)\n\n` +
          `• I’d suggest a brief **Purpose/Definitions/Obligations/Term & Termination/Fees/Confidentiality/IP/Governing Law/Dispute Resolution** structure.\n` +
          `• For your request: “${u.content}”, I can propose a **draft clause** or a **rewrite** next.\n` +
          `• When you wire this up, route messages here to your agreement chat endpoint to replace this placeholder.`,
      };
      setMessages((m) => [...m, a]);
      setTyping(false);
    }, 650);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const quickPrompts = [
    "Draft a confidentiality clause tailored to SMEs",
    "Rewrite the termination clause to be clearer",
    "Suggest a liability cap with carve-outs",
    "Add a South Africa governing law & venue clause",
    "Propose a dispute resolution ladder (negotiation → mediation → arbitration)",
    "Tighten the IP ownership language for work-for-hire",
  ];

  return (
    <div className="space-y-4">
      {/* Header — blue→purple (matches AlchemioChat) */}
      <div className="rounded-xl p-4 text-white bg-gradient-to-r from-blue-600 to-purple-600">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-white/20 rounded-lg">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold">Agreement Assistant</h3>
            <p className="text-xs opacity-90">
              Preview chat (no backend calls)
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border">
        <div className="h-[400px] overflow-y-auto p-4 space-y-4">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex gap-3 ${
                m.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {m.role === "assistant" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-r from-blue-500 to-purple-500">
                  <Bot className="w-4 h-4 text-white" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  m.role === "user"
                    ? "bg-blue-600 text-white ml-auto"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                <div className="whitespace-pre-wrap">{m.content}</div>
                <div
                  className={`text-[10px] mt-1 opacity-70 ${
                    m.role === "user" ? "text-blue-100" : "text-gray-500"
                  }`}
                >
                  {m.ts.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </div>
              </div>
              {m.role === "user" && (
                <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-gray-600" />
                </div>
              )}
            </div>
          ))}

          {typing && (
            <div className="flex gap-3 justify-start">
              <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-r from-blue-500 to-purple-500">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="bg-gray-100 rounded-lg px-3 py-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  />
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {messages.length <= 2 && (
          <div className="border-t p-4">
            <div className="text-xs text-gray-500 mb-3 flex items-center gap-1">
              <Zap className="w-3 h-3" />
              Quick suggestions:
            </div>
            <div className="grid grid-cols-1 gap-2">
              {quickPrompts.slice(0, 3).map((p) => (
                <button
                  key={p}
                  onClick={() => setInput(p)}
                  className="text-left text-xs bg-gray-50 hover:bg-gray-100 rounded-lg p-2 transition-colors border"
                >
                  {p}
                </button>
              ))}
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="w-full mt-2 text-xs h-8"
            >
              Show more suggestions…
            </Button>
          </div>
        )}

        <div className="border-t p-4">
          <div className="flex gap-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              placeholder="Ask for a clause, rewrite, or structure idea…"
              className="flex-1 min-h-[40px] max-h-[100px] resize-none text-sm"
              disabled={typing}
            />
            <Button
              onClick={send}
              disabled={!input.trim() || typing}
              size="sm"
              className="h-[40px] px-3"
            >
              {typing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <span>Preview only — no changes applied to your agreement</span>
            <div className="flex items-center gap-1">
              <MessageCircle className="w-3 h-3" />
              {Math.max(0, messages.length - 1)} messages
            </div>
          </div>
        </div>
      </div>

      <Button
        variant="outline"
        size="sm"
        className="w-full"
        onClick={() =>
          setMessages((m) =>
            m.filter(
              (x) =>
                x.id === "intro" || x.id === "ctx-title" || x.id === "ctx-prev"
            )
          )
        }
      >
        Clear Chat (keep context)
      </Button>
    </div>
  );
}
