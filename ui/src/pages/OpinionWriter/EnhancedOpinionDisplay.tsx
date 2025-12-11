// ui/src/pages/OpinionWriter/EnhancedOpinionDisplay.tsx
// Updated version with change markup support

import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Clipboard, Save, Eye, EyeOff, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { createDiffMarkup } from "./opinion-markup-utils";

interface EnhancedOpinionDisplayProps {
  opinionText: string;
  originalText?: string;
  showChangeMarkup?: boolean;
  onToggleMarkup?: () => void;
  onAcceptChanges?: () => void;
  currentOpinionVersionInfo: {
    version: number;
    name: string;
    draft_id: string;
  } | null;
  copyToClipboard: () => void;
  copyingTextToClipboard: boolean;
  hasUnsavedChanges?: boolean;
  onSaveChanges?: () => void;
}

export const EnhancedOpinionDisplay = ({
  opinionText,
  originalText,
  showChangeMarkup = false,
  onToggleMarkup,
  onAcceptChanges,
  currentOpinionVersionInfo,
  copyToClipboard,
  copyingTextToClipboard,
  hasUnsavedChanges = false,
  onSaveChanges,
}: EnhancedOpinionDisplayProps) => {
  // Determine if we have AI changes to show
  const hasAIChanges =
    originalText && originalText !== opinionText && originalText.length > 0;

  // Generate marked-up text if we're showing changes
  const displayText =
    hasAIChanges && showChangeMarkup
      ? createDiffMarkup(originalText, opinionText)
      : opinionText;

  const scrollToSection = (section: string) => {
    const headings = document.querySelectorAll("h1, h2, h3");
    const targetHeading = Array.from(headings).find((heading) =>
      heading.textContent?.toLowerCase().includes(section.toLowerCase())
    );
    if (targetHeading) {
      targetHeading.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
      targetHeading.classList.add("bg-yellow-200");
      setTimeout(() => {
        targetHeading.classList.remove("bg-yellow-200");
      }, 2000);
    }
  };

  const wordCount = opinionText
    .split(/\s+/)
    .filter((word) => word.length > 0).length;
  const readingTime = Math.ceil(wordCount / 200);

  return (
    <div className="bg-white rounded-xl border p-6">
      <div className="mb-4">
        {currentOpinionVersionInfo && (
          <div className="text-sm text-gray-600 mb-2 flex items-center justify-between">
            <div>
              Draft version #{currentOpinionVersionInfo.version} (
              {currentOpinionVersionInfo.name})
              {hasUnsavedChanges && (
                <span className="ml-2 text-orange-600 font-medium flex items-center gap-1">
                  •{" "}
                  <span className="w-2 h-2 bg-orange-600 rounded-full animate-pulse"></span>
                  Unsaved changes
                </span>
              )}
            </div>
            {hasAIChanges && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-blue-600 font-medium">
                  AI modifications detected
                </span>
              </div>
            )}
          </div>
        )}
        <div className="text-sm text-gray-500 flex items-center justify-between">
          <span>
            Please check for accuracy and completeness
            {hasUnsavedChanges && (
              <span className="ml-2 text-orange-600">
                • Changes will be auto-saved shortly
              </span>
            )}
          </span>
        </div>
      </div>

      {/* Markup Control Bar - Only show if we have AI changes */}
      {hasAIChanges && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-100 border border-green-400 rounded"></div>
                  <span className="text-xs text-gray-700">Additions</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-red-100 border border-red-400 rounded"></div>
                  <span className="text-xs text-gray-700">Deletions</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {onToggleMarkup && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onToggleMarkup}
                  className="flex items-center gap-2"
                >
                  {showChangeMarkup ? (
                    <>
                      <EyeOff className="w-4 h-4" />
                      Hide Changes
                    </>
                  ) : (
                    <>
                      <Eye className="w-4 h-4" />
                      Show Changes
                    </>
                  )}
                </Button>
              )}
              {onAcceptChanges && showChangeMarkup && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={onAcceptChanges}
                  className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
                >
                  <Check className="w-4 h-4" />
                  Accept All Changes
                </Button>
              )}
            </div>
          </div>
          <div className="mt-2 text-xs text-gray-600">
            {showChangeMarkup
              ? "Showing AI-suggested changes in green (additions) and red (deletions)"
              : "Change markup hidden - click 'Show Changes' to review AI modifications"}
          </div>
        </div>
      )}

      <div className="relative">
        {/* Action buttons */}
        <div className="absolute top-2 right-2 z-10 flex gap-2">
          {hasUnsavedChanges && onSaveChanges && (
            <div
              className="bg-orange-100 hover:bg-orange-200 p-2 rounded cursor-pointer shadow-sm border border-orange-300 transition-colors"
              onClick={onSaveChanges}
              title="Save changes now"
            >
              <div className="flex items-center gap-1">
                <Save className="w-4 h-4 text-orange-700" />
                <span className="text-xs text-orange-700 font-medium">
                  Save
                </span>
              </div>
            </div>
          )}
          <div
            className="bg-white/90 hover:bg-white p-2 rounded cursor-pointer shadow-sm border transition-colors"
            onClick={copyToClipboard}
            title="Copy to clipboard"
          >
            <div className="flex items-center gap-1">
              <Clipboard
                className={cn(
                  "w-4 h-4 transition-colors",
                  copyingTextToClipboard
                    ? "text-green-600"
                    : "text-gray-500 hover:text-gray-700"
                )}
              />
              <span
                className={cn(
                  "text-xs transition-colors",
                  copyingTextToClipboard
                    ? "text-green-600"
                    : "text-gray-500 hover:text-gray-700"
                )}
              >
                {copyingTextToClipboard ? "Copied!" : "Copy"}
              </span>
            </div>
          </div>
        </div>

        <div className="max-h-[700px] overflow-y-auto p-6 rounded-lg bg-gray-50 border text-sm">
          {hasAIChanges && showChangeMarkup ? (
            // Render HTML with markup
            <div
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: displayText }}
            />
          ) : (
            // Render normal Markdown
            <Markdown
              className="prose prose-sm max-w-none"
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children }) => (
                  <a
                    href={href || "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 underline hover:text-blue-800 break-words"
                  >
                    {children}
                  </a>
                ),
                h1: ({ children }) => (
                  <h1 className="text-xl font-bold text-gray-900 mt-8 mb-4 pb-2 border-b border-gray-200">
                    {children}
                  </h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-lg font-semibold text-gray-800 mt-6 mb-3">
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-base font-medium text-gray-700 mt-4 mb-2">
                    {children}
                  </h3>
                ),
                h4: ({ children }) => (
                  <h4 className="text-sm font-medium text-gray-600 mt-3 mb-2">
                    {children}
                  </h4>
                ),
                code: ({ children, className }) => {
                  const isInline = !className?.includes("language-");
                  return isInline ? (
                    <span className="bg-blue-50 text-blue-800 px-1 py-0.5 rounded text-xs font-mono">
                      {children}
                    </span>
                  ) : (
                    <pre className="bg-gray-100 p-3 rounded overflow-x-auto">
                      <code>{children}</code>
                    </pre>
                  );
                },
                ul: ({ children }) => (
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal list-inside space-y-1 ml-4">
                    {children}
                  </ol>
                ),
                p: ({ children }) => (
                  <p className="mb-3 leading-relaxed text-gray-700 hover:bg-blue-50 hover:border-l-2 hover:border-blue-300 hover:pl-3 transition-all duration-200">
                    {children}
                  </p>
                ),
                strong: ({ children }) => (
                  <strong className="font-semibold text-gray-900">
                    {children}
                  </strong>
                ),
                em: ({ children }) => (
                  <em className="italic text-gray-800">{children}</em>
                ),
                table: ({ children }) => (
                  <div className="overflow-x-auto my-4">
                    <table className="min-w-full divide-y divide-gray-200 border border-gray-200">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="bg-gray-50">{children}</thead>
                ),
                th: ({ children }) => (
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="px-4 py-2 text-sm text-gray-900 border-b border-gray-200 break-words">
                    {children}
                  </td>
                ),
              }}
            >
              {displayText}
            </Markdown>
          )}
        </div>
      </div>

      {/* Quick navigation and stats */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs text-gray-500">Quick Navigation:</div>
          {hasAIChanges && (
            <div className="text-xs text-blue-600 flex items-center gap-1">
              <span className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></span>
              Draft modified by AI suggestions
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {[
            "Executive Summary",
            "Background",
            "Issues",
            "Opinion",
            "Recommendations",
            "Conclusion",
            "Sources",
          ].map((section) => (
            <button
              key={section}
              onClick={() => scrollToSection(section)}
              className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded transition-colors border"
            >
              {section}
            </button>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
          <span>Words: {wordCount}</span>
          <span>Est. reading time: {readingTime} min</span>
          {hasAIChanges && (
            <span className="text-blue-600 font-medium">• Modified by AI</span>
          )}
        </div>
      </div>
    </div>
  );
};
