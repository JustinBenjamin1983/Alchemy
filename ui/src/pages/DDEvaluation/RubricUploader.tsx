// pages/DDEvaluation/RubricUploader.tsx
/**
 * RubricUploader - Form for uploading/creating new rubrics from JSON
 */

import React, { useState, useRef } from "react";
import { useMutateCreateRubric } from "@/hooks/useMutateCreateRubric";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Loader2, Upload, FileJson, X, Check } from "lucide-react";
import { toast } from "sonner";

interface RubricUploaderProps {
  onSuccess: () => void;
  onCancel: () => void;
}

export const RubricUploader: React.FC<RubricUploaderProps> = ({
  onSuccess,
  onCancel,
}) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [jsonContent, setJsonContent] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const [parsedData, setParsedData] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const createRubric = useMutateCreateRubric();

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".json")) {
      toast.error("Please upload a JSON file");
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setJsonContent(content);
      validateJson(content);
    };
    reader.readAsText(file);
  };

  const validateJson = (content: string) => {
    try {
      const parsed = JSON.parse(content);
      setParsedData(parsed);
      setParseError(null);

      // Auto-fill name if present in JSON
      if (parsed.name && !name) {
        setName(parsed.name);
      }
      if (parsed.description && !description) {
        setDescription(parsed.description);
      }

      return true;
    } catch (err) {
      setParseError(err instanceof Error ? err.message : "Invalid JSON");
      setParsedData(null);
      return false;
    }
  };

  const handleJsonChange = (content: string) => {
    setJsonContent(content);
    if (content.trim()) {
      validateJson(content);
    } else {
      setParsedData(null);
      setParseError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      toast.error("Name is required");
      return;
    }

    if (!parsedData) {
      toast.error("Valid rubric JSON is required");
      return;
    }

    // Extract rubric_data from parsed JSON
    // Support both flat format (rubric_data at root) and wrapped format
    const rubricData = parsedData.rubric_data || parsedData;

    try {
      await createRubric.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        rubric_data: rubricData,
        total_points: parsedData.total_points,
      });
      onSuccess();
    } catch (err) {
      // Error handled by mutation
    }
  };

  const getSummary = () => {
    if (!parsedData) return null;

    const data = parsedData.rubric_data || parsedData;
    return {
      criticalRedFlags: data.critical_red_flags?.length || 0,
      amberFlags: data.amber_flags?.length || 0,
      crossDocConnections: data.cross_document_connections?.length || 0,
      missingDocs: data.missing_documents?.length || 0,
    };
  };

  const summary = getSummary();

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Create Evaluation Rubric
        </h2>
        <Button variant="ghost" size="sm" onClick={onCancel}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Name */}
        <div className="space-y-2">
          <Label htmlFor="name">Rubric Name *</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Karoo Mining Test"
            required
          />
        </div>

        {/* Description */}
        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief description of this rubric..."
            rows={2}
          />
        </div>

        {/* File Upload */}
        <div className="space-y-2">
          <Label>Rubric JSON</Label>
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="w-4 h-4 mr-2" />
              Upload JSON File
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileUpload}
              className="hidden"
            />
            <span className="text-sm text-gray-500">or paste below</span>
          </div>
        </div>

        {/* JSON Content */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="json">Rubric Data *</Label>
            {parsedData && !parseError && (
              <span className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                <Check className="w-3 h-3" />
                Valid JSON
              </span>
            )}
          </div>
          <Textarea
            id="json"
            value={jsonContent}
            onChange={(e) => handleJsonChange(e.target.value)}
            placeholder={`{
  "critical_red_flags": [
    {"name": "Missing Eskom CoC", "description": "...", "points": 10}
  ],
  "amber_flags": [...],
  "cross_document_connections": [...],
  "intelligent_questions": {"criteria": "...", "points": 15},
  "missing_documents": [...],
  "overall_quality": {"criteria": "...", "points": 5}
}`}
            rows={12}
            className="font-mono text-xs"
          />
          {parseError && (
            <p className="text-sm text-red-500">{parseError}</p>
          )}
        </div>

        {/* Summary Preview */}
        {summary && !parseError && (
          <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Rubric Summary
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-red-600">Critical Red Flags:</span>{" "}
                <strong>{summary.criticalRedFlags}</strong>
              </div>
              <div>
                <span className="text-amber-600">Amber Flags:</span>{" "}
                <strong>{summary.amberFlags}</strong>
              </div>
              <div>
                <span className="text-indigo-600">Cross-Doc:</span>{" "}
                <strong>{summary.crossDocConnections}</strong>
              </div>
              <div>
                <span className="text-gray-600">Missing Docs:</span>{" "}
                <strong>{summary.missingDocs}</strong>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={createRubric.isPending || !parsedData || !!parseError}
          >
            {createRubric.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <FileJson className="w-4 h-4 mr-2" />
                Create Rubric
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default RubricUploader;
