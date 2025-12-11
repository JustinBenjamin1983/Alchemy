import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ChevronLeft, ChevronRight, Check, Loader2, Save, Cloud, CloudOff } from "lucide-react";
import { DDProjectSetup, DEFAULT_PROJECT_SETUP } from "./types";
import { Step1TransactionBasics } from "./Step1TransactionBasics";
import { Step2DealContext } from "./Step2DealContext";
import { Step3FocusAreas } from "./Step3FocusAreas";
import { Step4KeyParties } from "./Step4KeyParties";
import { Step5DocumentChecklist } from "./Step5DocumentChecklist";
import {
  useCreateWizardDraft,
  useUpdateWizardDraft,
  useDeleteWizardDraft,
  WizardDraftData,
} from "@/hooks/useWizardDraft";

interface DDProjectWizardProps {
  onComplete: (setup: DDProjectSetup) => void;
  onCancel: () => void;
  initialDraft?: WizardDraftData | null;
}

const STEPS = [
  { id: 1, title: "Transaction Type", description: "Select transaction type and basics" },
  { id: 2, title: "Deal Context", description: "Provide context for the deal" },
  { id: 3, title: "Focus Areas", description: "Set priorities and deal breakers" },
  { id: 4, title: "Key Parties", description: "Identify important parties" },
  { id: 5, title: "Documents", description: "Review document checklist" },
];

// Convert draft data to project setup
function draftToProjectSetup(draft: WizardDraftData): DDProjectSetup {
  return {
    transactionType: draft.transactionType as any,
    transactionName: draft.transactionName || "",
    clientRole: draft.clientRole as any,
    dealStructure: draft.dealStructure as any,
    estimatedValue: draft.estimatedValue,
    targetClosingDate: draft.targetClosingDate ? new Date(draft.targetClosingDate) : null,
    dealRationale: draft.dealRationale || "",
    knownConcerns: draft.knownConcerns || [],
    criticalPriorities: draft.criticalPriorities || [],
    knownDealBreakers: draft.knownDealBreakers || [],
    deprioritizedAreas: draft.deprioritizedAreas || [],
    targetCompanyName: draft.targetCompanyName || "",
    keyPersons: draft.keyPersons || [],
    counterparties: draft.counterparties || [],
    keyLenders: draft.keyLenders || [],
    keyRegulators: draft.keyRegulators || [],
    uploadedFile: null, // Files can't be restored from draft
  };
}

// Convert project setup to draft data for saving
function projectSetupToDraft(setup: DDProjectSetup, currentStep: number): Partial<WizardDraftData> {
  return {
    currentStep,
    transactionType: setup.transactionType,
    transactionName: setup.transactionName,
    clientRole: setup.clientRole,
    dealStructure: setup.dealStructure,
    estimatedValue: setup.estimatedValue,
    targetClosingDate: setup.targetClosingDate?.toISOString() || null,
    dealRationale: setup.dealRationale,
    knownConcerns: setup.knownConcerns,
    criticalPriorities: setup.criticalPriorities,
    knownDealBreakers: setup.knownDealBreakers,
    deprioritizedAreas: setup.deprioritizedAreas,
    targetCompanyName: setup.targetCompanyName,
    keyPersons: setup.keyPersons,
    counterparties: setup.counterparties,
    keyLenders: setup.keyLenders,
    keyRegulators: setup.keyRegulators,
  };
}

export function DDProjectWizard({ onComplete, onCancel, initialDraft }: DDProjectWizardProps) {
  const [currentStep, setCurrentStep] = useState(initialDraft?.currentStep || 1);
  const [projectSetup, setProjectSetup] = useState<DDProjectSetup>(
    initialDraft ? draftToProjectSetup(initialDraft) : DEFAULT_PROJECT_SETUP
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [draftId, setDraftId] = useState<string | null>(initialDraft?.id || null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  const createDraft = useCreateWizardDraft();
  const updateDraft = useUpdateWizardDraft();
  const deleteDraft = useDeleteWizardDraft();

  // Track if there are unsaved changes
  const hasChangesRef = useRef(false);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const updateSetup = (updates: Partial<DDProjectSetup>) => {
    setProjectSetup((prev) => ({ ...prev, ...updates }));
    hasChangesRef.current = true;
    setSaveStatus("idle");
  };

  // Auto-save function with debounce
  const saveDraft = useCallback(async () => {
    if (!hasChangesRef.current) return;

    // Don't save if we're on step 1 and haven't entered anything meaningful
    if (currentStep === 1 && !projectSetup.transactionName.trim() && !projectSetup.transactionType) {
      return;
    }

    setSaveStatus("saving");

    try {
      const draftData = projectSetupToDraft(projectSetup, currentStep);

      if (draftId) {
        // Update existing draft
        await updateDraft.mutateAsync({ draftId, data: draftData });
      } else {
        // Create new draft
        const newDraft = await createDraft.mutateAsync(draftData);
        setDraftId(newDraft.id);
      }

      hasChangesRef.current = false;
      setSaveStatus("saved");
      setLastSaved(new Date());

      // Reset to idle after a few seconds
      setTimeout(() => setSaveStatus("idle"), 3000);
    } catch (error) {
      console.error("Failed to save draft:", error);
      setSaveStatus("error");
    }
  }, [projectSetup, currentStep, draftId, createDraft, updateDraft]);

  // Debounced auto-save when data changes
  useEffect(() => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    // Auto-save after 2 seconds of no changes
    saveTimeoutRef.current = setTimeout(() => {
      saveDraft();
    }, 2000);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [projectSetup, currentStep, saveDraft]);

  // Save when navigating between steps
  useEffect(() => {
    saveDraft();
  }, [currentStep]);

  // Save before unloading the page
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (hasChangesRef.current && draftId) {
        // Use sendBeacon for reliable save on page close
        const draftData = projectSetupToDraft(projectSetup, currentStep);
        navigator.sendBeacon?.(
          "/api/dd-wizard-draft",
          JSON.stringify({ draftId, ...draftData })
        );
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [projectSetup, currentStep, draftId]);

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return (
          projectSetup.transactionType &&
          projectSetup.transactionName.trim() &&
          projectSetup.clientRole &&
          projectSetup.dealStructure
        );
      case 2:
        return true; // All optional in step 2
      case 3:
        return true; // All optional in step 3
      case 4:
        return projectSetup.targetCompanyName.trim();
      case 5:
        return !!projectSetup.uploadedFile; // Require file upload
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (currentStep < STEPS.length) {
      setCurrentStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleComplete = async () => {
    setIsSubmitting(true);
    try {
      await onComplete(projectSetup);
      // Delete the draft after successful completion
      if (draftId) {
        await deleteDraft.mutateAsync(draftId);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleManualSave = () => {
    hasChangesRef.current = true;
    saveDraft();
  };

  const progressValue = (currentStep / STEPS.length) * 100;

  // Save status indicator
  const SaveStatusIndicator = () => {
    if (saveStatus === "saving") {
      return (
        <span className="flex items-center text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          Saving...
        </span>
      );
    }
    if (saveStatus === "saved") {
      return (
        <span className="flex items-center text-xs text-green-600">
          <Cloud className="h-3 w-3 mr-1" />
          Saved
        </span>
      );
    }
    if (saveStatus === "error") {
      return (
        <span className="flex items-center text-xs text-red-600">
          <CloudOff className="h-3 w-3 mr-1" />
          Save failed
        </span>
      );
    }
    if (draftId && lastSaved) {
      return (
        <span className="flex items-center text-xs text-muted-foreground">
          <Cloud className="h-3 w-3 mr-1" />
          Draft saved
        </span>
      );
    }
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Progress Header */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium">
            Step {currentStep} of {STEPS.length}: {STEPS[currentStep - 1].title}
          </span>
          <div className="flex items-center gap-3">
            <SaveStatusIndicator />
            <span className="text-sm text-muted-foreground">
              {Math.round(progressValue)}% complete
            </span>
          </div>
        </div>
        <Progress value={progressValue} className="h-2" />
      </div>

      {/* Step Indicators */}
      <div className="flex justify-between">
        {STEPS.map((step) => {
          const isCompleted = step.id < currentStep;
          const isCurrent = step.id === currentStep;
          const isClickable = isCompleted; // Can only click completed steps

          return (
            <div
              key={step.id}
              className={`flex flex-col items-center w-1/5 ${
                isCurrent
                  ? "text-alchemyPrimaryOrange"
                  : isCompleted
                  ? "text-green-600"
                  : "text-muted-foreground"
              }`}
            >
              <div
                onClick={() => isClickable && setCurrentStep(step.id)}
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
                  isCurrent
                    ? "bg-alchemyPrimaryOrange text-white"
                    : isCompleted
                    ? "bg-green-600 text-white cursor-pointer hover:bg-green-700 hover:scale-110"
                    : "bg-gray-200"
                }`}
                title={isClickable ? `Go back to ${step.title}` : undefined}
              >
                {isCompleted ? <Check className="h-4 w-4" /> : step.id}
              </div>
              <span
                className={`text-xs mt-1 text-center hidden sm:block ${isClickable ? "cursor-pointer" : ""}`}
                onClick={() => isClickable && setCurrentStep(step.id)}
              >
                {step.title}
              </span>
            </div>
          );
        })}
      </div>

      {/* Step Content */}
      <div className="min-h-[400px] max-h-[60vh] overflow-y-auto px-1">
        {currentStep === 1 && (
          <Step1TransactionBasics data={projectSetup} onChange={updateSetup} />
        )}
        {currentStep === 2 && (
          <Step2DealContext data={projectSetup} onChange={updateSetup} />
        )}
        {currentStep === 3 && (
          <Step3FocusAreas data={projectSetup} onChange={updateSetup} />
        )}
        {currentStep === 4 && (
          <Step4KeyParties data={projectSetup} onChange={updateSetup} />
        )}
        {currentStep === 5 && <Step5DocumentChecklist data={projectSetup} onChange={updateSetup} />}
      </div>

      {/* Navigation Footer */}
      <div className="flex justify-between pt-4 border-t">
        <div className="flex gap-2">
          {currentStep > 1 ? (
            <Button variant="outline" onClick={handleBack}>
              <ChevronLeft className="h-4 w-4 mr-1" />
              Back
            </Button>
          ) : (
            <Button variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          )}
          {/* Manual save button */}
          <Button
            variant="outline"
            onClick={handleManualSave}
            disabled={saveStatus === "saving"}
            className="text-muted-foreground"
          >
            <Save className="h-4 w-4 mr-1" />
            Save Draft
          </Button>
        </div>

        <div className="flex gap-2">
          {currentStep < STEPS.length ? (
            <Button
              onClick={handleNext}
              disabled={!canProceed()}
              className="bg-alchemyPrimaryOrange hover:bg-alchemyPrimaryOrange/90"
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <Button
              onClick={handleComplete}
              disabled={!canProceed() || isSubmitting}
              className="bg-alchemyPrimaryOrange hover:bg-alchemyPrimaryOrange/90"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating Project...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4 mr-1" />
                  Create DD Project
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export default DDProjectWizard;
