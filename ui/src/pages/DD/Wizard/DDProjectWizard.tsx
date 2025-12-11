import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ChevronLeft, ChevronRight, Check, Loader2 } from "lucide-react";
import { DDProjectSetup, DEFAULT_PROJECT_SETUP } from "./types";
import { Step1TransactionBasics } from "./Step1TransactionBasics";
import { Step2DealContext } from "./Step2DealContext";
import { Step3FocusAreas } from "./Step3FocusAreas";
import { Step4KeyParties } from "./Step4KeyParties";
import { Step5DocumentChecklist } from "./Step5DocumentChecklist";

interface DDProjectWizardProps {
  onComplete: (setup: DDProjectSetup) => void;
  onCancel: () => void;
}

const STEPS = [
  { id: 1, title: "Transaction Type", description: "Select transaction type and basics" },
  { id: 2, title: "Deal Context", description: "Provide context for the deal" },
  { id: 3, title: "Focus Areas", description: "Set priorities and deal breakers" },
  { id: 4, title: "Key Parties", description: "Identify important parties" },
  { id: 5, title: "Documents", description: "Review document checklist" },
];

export function DDProjectWizard({ onComplete, onCancel }: DDProjectWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [projectSetup, setProjectSetup] = useState<DDProjectSetup>(DEFAULT_PROJECT_SETUP);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updateSetup = (updates: Partial<DDProjectSetup>) => {
    setProjectSetup((prev) => ({ ...prev, ...updates }));
  };

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
    } finally {
      setIsSubmitting(false);
    }
  };

  const progressValue = (currentStep / STEPS.length) * 100;

  return (
    <div className="space-y-6">
      {/* Progress Header */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium">
            Step {currentStep} of {STEPS.length}: {STEPS[currentStep - 1].title}
          </span>
          <span className="text-sm text-muted-foreground">
            {Math.round(progressValue)}% complete
          </span>
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
        <div>
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
