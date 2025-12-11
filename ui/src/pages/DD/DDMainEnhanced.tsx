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
import { Loader2 } from "lucide-react";
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
import { RiskSummary } from "./RiskSummary";
import DocumentChanges from "./DocumentChanges";

// Import new enhanced components
import { DDProjectWizard, DDProjectSetup } from "./Wizard";
import { MissingDocumentsTracker } from "./Documents";

export function DDMainEnhanced() {
  const navigate = useNavigate();
  const startDD = useMutateDDStart();
  const mutateDDDelete = useMutateDDDelete();
  const generateSAS = useGenerateSAS();
  const { data: dds } = useGetDDListing("im_not_a_member");
  const mutateDDJoin = useMutateDDJoin();
  const [isUploading, setIsUploading] = useState(false);
  const { instance } = useMsal();
  const idle = useIdle(10 * 60_000);
  const { data: user } = useGetUser();

  // Store project setup from wizard
  const [projectSetup, setProjectSetup] = useState<DDProjectSetup | null>(null);

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
    mutateDDDelete.mutate(
      { dd_id: ddId },
      {
        onSuccess: () => {
          window.location.href = window.location.pathname;
        },
        onError: (error) => {
          console.error("Failed to delete due diligence:", error);
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

  const [screenState, setScreenState] = useState<
    | "Documents"
    | "Wizard-Enhanced"
    | "Wizard-JoinProject"
    | "DocumentErrors"
    | "Search"
    | "Risks"
    | "Questions"
    | "DocumentChanges"
    | "ShowReport"
    | "MissingDocs"
  >("Wizard-Enhanced");

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

  // Handle wizard completion
  const handleWizardComplete = async (setup: DDProjectSetup) => {
    setProjectSetup(setup);
    // For now, just transition to the join project screen
    // In a full implementation, this would create the DD project with the setup data
    setScreenState("Wizard-JoinProject");
  };

  // Get uploaded document filenames for missing docs tracker
  const uploadedDocuments = useMemo(() => {
    if (!dd?.folders) return [];
    return dd.folders.flatMap((folder: any) =>
      folder.documents?.map((doc: any) => doc.original_file_name) ?? []
    );
  }, [dd]);

  return (
    <SidebarProvider>
      <AppSidebar isOpinion={false} />
      <SidebarInset>
        {/* Enhanced Project Wizard Dialog */}
        <Dialog
          open={screenState === "Wizard-Enhanced"}
          onOpenChange={(open) => (!open ? setScreenState("Documents") : null)}
        >
          <DialogContent className="w-[95vw] max-w-[1200px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>New Due Diligence Project</DialogTitle>
              <DialogDescription>
                Set up your DD project with the enhanced wizard
              </DialogDescription>
            </DialogHeader>
            <DDProjectWizard
              onComplete={handleWizardComplete}
              onCancel={() => setScreenState("Documents")}
            />
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
                Join Existing Project
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
              {screenState === "Risks" && "Risks"}
              {screenState === "Questions" && "Questions"}
              {screenState === "ShowReport" && "Generate Report"}
              {screenState === "MissingDocs" && "Document Status"}
            </div>
            <div>
              {screenState === "Documents" && (
                <DocListing folders={dd?.folders} dd_id={selectedDDID} />
              )}
              {screenState === "DocumentChanges" && (
                <DocumentChanges dd_id={selectedDDID} />
              )}
              {screenState === "Search" && <Search />}
              {screenState === "Risks" && <RiskSummary />}
              {screenState === "Questions" && (
                <Questions dd_id={selectedDDID} />
              )}
              {screenState === "ShowReport" && (
                <div>Report generation feature coming soon...</div>
              )}
              {screenState === "MissingDocs" && projectSetup?.transactionType && (
                <MissingDocumentsTracker
                  projectId={selectedDDID || ""}
                  transactionType={projectSetup.transactionType}
                  uploadedDocuments={uploadedDocuments}
                />
              )}
            </div>
          </div>
        )}
        <ChatbotUI folders={dd?.folders} dd_id={selectedDDID} />
      </SidebarInset>
    </SidebarProvider>
  );
}

export default DDMainEnhanced;
