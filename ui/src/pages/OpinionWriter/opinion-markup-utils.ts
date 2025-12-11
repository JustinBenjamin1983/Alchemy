// ui/src/pages/OpinionWriter/opinion-markup-utils.ts
// Utility functions for marking up opinion changes

export interface VisualChange {
  id: string;
  type: "replace" | "insert" | "delete";
  startIndex: number;
  endIndex: number;
  originalText?: string;
  newText: string;
  applied: boolean;
}

/**
 * Creates a diff-based markup by comparing original and modified text
 * Shows additions in green and deletions in red with strikethrough
 */
export function createDiffMarkup(
  originalText: string,
  modifiedText: string
): string {
  // Split by lines to handle markdown better
  const originalLines = originalText.split("\n");
  const modifiedLines = modifiedText.split("\n");

  const result: string[] = [];
  let i = 0,
    j = 0;

  while (i < originalLines.length || j < modifiedLines.length) {
    if (i < originalLines.length && j < modifiedLines.length) {
      if (originalLines[i] === modifiedLines[j]) {
        // Line unchanged
        result.push(modifiedLines[j]);
        i++;
        j++;
      } else {
        // Line changed - show deletion and addition
        if (originalLines[i].trim()) {
          result.push(
            `<span class="change-deletion" style="background-color: #ffd7d5; color: #a02620; text-decoration: line-through; display: block; padding: 2px 4px; margin: 1px 0;">${escapeHtml(
              originalLines[i]
            )}</span>`
          );
        }
        if (modifiedLines[j].trim()) {
          result.push(
            `<span class="change-addition" style="background-color: #d4f4dd; color: #0a5f0a; font-weight: 500; display: block; padding: 2px 4px; margin: 1px 0;">${escapeHtml(
              modifiedLines[j]
            )}</span>`
          );
        }
        i++;
        j++;
      }
    } else if (j < modifiedLines.length) {
      // Addition
      if (modifiedLines[j].trim()) {
        result.push(
          `<span class="change-addition" style="background-color: #d4f4dd; color: #0a5f0a; font-weight: 500; display: block; padding: 2px 4px; margin: 1px 0;">${escapeHtml(
            modifiedLines[j]
          )}</span>`
        );
      } else {
        result.push(modifiedLines[j]);
      }
      j++;
    } else if (i < originalLines.length) {
      // Deletion
      if (originalLines[i].trim()) {
        result.push(
          `<span class="change-deletion" style="background-color: #ffd7d5; color: #a02620; text-decoration: line-through; display: block; padding: 2px 4px; margin: 1px 0;">${escapeHtml(
            originalLines[i]
          )}</span>`
        );
      } else {
        result.push(originalLines[i]);
      }
      i++;
    }
  }

  return result.join("\n");
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
