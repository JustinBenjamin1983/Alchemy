// File: ui/src/pages/DD/DDMain.tsx

import { SidebarInset, SidebarProvider } from "../../components/ui/sidebar";

import { Button } from "@/components/ui/button";

import { useLocation, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState, useMemo } from "react";
import { useMutateDDDelete } from "@/hooks/useMutateDDDelete";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import RiskManager from "./RiskManager";
import { RiskSummary } from "./RiskSummary";
import DocumentChanges from "./DocumentChanges";
import { useMutateDDStart } from "@/hooks/useMutateDDStart";
import { DDProjectWizard } from "./Wizard/DDProjectWizard";
import { DDProjectSetup } from "./Wizard/types";
import { useGetDDListing } from "@/hooks/useGetDDListing";
import { AppSidebar } from "../OpinionWriter/AppSideBar";
import { Loader2, Clock, Trash2, FileEdit } from "lucide-react";
import { useMutateDDJoin } from "@/hooks/useMutateDDJoin";
import { DocListing } from "./Files/DocListing";
import Questions from "./Questions";
import { Search } from "./Search";
import { useGetDDDocsHistory } from "@/hooks/useGetDDDocsHistory";
import { useGetDD } from "@/hooks/useGetDD";
import { useGetUser } from "@/hooks/useGetUser";
import { useIdle } from "@uidotdev/usehooks";
import { useMsal } from "@azure/msal-react";
import { useGenerateSAS } from "@/hooks/useGenerateSAS";
import { DDTop } from "./DDTop";
import axios from "axios";
import ChatbotUI from "./ChatbotUI";
import { generateDDReport } from "@/utils/reportGenerator";
import { useGetDDRiskResults } from "@/hooks/useGetDDRiskResults";
import { useGetDDRisks } from "@/hooks/useGetDDRisks";
import { DEV_MODE } from "@/authConfig";
import { useGetWizardDrafts, useDeleteWizardDraft, WizardDraftData } from "@/hooks/useWizardDraft";
import { DDProcessingDashboard } from "./Processing";

export function DDMain() {
  const navigate = useNavigate();
  const [isDraggingFile, setIsDraggingFile] = useState<boolean>(false);
  const startDD = useMutateDDStart();
  const mutateDDDelete = useMutateDDDelete();

  // Wizard draft state
  const [selectedDraft, setSelectedDraft] = useState<WizardDraftData | null>(null);
  const { data: wizardDrafts, isLoading: draftsLoading } = useGetWizardDrafts();
  const deleteWizardDraft = useDeleteWizardDraft();
  const generateSAS = useGenerateSAS();
  const { data: dds } = useGetDDListing("im_not_a_member");
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [projectName, setProjectName] = useState<string>("");
  const [clientBriefing, setClientBriefing] = useState<string>("");
  const mutateDDJoin = useMutateDDJoin();
  const [joinDDLens, setJoinDDLens] = useState<string>(null);
  const [joinDDRisks, setJoinDDRisks] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  console.log("dds?.due_diligences", dds?.due_diligences);
  const { instance } = useMsal();
  const idle = useIdle(10 * 60_000);
  const { data: user } = useGetUser();
  useEffect(() => {
    // Skip redirect check in dev mode
    if (DEV_MODE) return;
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
    // Skip idle logout in dev mode
    if (DEV_MODE) return;
    console.log("idle", idle);
    if (!idle) return;
    console.log("attempting sign out due to no activity");
    instance.logoutRedirect();
  }, [idle]);

  const [filePendingUpload, setFilePendingUpload] = useState(null);
  const [uploadError, setUploadError] = useState<string | null>(null); //Error state for the file upload thing
  const draggingStyle = !isDraggingFile
    ? {}
    : {
        backgroundColor: "#E1E1E1", //bg-alchemySecondaryLightGrey
        transition: "0.5s all ease 0s",
        WebkitTransition: "0.5s all ease 0s",
        MozTransition: "0.5s all ease 0s",
        msTransition: "0.5s all ease 0s",
        borderWidth: "3px",
        borderStyle: "solid",
      };
  const location = useLocation();
  const [selectedDDToJoin, setSelectedDDToJoin] = useState(null);
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
  console.log("useGetDDDocsHistory", docsHistory);

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
    const resumeDraftId = query.get("resumeDraft");

    // Handle resuming a wizard draft from sidebar click
    if (resumeDraftId && wizardDrafts) {
      const draftToResume = wizardDrafts.find((d) => d.id === resumeDraftId);
      if (draftToResume) {
        setSelectedDraft(draftToResume);
        setScreenState("Wizard-NewProject");
        // Clear the URL parameter
        const params = new URLSearchParams(location.search);
        params.delete("resumeDraft");
        navigate(`${location.pathname}${params.toString() ? '?' + params.toString() : ''}`, { replace: true });
        return;
      }
    }

    if (!id) return;

    setSelectedDDID(id);
    // Only change to Documents if we're not already in a wizard state
    // This prevents the wizard from being kicked out when wizardDrafts updates
    setScreenState((prev) => prev.startsWith("Wizard") ? prev : "Documents");
  }, [location.search, wizardDrafts]);

  const handleButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { files } = e.target;
    if (files) {
      handleFiles(files, true);
    }
  };
  const createDD = async () => {
    if (!filePendingUpload) return;

    setIsUploading(true);

    try {
      // 1️⃣ Request SAS URL
      const { sasUrl } = await generateSAS.mutateAsync({
        filename: filePendingUpload.name,
      });

      // 2️⃣ Upload file using Axios
      await axios.put(sasUrl, filePendingUpload, {
        headers: {
          "x-ms-blob-type": "BlockBlob",
        },
      });

      // 3️⃣ Notify backend
      startDD.mutate({
        data: {
          name: projectName,
          briefing: clientBriefing,
          blobUrl: sasUrl,
        },
      });
    } catch (err) {
      setUploadError("An error occurred during file upload or processing.");
      console.error(err);
    } finally {
      setIsUploading(false); // stop spinner
    }
  };

  // Handler for the new wizard completion
  const handleWizardComplete = async (setup: DDProjectSetup) => {
    if (!setup.uploadedFile) {
      setUploadError("Please upload a ZIP file with your documents.");
      return;
    }

    setIsUploading(true);

    try {
      let blobUrl: string;

      // 1️⃣ Request SAS URL / dev mode info
      const sasResponse = await generateSAS.mutateAsync({
        filename: setup.uploadedFile.name,
      });

      if (sasResponse.devMode) {
        // Dev mode: Upload via FormData to backend endpoint
        const formData = new FormData();
        formData.append("file", setup.uploadedFile);
        formData.append("localPath", sasResponse.localPath);

        await axios.post("/api/dd-file-upload-dev", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });
        blobUrl = sasResponse.blobUrl;
      } else {
        // Production: Upload directly to Azure Blob Storage
        await axios.put(sasResponse.sasUrl, setup.uploadedFile, {
          headers: {
            "x-ms-blob-type": "BlockBlob",
          },
        });
        blobUrl = sasResponse.sasUrl;
      }

      // 3️⃣ Create the DD with wizard data
      const briefing = `
Transaction Type: ${setup.transactionType}
Client Role: ${setup.clientRole}
Deal Structure: ${setup.dealStructure}
Target Company: ${setup.targetCompanyName}
Estimated Value: ${setup.estimatedValue ? `R${setup.estimatedValue.toLocaleString()}` : "Not specified"}
Target Closing: ${setup.targetClosingDate ? new Date(setup.targetClosingDate).toLocaleDateString() : "Not specified"}

Deal Rationale: ${setup.dealRationale || "Not provided"}

Known Concerns: ${setup.knownConcerns.length > 0 ? setup.knownConcerns.join(", ") : "None specified"}

Critical Priorities: ${setup.criticalPriorities.length > 0 ? setup.criticalPriorities.join(", ") : "None specified"}
Known Deal Breakers: ${setup.knownDealBreakers.length > 0 ? setup.knownDealBreakers.join(", ") : "None specified"}

Key Persons: ${setup.keyPersons.length > 0 ? setup.keyPersons.join(", ") : "None specified"}
Counterparties: ${setup.counterparties.length > 0 ? setup.counterparties.join(", ") : "None specified"}
Key Lenders: ${setup.keyLenders.length > 0 ? setup.keyLenders.join(", ") : "None specified"}
Key Regulators: ${setup.keyRegulators.length > 0 ? setup.keyRegulators.join(", ") : "None specified"}
`.trim();

      startDD.mutate({
        data: {
          name: setup.transactionName,
          briefing: briefing,
          blobUrl: blobUrl,
          transactionType: setup.transactionType,
          projectSetup: setup, // Pass the full setup for future use
        },
      });
    } catch (err) {
      setUploadError("An error occurred during file upload or processing.");
      console.error(err);
    } finally {
      setIsUploading(false);
    }
  };
  useEffect(() => {
    if (!startDD.isSuccess) return;

    setSelectedDDID((startDD.data.data as any).dd_id);
    setScreenState("Wizard-JoinProject");
  }, [startDD.isSuccess]);

  const handleFiles = async (files: any, fileWasDraggedIn: boolean) => {
    const uploadedFile = Array.from(files)[0] as any;

    if (!uploadedFile.name.endsWith(".zip")) {
      setUploadError(
        "Only .zip files are supported. Please upload a valid ZIP file."
      );
      setFilePendingUpload(null);
      return;
    }

    setUploadError(null);

    setFilePendingUpload(uploadedFile);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    setIsDraggingFile(true);
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDeleteDD = (ddId: string) => {
    mutateDDDelete.mutate(
      { dd_id: ddId },
      {
        onSuccess: () => {
          // Simply refresh the page to reset all state and queries
          window.location.href = window.location.pathname;
        },
        onError: (error) => {
          console.error("Failed to delete due diligence:", error);
          // You might want to show a toast or error message here
        },
      }
    );
  };

  const handleDragExit = (e: React.DragEvent<HTMLDivElement>) => {
    setIsDraggingFile(false);
    e.preventDefault();
    e.stopPropagation();
  };
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    setIsDraggingFile(false);
    e.preventDefault();
    e.stopPropagation();
    const { files } = e.dataTransfer;
    handleFiles(files, true);
  };

  const joinDD = () => {
    mutateDDJoin.mutate({
      dd_id: selectedDDToJoin,
      lens: joinDDLens,
      risks: joinDDRisks,
    });
  };

  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  // Get risk results for report generation
  const { data: riskResultsRaw } = useGetDDRiskResults(selectedDDID);
  const riskResults = (riskResultsRaw ?? []) as Array<{
    category?: string;
    findings?: any[];
  }>;

  // Process findings for report
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

    setSelectedDDID(selectedDDToJoin);
    setScreenState("Documents");
  }, [mutateDDJoin.isSuccess]);
  const [screenState, setScreenState] = useState<
    | "Documents"
    | "Wizard-Chooser"
    | "Wizard-NewProject"
    | "Wizard-JoinProject"
    | "DocumentErrors"
    | "Search"
    | "Risks"
    | "Questions"
    | "DocumentChanges"
    | "ShowReport"
    | "Processing"
  >("Wizard-Chooser");

  const handleGenerateReport = async () => {
    if (!dd || allFindings.length === 0) {
      alert("No findings available to generate report");
      return;
    }

    setIsGeneratingReport(true);
    try {
      // Filter out deleted findings
      const activeFindings = allFindings.filter(
        (f: any) => f.finding_status !== "Deleted"
      );
      await generateDDReport(dd.name, activeFindings, categories);
      // Success - report will download automatically
    } catch (error) {
      console.error("Failed to generate report:", error);
      alert("Failed to generate report. Please try again.");
    } finally {
      setIsGeneratingReport(false);
    }
  };

  // Handler for resuming wizard draft from sidebar
  const handleResumeWizardDraft = (draftId: string) => {
    const draftToResume = wizardDrafts?.find((d) => d.id === draftId);
    if (draftToResume) {
      setSelectedDraft(draftToResume);
      setScreenState("Wizard-NewProject");
    }
  };

  return (
    <SidebarProvider>
      <AppSidebar isOpinion={false} onResumeWizardDraft={handleResumeWizardDraft} />
      <SidebarInset>
        <Dialog
          open={screenState.startsWith("Wizard")}
          onOpenChange={(open) => (!open ? setScreenState("Documents") : null)}
        >
          {/* <DialogContent className="w-[1200px]"> */}
          <DialogContent className="w-[95vw] max-w-[1200px] max-h-[85vh] overflow-y-auto overflow-x-hidden">
            <DialogHeader>
              <DialogTitle>Due Diligence Configuration</DialogTitle>
              <DialogDescription>
                {/* Set up a new due diligence project */}
              </DialogDescription>
            </DialogHeader>
            {screenState == "Wizard-NewProject" && (
              <DDProjectWizard
                onComplete={(setup) => {
                  setSelectedDraft(null);
                  handleWizardComplete(setup);
                }}
                onCancel={() => {
                  setSelectedDraft(null);
                  setScreenState("Wizard-Chooser");
                }}
                initialDraft={selectedDraft}
              />
            )}
            {screenState == "Wizard-JoinProject" && (
              <div>
                <div className="py-4">
                  <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                    <Label htmlFor="username" className="text-right">
                      Choose an existing Virtual Data Room
                    </Label>
                    <Select
                      onValueChange={setSelectedDDToJoin}
                      value={selectedDDToJoin}
                    >
                      <SelectTrigger className="w-[400px] bg-white">
                        <SelectValue placeholder="Select a due diligence to join" />
                      </SelectTrigger>
                      <SelectContent className=" bg-white">
                        <SelectGroup>
                          {dds?.due_diligences.map((dd) => {
                            return (
                              <SelectItem
                                key={dd.id}
                                value={dd.id}
                                disabled={dd.has_in_progress_docs}
                              >
                                {dd.name}{" "}
                                {dd.has_in_progress_docs
                                  ? " (document processing still in progress)"
                                  : null}
                              </SelectItem>
                            );
                          })}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="py-4">
                  <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                    <Label htmlFor="username" className="text-right">
                      Your lens
                    </Label>
                    <Input
                      value={joinDDLens}
                      onChange={(evt) => setJoinDDLens(evt.target.value)}
                    />
                  </div>
                </div>
                <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                  <div></div>
                  <div className="text-muted-foreground text-sm">
                    This is your perspective on the due diligence
                  </div>
                </div>
                <div className="py-4">
                  <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                    <Label htmlFor="username" className="text-right">
                      Risks
                    </Label>
                    <div className="min-w-0 overflow-hidden">
                      <div className="max-h-[360px] overflow-y-auto pr-1">
                        <RiskManager
                          folders={dd?.folders ?? []}
                          onRisksChange={setJoinDDRisks}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            {screenState == "Wizard-Chooser" && (
              <div className="space-y-6 p-6">
                {/* Saved Drafts Section */}
                {wizardDrafts && wizardDrafts.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <FileEdit className="h-5 w-5" />
                      Resume Saved Drafts
                    </h3>
                    <div className="space-y-2">
                      {wizardDrafts.map((draft) => (
                        <Card key={draft.id} className="rounded-lg border">
                          <CardContent className="p-4 flex items-center justify-between">
                            <div className="flex-1">
                              <div className="font-medium">
                                {draft.transactionName || "Untitled Project"}
                              </div>
                              <div className="text-sm text-muted-foreground flex items-center gap-3">
                                <span className="flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  Step {draft.currentStep} of 5
                                </span>
                                {draft.transactionType && (
                                  <span>• {draft.transactionType}</span>
                                )}
                                {draft.updatedAt && (
                                  <span>
                                    • Last saved:{" "}
                                    {new Date(draft.updatedAt).toLocaleDateString()}{" "}
                                    {new Date(draft.updatedAt).toLocaleTimeString([], {
                                      hour: "2-digit",
                                      minute: "2-digit",
                                    })}
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  setSelectedDraft(draft);
                                  setScreenState("Wizard-NewProject");
                                }}
                              >
                                Resume
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  if (draft.id) {
                                    deleteWizardDraft.mutate(draft.id);
                                  }
                                }}
                                disabled={deleteWizardDraft.isPending}
                              >
                                <Trash2 className="h-4 w-4 text-muted-foreground hover:text-red-500" />
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}

                {/* Main Options */}
                <div className="grid grid-cols-2 gap-6">
                  <Card className="rounded-2xl shadow-md">
                    <CardContent className="p-6 flex flex-col gap-4">
                      <h2 className="text-xl font-semibold">
                        Start a new project
                      </h2>
                      <p className="text-sm text-muted-foreground">
                        Set up and configure the Virtual Data Room for your
                        colleagues.
                      </p>
                      <Button
                        onClick={() => {
                          setSelectedDraft(null);
                          setScreenState("Wizard-NewProject");
                        }}
                      >
                        Start Now
                      </Button>
                    </CardContent>
                  </Card>

                  <Card className="rounded-2xl shadow-md">
                    <CardContent className="p-6 flex flex-col gap-4">
                      <h2 className="text-xl font-semibold">Join a project</h2>
                      <p className="text-sm text-muted-foreground">
                        Connect to an existing Alchemy Virtual Data Room
                      </p>
                      <Button
                        onClick={() => setScreenState("Wizard-JoinProject")}
                      >
                        Browse
                      </Button>
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}
            <DialogFooter>
              {/* Wizard-NewProject footer buttons handled by DDProjectWizard component */}
              {screenState === "Wizard-JoinProject" && (
                <Button
                  onClick={joinDD}
                  disabled={
                    mutateDDJoin.isPending || !joinDDLens || !joinDDRisks
                  }
                >
                  {mutateDDJoin.isPending && (
                    <Loader2 className="animate-spin" />
                  )}
                  Join Due Diligence
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>
        <DDTop
          ddId={selectedDDID}
          ddName={dd?.name}
          screenState={screenState}
          setScreenState={setScreenState}
          docHistoryCount={dd?.docHistory?.length}
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
            <div>
              <Button
                className="bg-alchemyPrimaryGoldenWeb"
                onClick={() => setScreenState("Wizard-Chooser")}
              >
                Start or Join a Due Diligence Virtual Data Room
              </Button>
            </div>
          </div>
        )}
        {ddIsFetching && (
          <div className="flex items-center justify-center h-screen">
            Busy loading
          </div>
        )}
        {dd && (
          <div className="text-xl flex flex-1 flex-col gap-4 p-4 pt-4">
            <div className="text-2xl font-bold">
              {screenState === "Documents" && "Documents"}
              {screenState === "DocumentErrors" && "Document Errors"}
              {screenState === "DocumentChanges" && "Document Changes"}
              {screenState === "Search" && "Search"}
              {screenState === "Risks" && "Risks"}
              {screenState === "Questions" && "Questions"}
              {screenState === "ShowReport" && "Generate Report"}
              {screenState === "Processing" && "Processing Dashboard"}
            </div>
            <div className="">
              {screenState === "Documents" && (
                <DocListing folders={dd?.folders} dd_id={selectedDDID} />
              )}
              {screenState === "DocumentChanges" && (
                <DocumentChanges dd_id={selectedDDID} />
              )}
              {screenState === "Search" && <Search />}
              {screenState === "Risks" && (
                <>
                  <RiskSummary />
                </>
              )}
              {screenState === "Questions" && (
                <Questions dd_id={selectedDDID} />
              )}
              {screenState === "ShowReport" && (
                <div>Report generation feature coming soon...</div>
              )}
              {screenState === "Processing" && (
                <DDProcessingDashboard ddId={selectedDDID} />
              )}
            </div>
          </div>
        )}
        <ChatbotUI folders={dd?.folders} dd_id={selectedDDID} />
      </SidebarInset>
    </SidebarProvider>
  );
}
