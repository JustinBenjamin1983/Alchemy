/**
 * Example Integration: How to use ReportVersionManager
 *
 * This file shows how to integrate the ReportVersionManager component
 * into your existing Findings Explorer or Report views.
 */

import React, { useState } from "react";
import { ReportVersionManager } from "./ReportVersionManager";
import {
  useReportVersions,
  useReportVersion,
  useCompareVersions,
  useProposeRefinement,
  useMergeRefinement,
} from "@/hooks/useReportVersions";

// ============================================
// Example 1: Basic Integration in Findings Explorer
// ============================================

interface FindingsExplorerExampleProps {
  ddId: string;
  runId: string;
  projectName?: string;
}

export function FindingsExplorerExample({ ddId, runId, projectName }: FindingsExplorerExampleProps) {
  const [activeVersion, setActiveVersion] = useState<number | null>(null);

  // Get the content for the selected version
  const { data: versionData } = useReportVersion(runId, activeVersion, !!activeVersion);

  return (
    <div className="space-y-6">
      {/* Version Manager Component */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <ReportVersionManager
          runId={runId}
          ddId={ddId}
          projectName={projectName}
          onVersionChange={(version) => {
            console.log("Version changed to:", version);
            setActiveVersion(version);
          }}
        />
      </div>

      {/* Display version content */}
      {versionData?.content && (
        <div className="space-y-4">
          {/* Executive Summary */}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3">Executive Summary</h3>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
              {String(versionData.content.executive_summary || '')}
            </p>
          </div>

          {/* Deal Assessment */}
          {versionData.content.deal_assessment && (
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-3">Deal Assessment</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm font-medium">Can Proceed:</span>
                  <span className={`ml-2 ${(versionData.content.deal_assessment as Record<string, unknown>).can_proceed ? 'text-green-600' : 'text-red-600'}`}>
                    {(versionData.content.deal_assessment as Record<string, unknown>).can_proceed ? 'Yes' : 'No'}
                  </span>
                </div>
                <div>
                  <span className="text-sm font-medium">Risk Rating:</span>
                  <span className="ml-2 capitalize">
                    {String((versionData.content.deal_assessment as Record<string, unknown>).overall_risk_rating || '')}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Rest of the findings explorer content... */}
        </div>
      )}
    </div>
  );
}

// ============================================
// Example 2: Synthesis View with Version Manager
// ============================================

export function SynthesisViewExample({ ddId, runId }: { ddId: string; runId: string }) {
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const { data: versionData, isLoading } = useReportVersion(runId, selectedVersion, !!selectedVersion);

  return (
    <div className="flex flex-col h-full">
      {/* Sticky Header with Version Manager */}
      <div className="sticky top-0 z-10 bg-background border-b pb-4 mb-4">
        <ReportVersionManager
          runId={runId}
          ddId={ddId}
          onVersionChange={setSelectedVersion}
        />
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="text-center py-8 text-muted-foreground">
            Loading version content...
          </div>
        ) : versionData?.content ? (
          <div className="space-y-6">
            {/* Your synthesis view content here */}
            <pre className="text-xs bg-gray-50 p-4 rounded overflow-auto">
              {JSON.stringify(versionData.content, null, 2)}
            </pre>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            Select a version to view its content
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================
// Example 3: Programmatic Refinement
// ============================================

export function ProgrammaticRefinementExample({ runId }: { runId: string }) {
  const [prompt, setPrompt] = useState("");
  const [proposal, setProposal] = useState<unknown>(null);

  const proposeMutation = useProposeRefinement();
  const mergeMutation = useMergeRefinement();

  const handlePropose = async () => {
    try {
      const result = await proposeMutation.mutateAsync({ runId, prompt });
      setProposal(result.proposal);
      console.log("Proposal received:", result);
    } catch (error) {
      console.error("Failed to propose:", error);
    }
  };

  const handleAccept = async () => {
    if (!proposal) return;

    try {
      const result = await mergeMutation.mutateAsync({
        runId,
        proposal: proposal as never,
        action: "merge",
      });
      console.log("Merged:", result);
      setProposal(null);
      setPrompt("");
    } catch (error) {
      console.error("Failed to merge:", error);
    }
  };

  return (
    <div className="space-y-4 p-4">
      <div>
        <label className="block text-sm font-medium mb-2">
          Refinement Prompt
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          className="w-full border rounded p-2"
          placeholder="Describe what you want to change..."
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={handlePropose}
          disabled={proposeMutation.isPending || !prompt}
          className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
        >
          {proposeMutation.isPending ? "Generating..." : "Generate Proposal"}
        </button>

        {proposal && (
          <>
            <button
              onClick={handleAccept}
              disabled={mergeMutation.isPending}
              className="px-4 py-2 bg-green-500 text-white rounded disabled:opacity-50"
            >
              {mergeMutation.isPending ? "Accepting..." : "Accept"}
            </button>
            <button
              onClick={() => setProposal(null)}
              className="px-4 py-2 bg-gray-500 text-white rounded"
            >
              Discard
            </button>
          </>
        )}
      </div>

      {proposal && (
        <div className="bg-gray-100 p-4 rounded">
          <h4 className="font-medium mb-2">Proposal:</h4>
          <pre className="text-xs overflow-auto">
            {JSON.stringify(proposal, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// ============================================
// Example 4: Version Comparison Utility
// ============================================

export function VersionComparisonExample({ runId }: { runId: string }) {
  const { data: versionsData } = useReportVersions(runId);
  const compareMutation = useCompareVersions();

  const versions = versionsData?.versions || [];

  const handleCompare = async (v1: number, v2: number) => {
    try {
      const result = await compareMutation.mutateAsync({
        runId,
        version1: v1,
        version2: v2,
      });
      console.log("Comparison result:", result);
    } catch (error) {
      console.error("Failed to compare:", error);
    }
  };

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-4">Version Comparison</h3>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {versions.slice(0, 4).map((v) => (
          <div
            key={v.version}
            className="p-3 border rounded cursor-pointer hover:bg-gray-50"
            onClick={() => {
              // Compare with previous version if exists
              const prevVersion = versions.find((pv) => pv.version === v.version - 1);
              if (prevVersion) {
                handleCompare(prevVersion.version, v.version);
              }
            }}
          >
            <div className="font-medium">Version {v.version}</div>
            <div className="text-sm text-muted-foreground">
              {v.change_summary || "Initial version"}
            </div>
          </div>
        ))}
      </div>

      {compareMutation.isPending && (
        <div className="text-center py-4">Comparing...</div>
      )}

      {compareMutation.data && (
        <div className="bg-gray-50 p-4 rounded">
          <h4 className="font-medium mb-2">
            {compareMutation.data.total_changes} change(s) found
          </h4>
          <pre className="text-xs overflow-auto">
            {JSON.stringify(compareMutation.data.diffs, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// ============================================
// Example 5: Using in a Page Layout
// ============================================

interface ReportPageLayoutProps {
  ddId: string;
  runId: string;
  projectName: string;
}

export function ReportPageLayout({ ddId, runId, projectName }: ReportPageLayoutProps) {
  const [activeTab, setActiveTab] = useState<"summary" | "findings" | "versions">("summary");

  return (
    <div className="h-screen flex flex-col">
      {/* Top Bar with Version Manager */}
      <header className="border-b p-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">{projectName} - DD Report</h1>
        <ReportVersionManager
          runId={runId}
          ddId={ddId}
          projectName={projectName}
        />
      </header>

      {/* Tab Navigation */}
      <nav className="border-b px-4">
        <div className="flex gap-4">
          {(["summary", "findings", "versions"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-4 border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-4">
        {activeTab === "summary" && (
          <div>Executive Summary content...</div>
        )}
        {activeTab === "findings" && (
          <div>Findings list...</div>
        )}
        {activeTab === "versions" && (
          <VersionComparisonExample runId={runId} />
        )}
      </main>
    </div>
  );
}

export default FindingsExplorerExample;
