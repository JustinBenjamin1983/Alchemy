import {
  useState,
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
} from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NewAgreementWelcome } from "./NewAgreementWelcome";
import { CLIENT_BRIEFING_TEMPLATE } from "./clientBriefingTemplate";
import {
  Loader2,
  X,
  FileText,
  Upload,
  Star,
  StarOff,
  CheckCircle2,
} from "lucide-react";
import { AgreementChat } from "./AgreementChat";

const ServerFileCard = ({
  file,
  onDelete,
  onSetAsMain,
  type,
  isDeleting = false,
  isMain = false,
}: {
  file: any;
  onDelete: () => void;
  onSetAsMain?: () => void;
  type: "precedent" | "example";
  isDeleting?: boolean;
  isMain?: boolean;
}) => (
  <Card
    className={`relative border transition-colors ${
      isMain
        ? "border-yellow-400 bg-yellow-50 shadow-md"
        : "border-green-200 bg-green-50 hover:border-green-300"
    }`}
  >
    {/* Main Precedent Badge */}
    {isMain && (
      <div className="absolute top-2 left-2 z-10 flex items-center gap-1 bg-yellow-500 text-white px-2 py-1 rounded-full text-xs font-medium">
        <Star className="h-3 w-3 fill-current" />
        Main Template
      </div>
    )}

    {/* Delete Button */}
    <button
      onClick={onDelete}
      disabled={isDeleting}
      className="absolute top-2 right-2 z-10 p-1 rounded-full hover:bg-red-100 transition-colors disabled:opacity-50"
      type="button"
    >
      {isDeleting ? (
        <Loader2 className="h-4 w-4 text-red-500 animate-spin" />
      ) : (
        <X className="h-4 w-4 text-gray-500 hover:text-red-500" />
      )}
    </button>

    {/* Content with proper spacing for badge */}
    <div className={`p-3 ${isMain ? "pt-10" : "pt-3"}`}>
      <div className="flex items-start gap-3 pr-8">
        <FileText
          className={`h-5 w-5 mt-0.5 ${
            isMain ? "text-yellow-600" : "text-green-600"
          }`}
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {file.filename || "Unknown file"}
          </p>
          <p className="text-xs text-gray-500 mt-1">{type} • uploaded</p>

          {/* Set as Main Button (only for precedents and if not already main) */}
          {type === "precedent" && onSetAsMain && !isMain && (
            <button
              onClick={onSetAsMain}
              className="mt-2 flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 transition-colors"
            >
              <StarOff className="h-3 w-3" />
              Set as Main Template
            </button>
          )}
        </div>
      </div>
    </div>
  </Card>
);

const FileCard = ({
  file,
  onRemove,
  type,
}: {
  file: File;
  onRemove: () => void;
  type: "precedent" | "example";
}) => (
  <Card className="relative p-3 border border-gray-200 hover:border-gray-300 transition-colors">
    <button
      onClick={onRemove}
      className="absolute top-2 right-2 p-1 rounded-full hover:bg-gray-100 transition-colors"
      type="button"
    >
      <X className="h-4 w-4 text-gray-500 hover:text-red-500" />
    </button>
    <div className="flex items-start gap-3 pr-8">
      <FileText className="h-5 w-5 text-blue-500 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {file.name}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          {(file.size / 1024 / 1024).toFixed(2)} MB • {type}
        </p>
      </div>
    </div>
  </Card>
);

export const NewAgreement = forwardRef(function NewAgreement(
  {
    existingAgreementId,
  }: {
    existingAgreementId?: string | null;
  },
  ref
) {
  const [screenState, setScreenState] = useState<"Welcome" | "1">("Welcome");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [filePendingUpload, setFilePendingUpload] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [clientBriefingText, setClientBriefingText] = useState<string>(
    CLIENT_BRIEFING_TEMPLATE
  );
  const [submitting, setSubmitting] = useState(false);
  const [agreementInfo, setAgreementInfo] = useState<any>(null);
  const [agreementName, setAgreementName] = useState("");
  const [governingLaw, setGoverningLaw] = useState("");
  const [disputeResolution, setDisputeResolution] = useState({
    courts: "",
    arbitration: "",
    mediation: "",
  });
  const [parties, setParties] = useState<any[]>([]);
  const [unlockedTabs, setUnlockedTabs] = useState<string[]>([
    "client_briefing",
  ]);
  const [activeTab, setActiveTab] = useState("client_briefing");
  const [agreementDocId, setAgreementDocId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [generatedAgreements, setGeneratedAgreements] = useState<any[]>([]);
  const [progressMsgs, setProgressMsgs] = useState<string[]>([]);
  const [percent, setPercent] = useState<number>(0);
  const API_BASE = import.meta.env.VITE_API_BASE_URL;
  const [mainPrecedentId, setMainPrecedentId] = useState<string | null>(null);

  useImperativeHandle(ref, () => ({
    resetAgreementState,
  }));

  const toggleItem = (item: string) => {
    setSelectedTags((prev) =>
      prev.includes(item) ? prev.filter((i) => i !== item) : [...prev, item]
    );
  };

  const [clauses, setClauses] = useState<any[]>([]);
  const [selectedClauseIds, setSelectedClauseIds] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/api/clauses`)
      .then((res) => res.json())
      .then((data) => setClauses(data.clauses))
      .catch(console.error);
  }, []);

  const toggleClause = (id: string) => {
    setSelectedClauseIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const deleteGeneratedAgreement = async (filename: string) => {
    if (!agreementDocId) {
      console.error("No agreementDocId set");
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/delete_generated_agreement/${agreementDocId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filename }),
        }
      );
      if (res.ok) {
        setGeneratedAgreements((prev) =>
          prev.filter((ag) => ag.name !== filename)
        );
        console.log("Deleted generated agreement", filename);
      } else {
        console.error("Failed to delete generated agreement");
      }
    } catch (err) {
      console.error("Error deleting generated agreement", err);
    } finally {
      setSaving(false);
    }
  };

  const setMainPrecedent = async (fileId: string) => {
    if (!agreementDocId) return;

    try {
      const res = await fetch(
        `${API_BASE}/api/set_main_precedent/${agreementDocId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ main_precedent_id: fileId }),
        }
      );

      if (res.ok) {
        setMainPrecedentId(fileId);
        console.log(`Set main precedent: ${fileId}`);
      } else {
        console.error("Failed to set main precedent");
      }
    } catch (err) {
      console.error("Error setting main precedent:", err);
    }
  };

  const deleteServerFile = async (
    fileId: string,
    type: "precedent" | "example"
  ) => {
    if (!agreementDocId) return;

    try {
      const res = await fetch(
        `${API_BASE}/api/delete_precedent_file/${agreementDocId}/${fileId}`,
        { method: "DELETE" }
      );

      if (res.ok) {
        if (type === "precedent") {
          setServerPrecedentFiles((prev) =>
            prev.filter((f) => f.id !== fileId)
          );

          // If we deleted the main precedent, clear the main precedent selection
          if (mainPrecedentId === fileId) {
            setMainPrecedentId(null);
          }
        } else {
          setServerExampleFiles((prev) => prev.filter((f) => f.id !== fileId));
        }
        console.log(`Deleted ${type} file: ${fileId}`);
      } else {
        console.error(`Failed to delete ${type} file`);
      }
    } catch (err) {
      console.error(`Error deleting ${type} file:`, err);
    }
  };

  const saveClauses = async () => {
    if (!agreementDocId) {
      console.error("No agreementDocId set");
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/update_agreement_doc/${agreementDocId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ additional_clauses: selectedClauseIds }),
        }
      );
      if (res.ok) {
        console.log("Clauses saved");
        setUnlockedTabs((prev) => [...new Set([...prev, "sample_agreement"])]);
        setActiveTab("sample_agreement");
      } else {
        console.error("Failed to save clauses");
      }
    } catch (err) {
      console.error("Error saving clauses", err);
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    if (existingAgreementId) {
      fetch(`${API_BASE}/api/get_agreement_doc/${existingAgreementId}`)
        .then((res) => res.json())
        .then((data) => {
          setAgreementDocId(existingAgreementId);
          setClientBriefingText(data.client_brief || "");
          setAgreementName(data.agreement_name || "");
          setGeneratedAgreements(data.generated_agreements || []);
          setGoverningLaw(data.governing_law || "");
          setDisputeResolution(
            data.dispute_resolution || {
              courts: "",
              arbitration: "",
              mediation: "",
            }
          );
          setParties(data.parties || []);

          // Handle server-stored files
          setServerPrecedentFiles(data.precedent_files || []);
          setServerExampleFiles(data.example_files || []);

          // Handle main precedent selection
          setMainPrecedentId(data.main_precedent_id || null);

          // Clear local file selections when loading existing agreement
          setPrecedentFiles([]);
          setExampleFiles([]);

          // Dynamically unlock all tabs based on what is filled
          const unlocked = ["client_briefing"];
          if (
            data.agreement_name ||
            data.governing_law ||
            data.dispute_resolution
          ) {
            unlocked.push("additional_information");
          }
          if (data.parties && data.parties.length > 0) {
            unlocked.push("parties");
          }
          if (data.additional_clauses || data.selected_tags) {
            unlocked.push("additional_clauses");
          }
          // Updated condition for precedents/examples
          if (
            data.precedent ||
            data.example ||
            (data.precedent_files && data.precedent_files.length > 0) ||
            (data.example_files && data.example_files.length > 0)
          ) {
            unlocked.push("precedents");
            unlocked.push("sample_agreement");
          }
          setUnlockedTabs(unlocked);
          setScreenState("1");
          setActiveTab(unlocked[unlocked.length - 1]);
        })
        .catch(console.error);
    }
  }, [existingAgreementId]);

  const resetAgreementState = () => {
    setScreenState("Welcome");
    setClientBriefingText(CLIENT_BRIEFING_TEMPLATE);
    setAgreementName("");
    setGoverningLaw("");
    setDisputeResolution({ courts: "", arbitration: "", mediation: "" });
    setParties([]);
    setSelectedTags([]);
    setPrecedentFiles([]);
    setExampleFiles([]);
    setServerPrecedentFiles([]);
    setServerExampleFiles([]);
    setMainPrecedentId(null); // Add this line
    setUnlockedTabs(["client_briefing"]);
    setActiveTab("client_briefing");
    setAgreementDocId(null);
    setAgreementInfo(null);
  };

  const generateAgreement = async () => {
    if (!agreementDocId) return;

    setSaving(true);
    setProgressMsgs([]);
    setPercent(0);

    // 👇 open SSE stream
    const es = new EventSource(
      `${API_BASE}/api/generate_agreement_stream/${agreementDocId}`
    );

    es.onmessage = (e) => {
      const data = JSON.parse(e.data);

      if (data.type === "start") {
        setPercent(0);
      }
      if (data.type === "progress") {
        setProgressMsgs((prev) => [...prev, data.msg]);
        setPercent(Math.round((data.step / data.total) * 100));
      }
      if (data.type === "done") {
        setGeneratedAgreements((prev) => [
          ...prev,
          { name: data.filename, url: data.pdf_url },
        ]);
        setPercent(100);
        es.close();
        setSaving(false);
      }
      if (data.type === "error") {
        setProgressMsgs((prev) => [...prev, `❌ ${data.msg}`]);
        es.close();
        setSaving(false);
      }
    };

    es.onerror = (err) => {
      setProgressMsgs((prev) => [...prev, "Stream error – see console"]);
      console.error(err);
      es.close();
      setSaving(false);
    };
  };

  const [precedentFiles, setPrecedentFiles] = useState<File[]>([]); // Local files only
  const [exampleFiles, setExampleFiles] = useState<File[]>([]); // Local files only
  const [serverPrecedentFiles, setServerPrecedentFiles] = useState<any[]>([]); // Server files
  const [serverExampleFiles, setServerExampleFiles] = useState<any[]>([]);

  const handlePrecedentChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setPrecedentFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const handleExampleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setExampleFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const removePrecedentFile = (index: number) => {
    setPrecedentFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const removeExampleFile = (index: number) => {
    setExampleFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const savePrecedentsExamples = async () => {
    if (!agreementDocId) {
      console.error("No agreementDocId set");
      return;
    }
    setSaving(true);
    try {
      const formData = new FormData();
      // Append all precedent files
      precedentFiles.forEach((file, index) => {
        formData.append(`precedents`, file);
      });
      // Append all example files
      exampleFiles.forEach((file, index) => {
        formData.append(`examples`, file);
      });

      const res = await fetch(
        `${API_BASE}/api/upload_precedents/${agreementDocId}`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (res.ok) {
        const result = await res.json();

        // Update server file lists with newly uploaded files
        if (result.precedent_files) {
          setServerPrecedentFiles((prev) => [
            ...prev,
            ...result.precedent_files,
          ]);

          // Auto-select first precedent as main if no main precedent is set
          if (!mainPrecedentId && result.precedent_files.length > 0) {
            const firstPrecedentId = result.precedent_files[0].id;
            setMainPrecedentId(firstPrecedentId);

            // Also update on server
            await fetch(
              `${API_BASE}/api/set_main_precedent/${agreementDocId}`,
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ main_precedent_id: firstPrecedentId }),
              }
            );
          }
        }
        if (result.example_files) {
          setServerExampleFiles((prev) => [...prev, ...result.example_files]);
        }

        // Clear local file selections after successful upload
        setPrecedentFiles([]);
        setExampleFiles([]);

        console.log("Precedents and examples uploaded");
        setUnlockedTabs((prev) => [
          ...new Set([...prev, "additional_clauses"]),
        ]);
        setActiveTab("additional_clauses");
      } else {
        console.error("Failed to upload precedents/examples");
      }
    } catch (err) {
      console.error("Error uploading precedents/examples", err);
    } finally {
      setSaving(false);
    }
  };

  const saveAgreement = async () => {
    setSaving(true);
    const url = agreementDocId
      ? `${API_BASE}/api/update_agreement_doc/${agreementDocId}`
      : `${API_BASE}/api/create_agreement_doc`;

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_brief: clientBriefingText,
          agreement_name: agreementName,
          governing_law: governingLaw,
          dispute_resolution: disputeResolution,
          parties,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (!agreementDocId) setAgreementDocId(data.doc_id);
        console.log("Agreement saved");
        setUnlockedTabs((prev) => [...new Set([...prev, "parties"])]);
        setActiveTab("parties");
      } else {
        console.error("Failed to save agreement");
      }
    } catch (err) {
      console.error("Error saving agreement", err);
    } finally {
      setSaving(false);
    }
  };

  const submitClientBriefing = async () => {
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/client_briefing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: clientBriefingText }),
      });
      if (res.ok) {
        const data = await res.json();
        setAgreementInfo(data);

        setAgreementName(data.agreement_name || "");
        setGoverningLaw(data.governing_law || "");

        setDisputeResolution({
          courts: data.dispute_resolution?.courts || "",
          arbitration: data.dispute_resolution?.arbitration || "",
          mediation: data.dispute_resolution?.mediation || "",
        });

        const partiesObj = data.parties || {};
        const partiesArray = Object.entries(partiesObj).map(
          ([name, details]: any) => ({
            name,
            type: details.type || "",
            address: details.address || "",
            incorporation: details.incorporation || "",
            registration_number: details.registration_number || "",
          })
        );
        setParties(partiesArray);
        setUnlockedTabs((prev) => [
          ...new Set([...prev, "additional_information"]),
        ]);
        setActiveTab("additional_information");
      } else {
        console.error("Failed to submit client briefing");
      }
    } catch (err) {
      console.error("Error submitting client briefing", err);
    } finally {
      setSubmitting(false);
    }
  };

  const saveParties = async () => {
    if (!agreementDocId) {
      console.error("No agreementDocId set");
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/update_agreement_doc/${agreementDocId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ parties }),
        }
      );
      if (res.ok) {
        console.log("Parties saved");
        setUnlockedTabs((prev) => [...new Set([...prev, "precedents"])]);
        setActiveTab("precedents");
      } else {
        console.error("Failed to save parties");
      }
    } catch (err) {
      console.error("Error saving parties", err);
    } finally {
      setSaving(false);
    }
  };

  const loadAgreement = async (docId: string) => {
    const res = await fetch(`${API_BASE}/api/get_agreement/${docId}`);
    if (res.ok) {
      const data = await res.json();
      setAgreementDocId(docId);
      setClientBriefingText(data.client_brief || "");
      setAgreementName(data.agreement_name || "");
      setGoverningLaw(data.governing_law || "");
      setGeneratedAgreements(data.generated_agreements || []);
      setDisputeResolution(
        data.dispute_resolution || {
          courts: "",
          arbitration: "",
          mediation: "",
        }
      );
      setParties(data.parties || []);

      // Unlock tabs based on what's present
      const unlocked = ["client_briefing"];
      if (
        data.agreement_name ||
        data.governing_law ||
        data.dispute_resolution
      ) {
        unlocked.push("additional_information");
      }
      if (data.parties) {
        unlocked.push("parties");
      }
      if (data.additional_clauses) {
        unlocked.push("additional_clauses");
      }
      // Extend this pattern if needed
      setUnlockedTabs(unlocked);
      setActiveTab(unlocked[unlocked.length - 1]);
    } else {
      console.error("Failed to load agreement");
    }
  };

  const handleButtonClick = () => fileInputRef.current?.click();
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFiles(file);
  };
  const handleFiles = (file: File) => {
    setUploadError(null);
    setFilePendingUpload(file);
  };
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDraggingFile(true);
  };
  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDraggingFile(false);
  };
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDraggingFile(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFiles(file);
  };

  const UploadArea = () => (
    <>
      <div
        className={`border-2 border-dotted shadow-md h-[150px] cursor-pointer border-black rounded-xl grid place-items-center ${
          isDraggingFile ? "bg-gray-100" : ""
        }`}
        onClick={handleButtonClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="text-center">
          <span className="underline">Click to upload</span> or drag and drop
          <div className="italic text-sm pt-2">{filePendingUpload?.name}</div>
          {uploadError && (
            <div className="text-red-600 text-sm pt-2">{uploadError}</div>
          )}
        </div>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileInputChange}
      />
    </>
  );

  return (
    <>
      <header className="flex h-4 shrink-0 items-center gap-2"></header>

      <main>
        {screenState === "Welcome" && (
          <NewAgreementWelcome onStart={() => setScreenState("1")} />
        )}

        {screenState != "Welcome" && (
          <>
            <Tabs
              value={activeTab}
              onValueChange={setActiveTab}
              className="w-full p-8"
            >
              <TabsList className="mb-4">
                <TabsTrigger value="client_briefing">Client Brief</TabsTrigger>
                <TabsTrigger
                  value="additional_information"
                  disabled={!unlockedTabs.includes("additional_information")}
                >
                  Additional Information
                </TabsTrigger>
                <TabsTrigger
                  value="parties"
                  disabled={!unlockedTabs.includes("parties")}
                >
                  Parties
                </TabsTrigger>
                <TabsTrigger
                  value="precedents"
                  disabled={!unlockedTabs.includes("precedents")}
                >
                  Precedents & Examples
                </TabsTrigger>
                <TabsTrigger
                  value="additional_clauses"
                  disabled={!unlockedTabs.includes("additional_clauses")}
                >
                  Clause Library
                </TabsTrigger>
                <TabsTrigger value="assistant">Assistant</TabsTrigger>
                <TabsTrigger
                  value="sample_agreement"
                  disabled={!unlockedTabs.includes("sample_agreement")}
                >
                  Generation
                </TabsTrigger>
              </TabsList>

              <TabsContent value="client_briefing">
                <div className="max-h-[600px] pr-2">
                  <Card className="mb-4">
                    <CardContent className="p-4">
                      <div>
                        <div className="text-lg font-semibold mb-2">
                          Client Briefing
                        </div>
                        <Textarea
                          rows={17}
                          value={clientBriefingText}
                          onChange={(e) =>
                            setClientBriefingText(e.target.value)
                          }
                        />
                      </div>

                      <div className="pt-4">
                        <Button
                          className=" text-white"
                          onClick={submitClientBriefing}
                          disabled={submitting}
                        >
                          {submitting ? (
                            <Loader2 className="animate-spin h-4 w-4" />
                          ) : (
                            "Submit Client Briefing"
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
              <TabsContent value="additional_information">
                <div className="max-h-[600px] overflow-y-auto pr-2">
                  <Card className="mb-4">
                    <CardContent className="p-4">
                      <>
                        <div className="pb-6">
                          <div className="text-2xl font-bold pb-2">
                            Agreement Name
                          </div>
                          <Input
                            value={agreementName}
                            onChange={(e) => setAgreementName(e.target.value)}
                          />
                        </div>

                        <div className="pb-6">
                          <div className="text-2xl font-bold pb-2">
                            Governing Law
                          </div>
                          <Input
                            value={governingLaw}
                            onChange={(e) => setGoverningLaw(e.target.value)}
                          />
                        </div>

                        <div className="pb-4 text-2xl font-semibold">
                          Dispute Resolution
                        </div>

                        <div className="pb-4">
                          <Label className="font-medium">Courts</Label>
                          <Textarea
                            rows={2}
                            value={disputeResolution.courts}
                            onChange={(e) =>
                              setDisputeResolution({
                                ...disputeResolution,
                                courts: e.target.value,
                              })
                            }
                          />
                        </div>

                        <div className="pb-4">
                          <Label className="font-medium">Arbitration</Label>
                          <Textarea
                            rows={2}
                            value={disputeResolution.arbitration}
                            onChange={(e) =>
                              setDisputeResolution({
                                ...disputeResolution,
                                arbitration: e.target.value,
                              })
                            }
                          />
                        </div>

                        <div className="pb-4">
                          <Label className="font-medium">Mediation</Label>
                          <Textarea
                            rows={2}
                            value={disputeResolution.mediation}
                            onChange={(e) =>
                              setDisputeResolution({
                                ...disputeResolution,
                                mediation: e.target.value,
                              })
                            }
                          />
                        </div>
                      </>
                    </CardContent>
                  </Card>
                </div>
                <div className="pt-4">
                  <Button
                    className="text-white"
                    onClick={saveAgreement}
                    disabled={saving}
                  >
                    {saving ? (
                      <Loader2 className="animate-spin h-4 w-4" />
                    ) : (
                      "Save Agreement"
                    )}
                  </Button>
                </div>
              </TabsContent>

              <TabsContent value="parties">
                <div className="max-h-[600px] overflow-y-auto pr-2">
                  <Card className="mb-4">
                    <CardContent className="p-4">
                      <>
                        <div className="pb-4 text-xl font-semibold">
                          Parties
                        </div>
                        {parties.map((party, index) => (
                          <div
                            key={party.name}
                            className="border p-2 rounded mb-4"
                          >
                            <div className="font-semibold text-lg pb-2">
                              {party.name}
                            </div>
                            <div className="grid grid-cols-2 gap-4 pb-2">
                              <div>
                                <Label>Type</Label>
                                <Input
                                  value={party.type}
                                  onChange={(e) => {
                                    const updated = [...parties];
                                    updated[index].type = e.target.value;
                                    setParties(updated);
                                  }}
                                />
                              </div>
                              <div>
                                <Label>Address</Label>
                                <Input
                                  value={party.address}
                                  onChange={(e) => {
                                    const updated = [...parties];
                                    updated[index].address = e.target.value;
                                    setParties(updated);
                                  }}
                                />
                              </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4 pb-2">
                              <div>
                                <Label>Incorporation</Label>
                                <Input
                                  value={party.incorporation}
                                  onChange={(e) => {
                                    const updated = [...parties];
                                    updated[index].incorporation =
                                      e.target.value;
                                    setParties(updated);
                                  }}
                                />
                              </div>
                              <div>
                                <Label>Registration Number</Label>
                                <Input
                                  value={party.registration_number}
                                  onChange={(e) => {
                                    const updated = [...parties];
                                    updated[index].registration_number =
                                      e.target.value;
                                    setParties(updated);
                                  }}
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                      </>
                    </CardContent>
                  </Card>
                  <div className="pt-4">
                    <Button
                      className="text-white"
                      onClick={saveParties}
                      disabled={saving}
                    >
                      {saving ? (
                        <Loader2 className="animate-spin h-4 w-4" />
                      ) : (
                        "Save Parties"
                      )}
                    </Button>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="sample_agreement">
                <div className="max-h-[600px] overflow-y-auto pr-2">
                  <Card className="mb-4">
                    <CardContent className="p-4">
                      <div className="font-semibold text-lg mb-2">
                        Agreements Generated
                      </div>
                      <table className="w-full border-collapse border">
                        <thead>
                          <tr>
                            <th className="border p-2 text-left">Name</th>
                            <th className="border p-2 text-left">URL</th>
                            <th className="border p-2 text-left">Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {generatedAgreements.map((ag, idx) => (
                            <tr key={idx}>
                              <td className="border p-2">{ag.name}</td>
                              <td className="border p-2">
                                <td className="border p-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                      window.open(
                                        `${API_BASE}/api/agreement_file/${agreementDocId}/${encodeURIComponent(
                                          ag.name
                                        )}`,
                                        "_blank"
                                      );
                                    }}
                                  >
                                    Download
                                  </Button>
                                </td>
                              </td>
                              <td className="border p-2">
                                <Button
                                  variant="destructive"
                                  size="sm"
                                  onClick={() =>
                                    deleteGeneratedAgreement(ag.name)
                                  }
                                  disabled={saving}
                                >
                                  {saving ? (
                                    <Loader2 className="animate-spin h-4 w-4" />
                                  ) : (
                                    "Delete"
                                  )}
                                </Button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <div className="pt-4">
                        <Button
                          className="text-white"
                          onClick={generateAgreement}
                          disabled={saving}
                        >
                          {saving ? (
                            <Loader2 className="animate-spin h-4 w-4" />
                          ) : (
                            "Generate"
                          )}
                        </Button>
                        {saving && (
                          <div className="mt-4 space-y-2">
                            {/* progress bar */}
                            <div className="h-2 bg-gray-200 rounded">
                              <div
                                className="h-2 bg-green-500 rounded transition-all duration-200"
                                style={{ width: `${percent}%` }}
                              />
                            </div>

                            {/* scrolling log */}
                            <ul className="text-sm max-h-32 overflow-y-auto border p-2 rounded">
                              {progressMsgs.map((m, i) => (
                                <li key={i}>{m}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="precedents">
                <div className="max-h-[600px] overflow-y-auto pr-2">
                  <Card className="mb-4">
                    <CardContent className="p-6">
                      <div className="space-y-6">
                        {/* Server-stored Precedents Section */}
                        {serverPrecedentFiles.length > 0 && (
                          <div>
                            <div className="flex items-center gap-2 mb-3">
                              <Label className="text-base font-semibold text-green-700">
                                Uploaded Precedents
                              </Label>
                              <span className="text-xs text-green-600">
                                ({serverPrecedentFiles.length} file
                                {serverPrecedentFiles.length !== 1
                                  ? "s"
                                  : ""}{" "}
                                uploaded)
                              </span>
                              {mainPrecedentId && (
                                <div className="flex items-center gap-1 text-xs text-yellow-600 font-medium">
                                  <Star className="h-3 w-3 fill-current" />
                                  Template selected
                                </div>
                              )}
                            </div>
                            <div className="grid gap-2 max-h-40 overflow-y-auto">
                              {serverPrecedentFiles.map((file) => (
                                <ServerFileCard
                                  key={`server-precedent-${file.id}`}
                                  file={file}
                                  type="precedent"
                                  isMain={mainPrecedentId === file.id}
                                  onDelete={() =>
                                    deleteServerFile(file.id, "precedent")
                                  }
                                  onSetAsMain={() => setMainPrecedent(file.id)}
                                />
                              ))}
                            </div>

                            {/* Main Precedent Info */}
                            {mainPrecedentId && (
                              <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                                <div className="flex items-center gap-2 text-sm text-yellow-800">
                                  <CheckCircle2 className="h-4 w-4" />
                                  The selected main template will be used for
                                  document structure and formatting.
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Local Precedents Section */}
                        <div>
                          <div className="flex items-center gap-2 mb-3">
                            <Label className="text-base font-semibold">
                              Upload New Precedents
                            </Label>
                            <span className="text-xs text-gray-500">
                              ({precedentFiles.length} file
                              {precedentFiles.length !== 1 ? "s" : ""} selected)
                            </span>
                          </div>
                          <div className="space-y-3">
                            <Input
                              type="file"
                              multiple
                              accept=".pdf,.doc,.docx"
                              onChange={handlePrecedentChange}
                              className="cursor-pointer"
                            />
                            {precedentFiles.length > 0 && (
                              <div className="grid gap-2 max-h-40 overflow-y-auto">
                                {precedentFiles.map((file, index) => (
                                  <FileCard
                                    key={`precedent-${index}-${file.name}`}
                                    file={file}
                                    type="precedent"
                                    onRemove={() => removePrecedentFile(index)}
                                  />
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Server-stored Examples Section - unchanged */}
                        {serverExampleFiles.length > 0 && (
                          <div>
                            <div className="flex items-center gap-2 mb-3">
                              <Label className="text-base font-semibold text-green-700">
                                Uploaded Examples
                              </Label>
                              <span className="text-xs text-green-600">
                                ({serverExampleFiles.length} file
                                {serverExampleFiles.length !== 1
                                  ? "s"
                                  : ""}{" "}
                                uploaded)
                              </span>
                            </div>
                            <div className="grid gap-2 max-h-40 overflow-y-auto">
                              {serverExampleFiles.map((file) => (
                                <ServerFileCard
                                  key={`server-example-${file.id}`}
                                  file={file}
                                  type="example"
                                  onDelete={() =>
                                    deleteServerFile(file.id, "example")
                                  }
                                />
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Local Examples Section - unchanged */}
                        <div>
                          <div className="flex items-center gap-2 mb-3">
                            <Label className="text-base font-semibold">
                              Upload New Examples
                            </Label>
                            <span className="text-xs text-gray-500">
                              ({exampleFiles.length} file
                              {exampleFiles.length !== 1 ? "s" : ""} selected)
                            </span>
                          </div>
                          <div className="space-y-3">
                            <Input
                              type="file"
                              multiple
                              accept=".pdf,.doc,.docx"
                              onChange={handleExampleChange}
                              className="cursor-pointer"
                            />
                            {exampleFiles.length > 0 && (
                              <div className="grid gap-2 max-h-40 overflow-y-auto">
                                {exampleFiles.map((file, index) => (
                                  <FileCard
                                    key={`example-${index}-${file.name}`}
                                    file={file}
                                    type="example"
                                    onRemove={() => removeExampleFile(index)}
                                  />
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Upload Summary - unchanged */}
                        {(precedentFiles.length > 0 ||
                          exampleFiles.length > 0) && (
                          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                            <div className="flex items-center gap-2 mb-2">
                              <Upload className="h-4 w-4 text-blue-600" />
                              <span className="text-sm font-medium text-blue-900">
                                Ready to Upload
                              </span>
                            </div>
                            <p className="text-xs text-blue-700">
                              {precedentFiles.length} precedent
                              {precedentFiles.length !== 1 ? "s" : ""} and{" "}
                              {exampleFiles.length} example
                              {exampleFiles.length !== 1 ? "s" : ""} will be
                              uploaded.
                              {precedentFiles.length > 0 &&
                                !mainPrecedentId && (
                                  <span className="block mt-1 font-medium">
                                    The first precedent will be automatically
                                    set as the main template.
                                  </span>
                                )}
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="pt-6 border-t mt-6">
                        <Button
                          className="text-white"
                          onClick={savePrecedentsExamples}
                          disabled={
                            saving ||
                            (precedentFiles.length === 0 &&
                              exampleFiles.length === 0)
                          }
                        >
                          {saving ? (
                            <Loader2 className="animate-spin h-4 w-4 mr-2" />
                          ) : (
                            <Upload className="h-4 w-4 mr-2" />
                          )}
                          {saving ? "Uploading..." : "Upload New Files"}
                        </Button>

                        {(serverPrecedentFiles.length > 0 ||
                          serverExampleFiles.length > 0) && (
                          <p className="text-xs text-gray-500 mt-2">
                            You have{" "}
                            {serverPrecedentFiles.length +
                              serverExampleFiles.length}{" "}
                            file(s) already uploaded.
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="assistant">
                <div className="max-h-[600px] overflow-y-auto pr-2">
                  <AgreementChat
                    contextTitle={agreementName || "Untitled Agreement"}
                    contextPreview={clientBriefingText}
                  />
                </div>
              </TabsContent>

              <TabsContent value="additional_clauses">
                <div className="max-h-[600px] overflow-y-auto pr-2">
                  <Card className="mb-4">
                    <CardContent className="p-4">
                      <div className="grid grid-cols-[350px_1fr]">
                        <div>What other clauses are important to include</div>
                        <div>
                          <div className="flex flex-wrap gap-2 py-4">
                            {clauses.map((clause) => {
                              const isSelected = selectedClauseIds.includes(
                                clause.id
                              );
                              const displayName = clause.name.replace(
                                /\.pdf$/i,
                                ""
                              );
                              return (
                                <Button
                                  key={clause.id}
                                  className={`px-4 py-2 text-black rounded border ${
                                    isSelected ? "bg-green-300" : "bg-gray-200"
                                  }`}
                                  onClick={() => toggleClause(clause.id)}
                                >
                                  {displayName}
                                </Button>
                              );
                            })}
                          </div>
                          <div>
                            <div className="max-h-[600px] overflow-y-auto pr-2">
                              <Card className="mb-4">
                                <CardContent className="p-4">
                                  <div className="grid grid-cols-[200px_1fr]">
                                    <div>Attach additional clauses</div>
                                    <div>
                                      <div className="flex flex-col gap-2 pb-4">
                                        <Label>Clause name</Label>
                                        <Input />
                                      </div>
                                      <UploadArea />
                                    </div>
                                  </div>
                                </CardContent>
                              </Card>
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
                <div className="pt-4">
                  <Button
                    className="text-white"
                    onClick={saveClauses}
                    disabled={saving}
                  >
                    {saving ? (
                      <Loader2 className="animate-spin h-4 w-4" />
                    ) : (
                      "Save Clauses"
                    )}
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          </>
        )}
      </main>
    </>
  );
});
