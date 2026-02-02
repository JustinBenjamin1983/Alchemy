/**
 * ValidationWizardModal - Human-in-the-Loop Checkpoint B
 *
 * A 4-step modal wizard for validating AI understanding after Pass 2 analysis.
 *
 * Step 1: Confirm Transaction Understanding - Answer AI-generated questions
 * Step 2: Confirm Financial Data - Validate extracted financial figures
 * Step 3: Missing Documents - Upload additional documents if available
 * Step 4: Review & Confirm - Final confirmation before proceeding
 */

import React, { useState, useCallback, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  ChevronLeft,
  ChevronRight,
  Check,
  X,
  AlertTriangle,
  FileText,
  Upload,
  HelpCircle,
  DollarSign,
  ClipboardCheck,
  Loader2,
  SkipForward,
  Building2,
} from "lucide-react";

import {
  CheckpointData,
  CheckpointResponses,
  UnderstandingQuestion,
  FinancialConfirmation,
  MissingDocument,
  EntityQuestion,
  QuestionResponse,
  FinancialResponse,
  MissingDocResponse,
  EntityResponse,
  useSubmitCheckpointResponse,
  useSkipCheckpoint,
} from "@/hooks/useValidationCheckpoint";

// ============================================
// Types
// ============================================

interface ValidationWizardModalProps {
  open: boolean;
  onClose: () => void;
  checkpoint: CheckpointData;
  ddId: string;
  onComplete?: () => void;
  onSkip?: () => void;
}

interface StepConfig {
  id: number;
  title: string;
  description: string;
  icon: React.ReactNode;
}

// ============================================
// Step Configurations
// ============================================

const STEPS: StepConfig[] = [
  {
    id: 1,
    title: "Understanding",
    description: "Confirm our understanding",
    icon: <HelpCircle className="h-4 w-4" />,
  },
  {
    id: 2,
    title: "Financials",
    description: "Confirm financial data",
    icon: <DollarSign className="h-4 w-4" />,
  },
  {
    id: 3,
    title: "Documents",
    description: "Additional documents",
    icon: <FileText className="h-4 w-4" />,
  },
  {
    id: 4,
    title: "Confirm",
    description: "Review & confirm",
    icon: <ClipboardCheck className="h-4 w-4" />,
  },
];

const ENTITY_STEPS: StepConfig[] = [
  {
    id: 1,
    title: "Entities",
    description: "Confirm entity relationships",
    icon: <Building2 className="h-4 w-4" />,
  },
];

// ============================================
// Helper Components
// ============================================

interface ImportanceBadgeProps {
  importance: "critical" | "high" | "medium" | "low";
}

function ImportanceBadge({ importance }: ImportanceBadgeProps) {
  const config = {
    critical: { label: "Critical", className: "bg-red-100 text-red-700 border-red-200" },
    high: { label: "High", className: "bg-orange-100 text-orange-700 border-orange-200" },
    medium: { label: "Medium", className: "bg-yellow-100 text-yellow-700 border-yellow-200" },
    low: { label: "Low", className: "bg-blue-100 text-blue-700 border-blue-200" },
  };

  const { label, className } = config[importance] || config.medium;

  return (
    <Badge variant="outline" className={className}>
      {label}
    </Badge>
  );
}

interface ConfidenceBadgeProps {
  confidence: number;
}

function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const pct = Math.round(confidence * 100);
  let className = "bg-gray-100 text-gray-700";

  if (pct >= 90) {
    className = "bg-green-100 text-green-700";
  } else if (pct >= 70) {
    className = "bg-blue-100 text-blue-700";
  } else if (pct >= 50) {
    className = "bg-yellow-100 text-yellow-700";
  } else {
    className = "bg-orange-100 text-orange-700";
  }

  return (
    <Badge variant="outline" className={className}>
      {pct}% confident
    </Badge>
  );
}

// ============================================
// Step 1: Understanding Questions
// ============================================

interface Step1Props {
  questions: UnderstandingQuestion[];
  responses: Record<string, QuestionResponse>;
  onResponseChange: (questionId: string, response: QuestionResponse) => void;
  preliminarySummary?: string;
}

function Step1Understanding({ questions, responses, onResponseChange, preliminarySummary }: Step1Props) {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const currentQuestion = questions[currentQuestionIndex];
  const totalQuestions = questions.length;

  const currentResponse = responses[currentQuestion?.question_id] || {
    selected_option: "",
    correction_text: "",
  };

  const handleOptionChange = (value: string) => {
    onResponseChange(currentQuestion.question_id, {
      ...currentResponse,
      selected_option: value,
    });
  };

  const handleCorrectionChange = (text: string) => {
    onResponseChange(currentQuestion.question_id, {
      ...currentResponse,
      correction_text: text,
    });
  };

  const goToNext = () => {
    if (currentQuestionIndex < totalQuestions - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  const goToPrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  if (!currentQuestion) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No questions to confirm. Your transaction details are clear.
      </div>
    );
  }

  const defaultOptions = [
    { value: "correct", label: "Yes, this is correct", description: "The AI understanding is accurate" },
    { value: "partial", label: "Partially correct", description: "Some aspects need clarification" },
    { value: "incorrect", label: "No, this is incorrect", description: "Please provide the correct information below" },
  ];

  const options = currentQuestion.options || defaultOptions;
  // Show correction field for any response that isn't a full confirmation
  // Handles various option values: "partial", "partially", "incorrect", "needs_correction", etc.
  const showCorrectionField = currentResponse.selected_option &&
    !["correct", "accurate", "agree", "confirmed", "yes"].includes(currentResponse.selected_option.toLowerCase());

  return (
    <div className="space-y-6">
      {/* Preliminary Summary */}
      {preliminarySummary && currentQuestionIndex === 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-2">
            Preliminary Summary
          </h4>
          <p className="text-sm text-blue-700 dark:text-blue-400">
            {preliminarySummary}
          </p>
        </div>
      )}

      {/* Question Progress */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>Question {currentQuestionIndex + 1} of {totalQuestions}</span>
        <div className="flex gap-1">
          {questions.map((q, idx) => (
            <button
              key={q.question_id}
              onClick={() => setCurrentQuestionIndex(idx)}
              className={`w-2 h-2 rounded-full transition-colors ${
                idx === currentQuestionIndex
                  ? "bg-alchemyPrimaryOrange"
                  : responses[q.question_id]?.selected_option
                  ? "bg-green-500"
                  : "bg-gray-300 dark:bg-gray-600"
              }`}
            />
          ))}
        </div>
      </div>

      {/* Question Card */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-5">
        <div className="flex items-start justify-between mb-4">
          <h4 className="text-base font-medium text-gray-900 dark:text-gray-100">
            {currentQuestion.question}
          </h4>
          {currentQuestion.confidence !== undefined && (
            <ConfidenceBadge confidence={currentQuestion.confidence} />
          )}
        </div>

        {/* AI Assessment */}
        {currentQuestion.ai_assessment && (
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 mb-4">
            <p className="text-sm text-gray-600 dark:text-gray-400 italic">
              "{currentQuestion.ai_assessment}"
            </p>
          </div>
        )}

        {/* Context */}
        {currentQuestion.context && (
          <p className="text-sm text-muted-foreground mb-4">
            {currentQuestion.context}
          </p>
        )}

        {/* Options */}
        <RadioGroup
          value={currentResponse.selected_option}
          onValueChange={handleOptionChange}
          className="space-y-3"
        >
          {options.map((option) => (
            <div
              key={option.value}
              className={`flex items-start space-x-3 p-3 rounded-lg border transition-colors cursor-pointer ${
                currentResponse.selected_option === option.value
                  ? "border-alchemyPrimaryOrange bg-orange-50 dark:bg-orange-900/20"
                  : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
              }`}
              onClick={() => handleOptionChange(option.value)}
            >
              <RadioGroupItem value={option.value} id={option.value} />
              <div className="flex-1">
                <Label
                  htmlFor={option.value}
                  className="text-sm font-medium cursor-pointer"
                >
                  {option.label}
                </Label>
                {option.description && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {option.description}
                  </p>
                )}
              </div>
            </div>
          ))}
        </RadioGroup>

        {/* Correction Text */}
        {showCorrectionField && (
          <div className="mt-4">
            <Label htmlFor="correction" className="text-sm font-medium mb-2 block">
              Please provide the correct information:
            </Label>
            <Textarea
              id="correction"
              placeholder="Enter your correction or clarification..."
              value={currentResponse.correction_text || ""}
              onChange={(e) => handleCorrectionChange(e.target.value)}
              className="min-h-[100px]"
            />
          </div>
        )}
      </div>

      {/* Navigation */}
      {totalQuestions > 1 && (
        <div className="flex justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={goToPrevious}
            disabled={currentQuestionIndex === 0}
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={goToNext}
            disabled={currentQuestionIndex === totalQuestions - 1}
          >
            Next
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      )}
    </div>
  );
}

// ============================================
// Step 2: Financial Confirmations
// ============================================

interface Step2Props {
  confirmations: FinancialConfirmation[];
  responses: FinancialResponse[];
  onResponseChange: (responses: FinancialResponse[]) => void;
  manualInputs: Record<string, number | string>;
  onManualInputChange: (inputs: Record<string, number | string>) => void;
}

function Step2Financials({
  confirmations,
  responses,
  onResponseChange,
  manualInputs,
  onManualInputChange,
}: Step2Props) {
  const formatCurrency = (value: number | null | undefined, currency = "ZAR") => {
    if (value === null || value === undefined) return "Not available";
    return new Intl.NumberFormat("en-ZA", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const handleConfirmationChange = (index: number, field: keyof FinancialResponse, value: unknown) => {
    const newResponses = [...responses];
    if (!newResponses[index]) {
      newResponses[index] = {
        metric: confirmations[index]?.metric || "",
        extracted_value: confirmations[index]?.extracted_value ?? null,
        confirmed_value: null,
        status: "correct",
      };
    }
    newResponses[index] = { ...newResponses[index], [field]: value };
    onResponseChange(newResponses);
  };

  const handleManualInput = (key: string, value: string) => {
    const numValue = value.replace(/[^0-9.-]/g, "");
    onManualInputChange({
      ...manualInputs,
      [key]: numValue ? parseFloat(numValue) : "",
    });
  };

  if (confirmations.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No financial figures to confirm.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Please confirm the key financial figures we extracted from your documents.
        Correct any inaccuracies to ensure accurate analysis.
      </p>

      <div className="space-y-4">
        {confirmations.map((conf, index) => {
          const response = responses[index] || {
            metric: conf.metric,
            extracted_value: conf.extracted_value,
            confirmed_value: null,
            status: "correct" as const,
          };

          return (
            <div
              key={conf.metric}
              className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {conf.metric}
                  </h4>
                  {conf.source_document && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Source: {conf.source_document}
                    </p>
                  )}
                </div>
                {conf.confidence !== undefined && (
                  <ConfidenceBadge confidence={conf.confidence} />
                )}
              </div>

              <div className="flex items-center gap-4 mb-3">
                <div className="flex-1">
                  <Label className="text-xs text-muted-foreground mb-1 block">
                    Extracted Value
                  </Label>
                  <div className="text-lg font-semibold">
                    {formatCurrency(conf.extracted_value, conf.currency)}
                  </div>
                </div>
              </div>

              <RadioGroup
                value={response.status}
                onValueChange={(value) =>
                  handleConfirmationChange(index, "status", value)
                }
                className="flex gap-4"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="correct" id={`${conf.metric}-correct`} />
                  <Label htmlFor={`${conf.metric}-correct`} className="text-sm cursor-pointer">
                    Correct
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="incorrect" id={`${conf.metric}-incorrect`} />
                  <Label htmlFor={`${conf.metric}-incorrect`} className="text-sm cursor-pointer">
                    Incorrect
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="not_available" id={`${conf.metric}-na`} />
                  <Label htmlFor={`${conf.metric}-na`} className="text-sm cursor-pointer">
                    Not in documents
                  </Label>
                </div>
              </RadioGroup>

              {response.status === "incorrect" && (
                <div className="mt-3">
                  <Label className="text-xs text-muted-foreground mb-1 block">
                    Correct Value ({conf.currency || "ZAR"})
                  </Label>
                  <Input
                    type="text"
                    placeholder="Enter correct value"
                    value={response.confirmed_value?.toString() || ""}
                    onChange={(e) => {
                      const num = parseFloat(e.target.value.replace(/[^0-9.-]/g, ""));
                      handleConfirmationChange(index, "confirmed_value", isNaN(num) ? null : num);
                    }}
                    className="h-9"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Manual Inputs Section */}
      <div className="border-t pt-4">
        <h4 className="text-sm font-medium mb-3">
          Missing Data (Optional)
        </h4>
        <p className="text-xs text-muted-foreground mb-4">
          If you have values that weren't in the documents but are important for analysis:
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="text-xs text-muted-foreground mb-1 block">
              EBITDA (ZAR)
            </Label>
            <Input
              type="text"
              placeholder="e.g., 28,000,000"
              value={manualInputs["ebitda"]?.toString() || ""}
              onChange={(e) => handleManualInput("ebitda", e.target.value)}
              className="h-9"
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground mb-1 block">
              Working Capital (ZAR)
            </Label>
            <Input
              type="text"
              placeholder="e.g., 15,000,000"
              value={manualInputs["working_capital"]?.toString() || ""}
              onChange={(e) => handleManualInput("working_capital", e.target.value)}
              className="h-9"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Step 3: Missing Documents
// ============================================

interface Step3Props {
  missingDocs: MissingDocument[];
  responses: Record<string, MissingDocResponse>;
  onResponseChange: (docType: string, response: MissingDocResponse) => void;
  onUpload?: (docType: string, file: File) => void;
}

function Step3Documents({ missingDocs, responses, onResponseChange, onUpload }: Step3Props) {
  const handleActionChange = (doc: MissingDocument, action: MissingDocResponse["action"]) => {
    onResponseChange(doc.doc_type, {
      doc_type: doc.doc_type,
      action,
    });
  };

  const handleNoteChange = (doc: MissingDocument, note: string) => {
    const current = responses[doc.doc_type] || { doc_type: doc.doc_type, action: "dont_have" };
    onResponseChange(doc.doc_type, {
      ...current,
      note,
    });
  };

  if (missingDocs.length === 0) {
    return (
      <div className="text-center py-8">
        <Check className="h-12 w-12 mx-auto text-green-500 mb-4" />
        <p className="text-muted-foreground">
          All expected documents have been provided. No additional documents needed.
        </p>
      </div>
    );
  }

  // Group by importance
  const groupedDocs = {
    critical: missingDocs.filter((d) => d.importance === "critical"),
    high: missingDocs.filter((d) => d.importance === "high"),
    medium: missingDocs.filter((d) => d.importance === "medium"),
  };

  const renderDocSection = (docs: MissingDocument[], title: string) => {
    if (docs.length === 0) return null;

    return (
      <div className="space-y-3">
        <h4 className="text-sm font-semibold flex items-center gap-2">
          <AlertTriangle className="h-4 w-4" />
          {title}
        </h4>
        {docs.map((doc) => {
          const response = responses[doc.doc_type];

          return (
            <div
              key={doc.doc_type}
              className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h5 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {doc.doc_type}
                  </h5>
                  <p className="text-xs text-muted-foreground mt-1">
                    {doc.description}
                  </p>
                  {doc.expected_folder && (
                    <p className="text-xs text-muted-foreground">
                      Expected in: {doc.expected_folder}
                    </p>
                  )}
                </div>
                <ImportanceBadge importance={doc.importance} />
              </div>

              <div className="text-xs text-muted-foreground mb-3 italic">
                {doc.reason}
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  variant={response?.action === "uploaded" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleActionChange(doc, "uploaded")}
                  className="text-xs"
                >
                  <Upload className="h-3 w-3 mr-1" />
                  Upload Now
                </Button>
                <Button
                  variant={response?.action === "dont_have" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleActionChange(doc, "dont_have")}
                  className="text-xs"
                >
                  Don't Have It
                </Button>
                <Button
                  variant={response?.action === "not_applicable" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleActionChange(doc, "not_applicable")}
                  className="text-xs"
                >
                  Not Applicable
                </Button>
              </div>

              {(response?.action === "dont_have" || response?.action === "not_applicable") && (
                <div className="mt-3">
                  <Input
                    placeholder="Add a note (optional)"
                    value={response?.note || ""}
                    onChange={(e) => handleNoteChange(doc, e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Based on your transaction type, we expected these documents but didn't find them.
        Please upload if available or indicate why they're not included.
      </p>

      {renderDocSection(groupedDocs.critical, "Critical Documents")}
      {renderDocSection(groupedDocs.high, "High Priority Documents")}
      {renderDocSection(groupedDocs.medium, "Medium Priority Documents")}
    </div>
  );
}

// ============================================
// Step 4: Review & Confirm
// ============================================

interface Step4Props {
  checkpoint: CheckpointData;
  questionResponses: Record<string, QuestionResponse>;
  financialResponses: FinancialResponse[];
  manualInputs: Record<string, number | string>;
  missingDocResponses: Record<string, MissingDocResponse>;
  onConfirm: () => void;
  onBack: () => void;
}

function Step4Review({
  checkpoint,
  questionResponses,
  financialResponses,
  manualInputs,
  missingDocResponses,
}: Step4Props) {
  const questions = (checkpoint.questions as UnderstandingQuestion[]) || [];
  const financials = checkpoint.financial_confirmations || [];
  const missingDocs = checkpoint.missing_docs || [];

  const questionsAnswered = Object.keys(questionResponses).length;
  const financialsConfirmed = financialResponses.filter((r) => r?.status).length;
  const docsAddressed = Object.keys(missingDocResponses).length;
  const corrections = Object.values(questionResponses).filter(
    (r) => r.selected_option === "incorrect" || r.selected_option === "partial"
  ).length;
  const financialCorrections = financialResponses.filter((r) => r?.status === "incorrect").length;
  const manualInputCount = Object.values(manualInputs).filter((v) => v !== "").length;

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-2">
          Updated Summary
        </h4>
        <p className="text-sm text-blue-700 dark:text-blue-400">
          {checkpoint.preliminary_summary || "Your responses have been recorded and will be incorporated into the analysis."}
        </p>
        {corrections > 0 && (
          <p className="text-sm text-blue-700 dark:text-blue-400 mt-2">
            <strong>{corrections} correction(s)</strong> will be applied to improve accuracy.
          </p>
        )}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-green-600">
            {questionsAnswered}/{questions.length}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Questions Answered
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-blue-600">
            {financialsConfirmed}/{financials.length}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Financials Confirmed
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-purple-600">
            {docsAddressed}/{missingDocs.length}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Documents Addressed
          </div>
        </div>
      </div>

      {/* Corrections Summary */}
      {(corrections > 0 || financialCorrections > 0 || manualInputCount > 0) && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-yellow-800 dark:text-yellow-300 mb-2">
            Changes to be Applied
          </h4>
          <ul className="text-sm text-yellow-700 dark:text-yellow-400 space-y-1">
            {corrections > 0 && (
              <li>• {corrections} understanding correction(s)</li>
            )}
            {financialCorrections > 0 && (
              <li>• {financialCorrections} financial figure correction(s)</li>
            )}
            {manualInputCount > 0 && (
              <li>• {manualInputCount} manual data input(s) added</li>
            )}
          </ul>
        </div>
      )}

      {/* Confirmation Message */}
      <div className="text-center py-4">
        <Check className="h-12 w-12 mx-auto text-green-500 mb-3" />
        <p className="text-sm text-muted-foreground">
          Click "Confirm & Continue" to proceed with the analysis using your validated inputs.
        </p>
      </div>
    </div>
  );
}

// ============================================
// Entity Confirmation Step (for entity_confirmation type)
// ============================================

interface EntityStepProps {
  entities: EntityQuestion[];
  responses: Record<string, EntityResponse>;
  onResponseChange: (entityName: string, response: EntityResponse) => void;
}

function EntityConfirmationStep({ entities, responses, onResponseChange }: EntityStepProps) {
  const relationshipOptions = [
    { value: "related_party", label: "Related Party", description: "Supplier, customer, or other related party" },
    { value: "subsidiary", label: "Subsidiary of Target", description: "Owned by the target company" },
    { value: "parent", label: "Parent/Holding Company", description: "Owns or controls the target" },
    { value: "counterparty", label: "Known Counterparty", description: "Not related, just a contract partner" },
    { value: "exclude", label: "Exclude", description: "Documents uploaded in error" },
    { value: "other", label: "Other", description: "Please specify below" },
  ];

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        We found entities that we couldn't confidently link to your target company.
        Please confirm their relationship:
      </p>

      {entities.map((entity) => {
        const response = responses[entity.entity_name] || {
          entity_name: entity.entity_name,
          relationship: "" as EntityResponse["relationship"],
        };

        return (
          <div
            key={entity.entity_name}
            className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {entity.entity_name}
                </h4>
                {entity.registration_number && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Reg: {entity.registration_number}
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  Appears in: {entity.appears_in_documents} document(s)
                </p>
              </div>
              {entity.confidence !== undefined && (
                <ConfidenceBadge confidence={entity.confidence} />
              )}
            </div>

            {entity.ai_assessment && (
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 mb-4">
                <p className="text-sm text-gray-600 dark:text-gray-400 italic">
                  AI Assessment: "{entity.ai_assessment}"
                </p>
              </div>
            )}

            <RadioGroup
              value={response.relationship}
              onValueChange={(value) =>
                onResponseChange(entity.entity_name, {
                  ...response,
                  relationship: value as EntityResponse["relationship"],
                })
              }
              className="space-y-2"
            >
              {relationshipOptions.map((option) => (
                <div
                  key={option.value}
                  className={`flex items-start space-x-3 p-2 rounded-lg border transition-colors cursor-pointer ${
                    response.relationship === option.value
                      ? "border-alchemyPrimaryOrange bg-orange-50 dark:bg-orange-900/20"
                      : "border-gray-200 dark:border-gray-700"
                  }`}
                  onClick={() =>
                    onResponseChange(entity.entity_name, {
                      ...response,
                      relationship: option.value as EntityResponse["relationship"],
                    })
                  }
                >
                  <RadioGroupItem value={option.value} id={`${entity.entity_name}-${option.value}`} />
                  <div className="flex-1">
                    <Label htmlFor={`${entity.entity_name}-${option.value}`} className="text-sm cursor-pointer">
                      {option.label}
                    </Label>
                    <p className="text-xs text-muted-foreground">{option.description}</p>
                  </div>
                </div>
              ))}
            </RadioGroup>

            {response.relationship === "other" && (
              <div className="mt-3">
                <Input
                  placeholder="Please describe the relationship..."
                  value={response.other_description || ""}
                  onChange={(e) =>
                    onResponseChange(entity.entity_name, {
                      ...response,
                      other_description: e.target.value,
                    })
                  }
                  className="h-9"
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function ValidationWizardModal({
  open,
  onClose,
  checkpoint,
  ddId,
  onComplete,
  onSkip,
}: ValidationWizardModalProps) {
  const [currentStep, setCurrentStep] = useState(1);

  // Responses state
  const [questionResponses, setQuestionResponses] = useState<Record<string, QuestionResponse>>({});
  const [financialResponses, setFinancialResponses] = useState<FinancialResponse[]>([]);
  const [manualInputs, setManualInputs] = useState<Record<string, number | string>>({});
  const [missingDocResponses, setMissingDocResponses] = useState<Record<string, MissingDocResponse>>({});
  const [entityResponses, setEntityResponses] = useState<Record<string, EntityResponse>>({});

  // API mutations
  const submitMutation = useSubmitCheckpointResponse();
  const skipMutation = useSkipCheckpoint();

  // Determine which steps to show based on checkpoint type
  const isEntityCheckpoint = checkpoint.checkpoint_type === "entity_confirmation";
  const steps = isEntityCheckpoint ? ENTITY_STEPS : STEPS;
  const totalSteps = steps.length;

  // Progress calculation
  const progressValue = (currentStep / totalSteps) * 100;

  // Get data from checkpoint
  const questions = (checkpoint.questions as UnderstandingQuestion[]) || [];
  const entities = (checkpoint.questions as EntityQuestion[]) || [];
  const financials = checkpoint.financial_confirmations || [];
  const missingDocs = checkpoint.missing_docs || [];

  // Navigation handlers
  const canGoNext = useMemo(() => {
    if (isEntityCheckpoint) {
      // For entity checkpoint, check if all entities have responses
      return entities.every((e) => entityResponses[e.entity_name]?.relationship);
    }

    switch (currentStep) {
      case 1:
        // At least one question should be answered (or no questions)
        return questions.length === 0 || Object.keys(questionResponses).length > 0;
      case 2:
        // At least one financial should be confirmed (or no financials)
        return financials.length === 0 || financialResponses.some((r) => r?.status);
      case 3:
        // Can always proceed from documents step
        return true;
      case 4:
        return true;
      default:
        return true;
    }
  }, [currentStep, isEntityCheckpoint, questions, questionResponses, financials, financialResponses, entities, entityResponses]);

  const handleNext = useCallback(() => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  }, [currentStep, totalSteps]);

  const handleBack = useCallback(() => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  }, [currentStep]);

  const handleSkip = useCallback(async () => {
    try {
      await skipMutation.mutateAsync({
        checkpointId: checkpoint.id,
        reason: "User skipped validation",
      });
      onSkip?.();
      onClose();
    } catch (error) {
      console.error("Failed to skip checkpoint:", error);
    }
  }, [checkpoint.id, skipMutation, onSkip, onClose]);

  const handleSubmit = useCallback(async () => {
    try {
      const responses: CheckpointResponses = {
        question_responses: questionResponses,
        financial_confirmations: financialResponses,
        manual_inputs: manualInputs,
        missing_doc_responses: missingDocResponses,
        entity_responses: entityResponses,
        step_4_confirmed: true,
      };

      await submitMutation.mutateAsync({
        checkpointId: checkpoint.id,
        responses,
      });

      onComplete?.();
      onClose();
    } catch (error) {
      console.error("Failed to submit checkpoint:", error);
    }
  }, [
    checkpoint.id,
    questionResponses,
    financialResponses,
    manualInputs,
    missingDocResponses,
    entityResponses,
    submitMutation,
    onComplete,
    onClose,
  ]);

  // Render current step content
  const renderStepContent = () => {
    if (isEntityCheckpoint) {
      return (
        <EntityConfirmationStep
          entities={entities}
          responses={entityResponses}
          onResponseChange={(entityName, response) =>
            setEntityResponses((prev) => ({ ...prev, [entityName]: response }))
          }
        />
      );
    }

    switch (currentStep) {
      case 1:
        return (
          <Step1Understanding
            questions={questions}
            responses={questionResponses}
            onResponseChange={(questionId, response) =>
              setQuestionResponses((prev) => ({ ...prev, [questionId]: response }))
            }
            preliminarySummary={checkpoint.preliminary_summary}
          />
        );
      case 2:
        return (
          <Step2Financials
            confirmations={financials}
            responses={financialResponses}
            onResponseChange={setFinancialResponses}
            manualInputs={manualInputs}
            onManualInputChange={setManualInputs}
          />
        );
      case 3:
        return (
          <Step3Documents
            missingDocs={missingDocs}
            responses={missingDocResponses}
            onResponseChange={(docType, response) =>
              setMissingDocResponses((prev) => ({ ...prev, [docType]: response }))
            }
          />
        );
      case 4:
        return (
          <Step4Review
            checkpoint={checkpoint}
            questionResponses={questionResponses}
            financialResponses={financialResponses}
            manualInputs={manualInputs}
            missingDocResponses={missingDocResponses}
            onConfirm={handleSubmit}
            onBack={handleBack}
          />
        );
      default:
        return null;
    }
  };

  const isSubmitting = submitMutation.isPending || skipMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="text-lg font-semibold">
              {isEntityCheckpoint ? "Entity Confirmation Required" : "Validation Checkpoint"}
            </DialogTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSkip}
              disabled={isSubmitting}
              className="text-muted-foreground hover:text-foreground"
            >
              <SkipForward className="h-4 w-4 mr-1" />
              Skip All
            </Button>
          </div>
          <DialogDescription>
            {isEntityCheckpoint
              ? "Confirm the relationship of entities found in your documents"
              : `Step ${currentStep} of ${totalSteps}: ${steps[currentStep - 1]?.description}`}
          </DialogDescription>
        </DialogHeader>

        {/* Progress */}
        {!isEntityCheckpoint && (
          <div className="px-1">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium">
                {steps[currentStep - 1]?.title}
              </span>
              <span className="text-sm text-muted-foreground">
                {Math.round(progressValue)}% complete
              </span>
            </div>
            <Progress value={progressValue} className="h-2" />

            {/* Step Indicators */}
            <div className="flex justify-between mt-4">
              {steps.map((step) => {
                const isCompleted = step.id < currentStep;
                const isCurrent = step.id === currentStep;

                return (
                  <div
                    key={step.id}
                    className={`flex flex-col items-center w-1/${totalSteps} ${
                      isCurrent
                        ? "text-alchemyPrimaryOrange"
                        : isCompleted
                        ? "text-green-600"
                        : "text-muted-foreground"
                    }`}
                  >
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
                        isCurrent
                          ? "bg-alchemyPrimaryOrange text-white"
                          : isCompleted
                          ? "bg-green-600 text-white"
                          : "bg-gray-200 dark:bg-gray-700"
                      }`}
                    >
                      {isCompleted ? <Check className="h-4 w-4" /> : step.icon}
                    </div>
                    <span className="text-xs mt-1 text-center hidden sm:block">
                      {step.title}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Step Content */}
        <div className="flex-1 overflow-y-auto py-4 px-1 min-h-[300px]">
          {renderStepContent()}
        </div>

        {/* Footer */}
        <DialogFooter className="border-t pt-4">
          <div className="flex justify-between w-full">
            <div>
              {currentStep > 1 && !isEntityCheckpoint && (
                <Button variant="outline" onClick={handleBack} disabled={isSubmitting}>
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Back
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              {currentStep < totalSteps && !isEntityCheckpoint ? (
                <Button
                  onClick={handleNext}
                  disabled={!canGoNext || isSubmitting}
                  className="bg-alchemyPrimaryOrange hover:bg-alchemyPrimaryOrange/90"
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={!canGoNext || isSubmitting}
                  className="bg-alchemyPrimaryOrange hover:bg-alchemyPrimaryOrange/90"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Check className="h-4 w-4 mr-1" />
                      Confirm & Continue
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ValidationWizardModal;
