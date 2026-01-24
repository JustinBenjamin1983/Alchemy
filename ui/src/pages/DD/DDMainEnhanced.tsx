/**
 * DDMainEnhanced - Due Diligence Main Page with Enhanced Project Wizard
 *
 * This component extends the existing DDMain functionality with:
 * - Transaction type selection with blueprints and document registries
 * - Multi-step project wizard for better DD setup
 * - Document upload with auto-classification
 * - Missing documents tracker
 *
 * To use this instead of DDMain, update the route in App.tsx:
 * import { DDMainEnhanced } from "./pages/DD/DDMainEnhanced";
 * <Route path="/dd" element={<DDMainEnhanced />} />
 */

import { SidebarInset, SidebarProvider } from "../../components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { useLocation, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState, useMemo } from "react";
import { useMutateDDDelete } from "@/hooks/useMutateDDDelete";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useMutateDDStart } from "@/hooks/useMutateDDStart";
import { useGetDDListing } from "@/hooks/useGetDDListing";
import { AppSidebar } from "../OpinionWriter/AppSideBar";
import { Loader2, AlertCircle } from "lucide-react";
import { useMutateDDJoin } from "@/hooks/useMutateDDJoin";
import { useDevFileUpload } from "@/hooks/useDevFileUpload";
import { DocListing } from "./Files/DocListing";
import Questions from "./Questions";
import { Search } from "./Search";
import { useGetDDDocsHistory } from "@/hooks/useGetDDDocsHistory";
import { useGetDD } from "@/hooks/useGetDD";
import { useGetUser } from "@/hooks/useGetUser";
import { useIdle } from "@uidotdev/usehooks";
import { useMsal } from "@azure/msal-react";
import { useGenerateSAS } from "@/hooks/useGenerateSAS";
import { DDTop, ScreenState } from "./DDTop";
import axios from "axios";
import ChatbotUI from "./ChatbotUI";
import { generateDDReport } from "@/utils/reportGenerator";
import { useGetDDRiskResults } from "@/hooks/useGetDDRiskResults";
import { RiskSummary } from "./RiskSummary";
import DocumentChanges from "./DocumentChanges";

// Import new enhanced components
import { DDProjectWizard, DDProjectSetup } from "./Wizard";
import { MissingDocumentsTracker } from "./Documents";
import { useGetWizardDrafts, WizardDraftData } from "@/hooks/useWizardDraft";

// Import Checkpoint A components
import { ClassificationProgressModal } from "./Processing/ClassificationProgressModal";
import { CheckpointADocListing } from "./Processing/CheckpointADocListing";
import { useClassifyDocuments } from "@/hooks/useOrganisationProgress";

export function DDMainEnhanced() {
  const navigate = useNavigate();
  const startDD = useMutateDDStart();
  const mutateDDDelete = useMutateDDDelete();
  const generateSAS = useGenerateSAS();
  const devFileUpload = useDevFileUpload();
  const { data: myProjects, isLoading: projectsLoading } = useGetDDListing("involves_me");
  const { data: wizardDrafts, isLoading: draftsLoading } = useGetWizardDrafts();
  const mutateDDJoin = useMutateDDJoin();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedDraft, setSelectedDraft] = useState<WizardDraftData | null>(null);
  const { instance } = useMsal();
  const idle = useIdle(10 * 60_000);
  const { data: user } = useGetUser();

  // Store project setup from wizard
  const [projectSetup, setProjectSetup] = useState<DDProjectSetup | null>(null);

  // Checkpoint A: Classification modal state
  const [showClassificationModal, setShowClassificationModal] = useState(false);
  const classifyDocuments = useClassifyDocuments();

  useEffect(() => {
    if (user && (user as any).likelyLoggedOut) {
      navigate("/login", {
        state: {
          message:
            "As a security measure, we have logged you out due to inactivity",
        },
      });
    }
  }, [user]);

  useEffect(() => {
    if (!idle) return;
    instance.logoutRedirect();
  }, [idle]);

  const location = useLocation();
  const [selectedDDID, setSelectedDDID] = useState(() => {
    const query = new URLSearchParams(location.search);
    return query.get("id");
  });

  const {
    data: dd,
    isFetching: ddIsFetching,
    error: ddError,
  } = useGetDD(selectedDDID, !!selectedDDID && !mutateDDDelete.isPending);

  const { data: docsHistory, refetch: refetchDocsHistory } =
    useGetDDDocsHistory(selectedDDID);

  useEffect(() => {
    if (!selectedDDID) return;
    refetchDocsHistory();
  }, [selectedDDID]);

  useEffect(() => {
    if (selectedDDID) {
      const params = new URLSearchParams(location.search);
      params.set("id", selectedDDID);
      navigate(`${location.pathname}?${params.toString()}`, { replace: true });
    }
  }, [selectedDDID, location.pathname]);

  useEffect(() => {
    const query = new URLSearchParams(location.search);
    const id = query.get("id");
    if (!id) return;

    setSelectedDDID(id);
    setScreenState("Documents");
  }, [location.search]);

  const handleDeleteDD = (ddId: string) => {
    if (!ddId) {
      alert("Cannot delete: No project selected");
      return;
    }
    mutateDDDelete.mutate(
      { dd_id: ddId },
      {
        onSuccess: () => {
          window.location.href = window.location.pathname;
        },
        onError: (error: any) => {
          console.error("Failed to delete due diligence:", error);
          const errorMessage = error?.response?.data?.error || error?.message || "Unknown error occurred";
          alert(`Failed to delete project: ${errorMessage}`);
        },
      }
    );
  };

  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const { data: riskResultsRaw } = useGetDDRiskResults(selectedDDID);
  const riskResults = (riskResultsRaw ?? []) as Array<{
    category?: string;
    findings?: any[];
  }>;

  const allFindings = useMemo(() => {
    if (!riskResults) return [];
    return riskResults.flatMap((category) =>
      (category.findings ?? []).map((finding) => ({
        ...finding,
        category: category.category ?? "Uncategorized",
      }))
    );
  }, [riskResults]);

  const categories = useMemo(() => {
    if (!riskResults) return [];
    return Array.from(
      new Set(riskResults.map((r) => r.category ?? "Uncategorized"))
    );
  }, [riskResults]);

  useEffect(() => {
    if (!mutateDDJoin.isSuccess) return;
    setScreenState("Documents");
  }, [mutateDDJoin.isSuccess]);

  const [screenState, setScreenState] = useState<ScreenState>("Wizard-Enhanced");

  const handleGenerateReport = async () => {
    if (!dd || allFindings.length === 0) {
      alert("No findings available to generate report");
      return;
    }

    setIsGeneratingReport(true);
    try {
      const activeFindings = allFindings.filter(
        (f: any) => f.finding_status !== "Deleted"
      );
      await generateDDReport(dd.name, activeFindings, categories);
    } catch (error) {
      console.error("Failed to generate report:", error);
      alert("Failed to generate report. Please try again.");
    } finally {
      setIsGeneratingReport(false);
    }
  };

  // Handle wizard completion - creates the DD project
  const handleWizardComplete = async (setup: DDProjectSetup) => {
    setProjectSetup(setup);
    setUploadError(null);
    setIsUploading(true);

    try {
      if (!setup.uploadedFile) {
        throw new Error("No file selected. Please upload a ZIP file with your documents.");
      }

      // Generate a unique filename for local storage
      const timestamp = Date.now();
      const safeFilename = setup.uploadedFile.name.replace(/[^a-zA-Z0-9.-]/g, "_");
      const localStoragePath = `/tmp/dd_storage/uploads/${timestamp}_${safeFilename}`;

      // Upload file to local storage (dev mode)
      const uploadResult = await devFileUpload.mutateAsync({
        file: setup.uploadedFile,
        targetPath: localStoragePath,
      });

      if (!uploadResult.success) {
        throw new Error("Failed to upload file to local storage");
      }

      // Create the DD project with the local file URL
      const createResult = await startDD.mutateAsync({
        data: {
          name: setup.transactionName || "Untitled DD Project",
          briefing: setup.dealRationale || "",
          blobUrl: `local://${uploadResult.localPath}`,
          transactionType: setup.transactionType,
          projectSetup: {
            ...setup,
            uploadedFile: undefined, // Don't send File object to backend
          },
        },
      });

      // Navigate to the newly created project and start classification
      const newDdId = createResult.data?.dd_id;
      if (newDdId) {
        setSelectedDDID(newDdId);
        // Show classification modal and trigger classification
        setShowClassificationModal(true);
        setScreenState("CheckpointA");

        // Start document classification in background
        classifyDocuments.mutate({ ddId: newDdId });
      } else {
        setScreenState("Documents");
      }
    } catch (error: any) {
      console.error("Failed to create DD project:", error);
      setUploadError(
        error?.response?.data?.error ||
          error?.message ||
          "Failed to create project. Please try again."
      );
      // Stay on wizard screen so user can retry
      setScreenState("Wizard-Enhanced");
    } finally {
      setIsUploading(false);
    }
  };

  // Get uploaded document filenames for missing docs tracker
  const uploadedDocuments = useMemo(() => {
    if (!dd?.folders) return [];
    return dd.folders.flatMap((folder: any) =>
      folder.documents?.map((doc: any) => doc.original_file_name) ?? []
    );
  }, [dd]);

  // Get transaction type from DD data or project setup
  const currentTransactionType = useMemo(() => {
    return (dd as any)?.transaction_type || projectSetup?.transactionType;
  }, [dd, projectSetup]);

  // Restore project setup from DD when loading existing project
  useEffect(() => {
    if (dd && (dd as any)?.project_setup && !projectSetup) {
      setProjectSetup((dd as any).project_setup);
    }
  }, [dd, projectSetup]);

  return (
    <SidebarProvider>
      <AppSidebar isOpinion={false} />
      <SidebarInset>
        {/* Enhanced Project Wizard Dialog */}
        <Dialog
          open={screenState === "Wizard-Enhanced"}
          onOpenChange={(open) => {
            if (!open && !isUploading) {
              setScreenState("Documents");
              setSelectedDraft(null);
            }
          }}
        >
          <DialogContent className="w-[95vw] max-w-[1200px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {selectedDraft ? "Continue Draft" : "New Due Diligence Project"}
              </DialogTitle>
              <DialogDescription>
                {selectedDraft
                  ? `Continuing "${selectedDraft.transactionName || 'Untitled Draft'}" - Step ${selectedDraft.currentStep} of 4`
                  : "Set up your DD project with the enhanced wizard"
                }
              </DialogDescription>
            </DialogHeader>

            {/* Show saved drafts if available and not already editing one */}
            {!selectedDraft && !isUploading && wizardDrafts && wizardDrafts.length > 0 && (
              <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-sm font-medium text-green-800">
                    You have {wizardDrafts.length} saved draft{wizardDrafts.length > 1 ? 's' : ''}
                  </span>
                </div>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {wizardDrafts.map((draft) => (
                    <div
                      key={draft.id}
                      className="flex items-center justify-between p-2 bg-white border border-green-200 rounded hover:border-green-400 cursor-pointer transition-all"
                      onClick={() => setSelectedDraft(draft)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">
                          {draft.transactionName || "Untitled Draft"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Step {draft.currentStep}/4 • Last saved: {draft.updatedAt ? new Date(draft.updatedAt).toLocaleString() : 'Unknown'}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        className="bg-green-600 hover:bg-green-700 text-white ml-2"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedDraft(draft);
                        }}
                      >
                        Continue
                      </Button>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-green-700 mt-2">
                  Or scroll down to start a new project
                </p>
              </div>
            )}

            {uploadError && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-md text-red-700">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <span className="text-sm">{uploadError}</span>
              </div>
            )}
            {isUploading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-12 w-12 animate-spin text-alchemyPrimaryOrange mb-4" />
                <p className="text-lg font-medium">Creating your DD project...</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Uploading documents and setting up classification
                </p>
              </div>
            ) : (
              <DDProjectWizard
                onComplete={handleWizardComplete}
                onCancel={() => {
                  setScreenState("Documents");
                  setSelectedDraft(null);
                }}
                initialDraft={selectedDraft}
              />
            )}
          </DialogContent>
        </Dialog>

        {/* Open Existing Project Dialog */}
        <Dialog
          open={screenState === "Wizard-JoinProject"}
          onOpenChange={(open) => (!open ? setScreenState("Documents") : null)}
        >
          <DialogContent className="w-[90vw] max-w-[600px] max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Open Existing Project</DialogTitle>
              <DialogDescription>
                Select a project to continue working on
              </DialogDescription>
            </DialogHeader>
            {projectsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin mr-2" />
                Loading projects...
              </div>
            ) : myProjects && myProjects.length > 0 ? (
              <div className="space-y-2 max-h-[50vh] overflow-y-auto">
                {myProjects.map((project: any) => (
                  <div
                    key={project.id}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => {
                      setSelectedDDID(project.id);
                      setScreenState("Documents");
                    }}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{project.name}</p>
                      <p className="text-sm text-muted-foreground">
                        Created: {new Date(project.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedDDID(project.id);
                        setScreenState("Documents");
                      }}
                    >
                      Open
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <p>No existing projects found.</p>
                <Button
                  className="mt-4 bg-alchemyPrimaryGoldenWeb"
                  onClick={() => setScreenState("Wizard-Enhanced")}
                >
                  Start New Project
                </Button>
              </div>
            )}
          </DialogContent>
        </Dialog>

        <DDTop
          ddId={selectedDDID}
          ddName={dd?.name}
          screenState={screenState}
          setScreenState={setScreenState}
          onDelete={handleDeleteDD}
          isDeleting={mutateDDDelete.isPending}
          onGenerateReport={handleGenerateReport}
          isGeneratingReport={isGeneratingReport}
        />

        {!dd && !ddIsFetching && (
          <div className="flex flex-col items-center justify-center h-screen">
            <div className="text-lg pb-4">
              {(user as any)?.name && <>Hi, {(user as any)?.name}</>}
            </div>
            <div className="flex gap-4">
              <Button
                className="bg-alchemyPrimaryGoldenWeb"
                onClick={() => setScreenState("Wizard-Enhanced")}
              >
                Start New DD Project (Enhanced)
              </Button>
              <Button
                variant="outline"
                onClick={() => setScreenState("Wizard-JoinProject")}
              >
                Open Existing Project
              </Button>
            </div>
          </div>
        )}

        {ddIsFetching && (
          <div className="flex items-center justify-center h-screen">
            <Loader2 className="h-8 w-8 animate-spin mr-2" />
            Loading...
          </div>
        )}

        {dd && (
          <div className="text-xl flex flex-1 flex-col gap-4 p-4 pt-4">
            <div className="text-2xl font-bold">
              {screenState === "Documents" && "Documents"}
              {screenState === "DocumentErrors" && "Document Errors"}
              {screenState === "DocumentChanges" && "Document Changes"}
              {screenState === "Search" && "Search"}
              {screenState === "Analysis" && "Analysis"}
              {screenState === "Questions" && "Questions"}
              {screenState === "ShowReport" && "Generate Report"}
              {screenState === "MissingDocs" && "Document Status"}
              {screenState === "CheckpointA" && "Document Classification Review"}
            </div>
            <div>
              {screenState === "Documents" && (
                <DocListing folders={dd?.folders} dd_id={selectedDDID} />
              )}
              {screenState === "DocumentChanges" && (
                <DocumentChanges dd_id={selectedDDID} />
              )}
              {screenState === "Search" && <Search />}
              {screenState === "Analysis" && <RiskSummary />}
              {screenState === "Questions" && (
                <Questions dd_id={selectedDDID} />
              )}
              {screenState === "ShowReport" && (
                <div>Report generation feature coming soon...</div>
              )}
              {screenState === "MissingDocs" && currentTransactionType && (
                <MissingDocumentsTracker
                  projectId={selectedDDID || ""}
                  transactionType={currentTransactionType}
                  uploadedDocuments={uploadedDocuments}
                />
              )}
              {screenState === "CheckpointA" && currentTransactionType && selectedDDID && (
                <CheckpointADocListing
                  ddId={selectedDDID}
                  transactionType={currentTransactionType}
                  onReadabilityCheck={() => {
                    // TODO: Trigger readability check and move to next stage
                    setScreenState("Documents");
                  }}
                />
              )}
            </div>
          </div>
        )}

        {/* Checkpoint A: Classification Progress Modal */}
        <ClassificationProgressModal
          open={showClassificationModal}
          ddId={selectedDDID}
          transactionType={currentTransactionType}
          onComplete={() => {
            // Classification complete with no issues - stay on CheckpointA for review
            setShowClassificationModal(false);
          }}
          onReviewDocuments={() => {
            // Classification complete with issues - go to CheckpointA review
            setShowClassificationModal(false);
          }}
        />

        <ChatbotUI folders={dd?.folders} dd_id={selectedDDID} />
      </SidebarInset>
    </SidebarProvider>
  );
}

export default DDMainEnhanced;
