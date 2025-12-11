// File: ui/src/pages/OpinionWriter/OpinionMain.tsx

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { SidebarInset, SidebarProvider } from "../../components/ui/sidebar";
import { useMutateCompileOpinion } from "@/hooks/useMutateCompileOpinion";
import { toast } from "sonner";
import { OpinionViewToggle, OpinionView } from "./OpinionViewToggle";

import { Textarea } from "@/components/ui/textarea";
import {
  CornerDownLeft,
  Loader2,
  Paperclip,
  CheckCircle2,
  Circle,
  Plus,
  Save,
  RefreshCw,
  X,
} from "lucide-react";
import { useMutateDeleteOpinion } from "@/hooks/useMutateDeleteOpinion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useEffect, useState, useRef, useCallback } from "react";
import { useMutateCreateOpinion } from "@/hooks/useMutateCreateOpinion";
import { AppSidebar } from "./AppSideBar";
import { useNavigate, useLocation } from "react-router-dom";
import { useGetOpinion } from "@/hooks/useGetOpinion";
import { useMutateSaveOpinion } from "@/hooks/useMutateSaveOpinion";
import { useMutateGenerateOpinion } from "@/hooks/useMutateGenerateOpinion";
import { Uploader } from "@/components/Uploader";
import { DocLister } from "@/components/DocLister";
import { useGetGlobalOpinionDocs } from "@/hooks/useGetGlobalOpinionDocs";
import { Top } from "@/components/Top";
import { cn } from "@/lib/utils";
import { useMutateGetLink } from "@/hooks/useMutateGetLink";
import { useMutateGetOpinionDraft } from "@/hooks/useMutateGetOpinionDraft";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useMutateGetPrecedents } from "@/hooks/useMutateGetPrecedents";
import PrecedentsListing from "@/components/PrecedentsListing";
import { useMutateSaveStagingDraft } from "@/hooks/useMutateSaveStagingDraft";
import { useMutateApplyChangesToDraft } from "@/hooks/useMutateApplyChangesToDraft";
import { OpinionStep } from "./types";
import { AlchemioChat } from "./AlchemioChat";
import { EnhancedOpinionDisplay } from "./EnhancedOpinionDisplay";
import { DiffViewer } from "./DiffViewer";

type OpinionOutputs = {
  initialDraft?: string;
  verificationReport?: string;
  rewrittenDraft?: string;
  docs?: any[];
};

export function OpinionMain() {
  const mutateCompileOpinion = useMutateCompileOpinion();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const mutateDeleteOpinion = useMutateDeleteOpinion();
  const [compileError, setCompileError] = useState<string | null>(null);
  const [compileTo, setCompileTo] = useState<string>("");
  const [compileUrl, setCompileUrl] = useState<string | null>(null);
  const [compileFileName, setCompileFileName] = useState<string | null>(null);
  const [compileDate, setCompileDate] = useState<string>(() => {
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  });
  const [compileRe, setCompileRe] = useState<string>("");
  const [templateFile, setTemplateFile] = useState<File | null>(null);
  const [templateB64, setTemplateB64] = useState<string | null>(null);
  const [defaultTemplateB64, setDefaultTemplateB64] = useState<string | null>(
    null
  );
  const [defaultTemplateType, setDefaultTemplateType] = useState<"al" | "adr">(
    "al"
  );
  const [alTemplateB64, setAlTemplateB64] = useState<string | null>(null);
  const [adrTemplateB64, setAdrTemplateB64] = useState<string | null>(null);
  const [isLoadingDefaultTemplate, setIsLoadingDefaultTemplate] =
    useState(false);
  const defaultTemplateLoadedRef = useRef<{ al: boolean; adr: boolean }>({
    al: false,
    adr: false,
  });
  const [useCustomTemplate, setUseCustomTemplate] = useState(false);

  // ==== NEW: multi-pane state ====
  const [activeView, setActiveView] = useState<OpinionView>("rewritten");
  const [outputs, setOutputs] = useState<OpinionOutputs>({});
  const [workingText, setWorkingText] = useState<{
    initial?: string;
    rewritten?: string;
  }>({});

  // Diff tracking state for AI changes
  const [showDiffView, setShowDiffView] = useState(false);
  const [appliedAIChanges, setAppliedAIChanges] = useState<
    Array<{
      id: string;
      type: "replace" | "insert" | "delete";
      startIndex: number;
      endIndex: number;
      originalText?: string;
      newText?: string;
      reasoning?: string;
    }>
  >([]);
  const [originalTextBeforeChanges, setOriginalTextBeforeChanges] =
    useState<string>("");

  // add this small helper just above normalizeGeneratedPayload
  const formatVerification = (v: any): string => {
    if (!v) return "";
    if (typeof v === "string") return v;

    const lines: string[] = [];
    if (v.summary) lines.push(`Summary: ${v.summary}`);

    if (Array.isArray(v.citations) && v.citations.length > 0) {
      lines.push(
        [
          "Citations:",
          ...v.citations.map((c: any, i: number) =>
            typeof c === "string"
              ? `  ${i + 1}. ${c}`
              : `  ${i + 1}. ${c.title || c.id || "citation"}`
          ),
        ].join("\n")
      );
    } else {
      lines.push("Citations: none found.");
    }

    if (Array.isArray(v.verified_cases) && v.verified_cases.length > 0) {
      lines.push(
        [
          "Verified cases:",
          ...v.verified_cases.map((c: any, i: number) =>
            typeof c === "string"
              ? `  ${i + 1}. ${c}`
              : `  ${i + 1}. ${c.title || c.name || c.id || "case"}`
          ),
        ].join("\n")
      );
    }

    return lines.join("\n\n");
  };

  const handleDeleteRequest = () => {
    setShowDeleteConfirm(true);
  };

  const confirmDelete = () => {
    if (!selectedOpinionId) return;
    mutateDeleteOpinion.mutate(
      { opinion_id: selectedOpinionId },
      {
        onSuccess: () => {
          setShowDeleteConfirm(false);
          startNewOpinion(); // Navigate back to create new opinion
          // Refresh the sidebar by triggering a re-render
          window.location.reload(); // Simple way to refresh sidebar data
        },
      }
    );
  };

  const cancelDelete = () => setShowDeleteConfirm(false);

  const normalizeGeneratedPayload = (raw: any): OpinionOutputs => {
    if (!raw) return {};

    // INITIAL: prefer top-level draft (string) or nested initial fields
    const initial =
      (typeof raw.draft === "string" && raw.draft) ||
      (typeof raw?.draft === "object" &&
        typeof raw.draft.initial_draft === "string" &&
        raw.draft.initial_draft) ||
      (typeof raw.initial_draft === "string" && raw.initial_draft) ||
      (typeof raw.initialDraft === "string" && raw.initialDraft) ||
      undefined;

    // REWRITTEN: prefer final_draft, then common rewritten keys
    const rewritten =
      (typeof raw.final_draft === "string" && raw.final_draft) ||
      (typeof raw.rewritten_draft === "string" && raw.rewritten_draft) ||
      (typeof raw.rewrittenDraft === "string" && raw.rewrittenDraft) ||
      (typeof raw?.draft === "object" &&
        typeof raw.draft.rewritten_draft === "string" &&
        raw.draft.rewritten_draft) ||
      (typeof raw?.draft === "object" &&
        typeof raw.draft.final_draft === "string" &&
        raw.draft.final_draft) ||
      undefined;

    // VERIFICATION: accept string or object; object is formatted
    const verification =
      (typeof raw.verification_report === "string" &&
        raw.verification_report) ||
      (raw.verification_report &&
        formatVerification(raw.verification_report)) ||
      (typeof raw.verificationReport === "string" && raw.verificationReport) ||
      (typeof raw.report === "string" && raw.report) ||
      undefined;

    const docs =
      (Array.isArray(raw.docs) && raw.docs) ||
      (Array.isArray(raw?.draft?.docs) && raw.draft.docs) ||
      [];

    return {
      initialDraft: initial,
      rewrittenDraft: rewritten,
      verificationReport: verification,
      docs,
    };
  };

  const getActiveDraftText = () => {
    if (activeView === "verification") {
      return outputs.verificationReport ?? "";
    }

    if (activeView === "rewritten") {
      return (
        workingText.rewritten ??
        outputs.rewrittenDraft ??
        outputs.initialDraft ??
        modifiedOpinionText ??
        ""
      );
    }

    // initial
    return (
      workingText.initial ??
      outputs.initialDraft ??
      (workingText.rewritten && !outputs.initialDraft
        ? workingText.rewritten
        : "") ??
      modifiedOpinionText ??
      ""
    );
  };

  // file → base64
  const fileToBase64 = (file: File) =>
    new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const bytes = reader.result as ArrayBuffer;
        let binary = "";
        const bytesArr = new Uint8Array(bytes);
        const chunkSize = 0x8000;
        for (let i = 0; i < bytesArr.length; i += chunkSize) {
          binary += String.fromCharCode.apply(
            null,
            Array.from(bytesArr.subarray(i, i + chunkSize))
          );
        }
        resolve(btoa(binary));
      };
      reader.onerror = reject;
      reader.readAsArrayBuffer(file);
    });

  // Load default template from public folder
  const loadDefaultTemplate = useCallback(
    async (type: "al" | "adr" = "al") => {
      // Check if already loaded using a ref to avoid dependency issues
      if (defaultTemplateLoadedRef.current[type]) {
        // Update the active template if already loaded
        if (type === "al" && alTemplateB64) {
          setDefaultTemplateB64(alTemplateB64);
        } else if (type === "adr" && adrTemplateB64) {
          setDefaultTemplateB64(adrTemplateB64);
        }
        return;
      }

      setIsLoadingDefaultTemplate(true);
      try {
        const templatePath =
          type === "al"
            ? "/default-opinion-template.docx"
            : "/ADR Opinion Memo Template (Sept 2024).docx";

        const response = await fetch(templatePath);
        if (!response.ok) {
          console.warn(
            `Default ${type.toUpperCase()} template not found, template upload will be required`
          );
          setIsLoadingDefaultTemplate(false);
          // Don't set the ref to true so we can try again if needed
          return;
        }
        const blob = await response.blob();
        const arrayBuffer = await blob.arrayBuffer();
        const bytes = new Uint8Array(arrayBuffer);
        let binary = "";
        const chunkSize = 0x8000;
        for (let i = 0; i < bytes.length; i += chunkSize) {
          binary += String.fromCharCode.apply(
            null,
            Array.from(bytes.subarray(i, i + chunkSize))
          );
        }
        const b64 = btoa(binary);

        // Store in the appropriate state
        if (type === "al") {
          setAlTemplateB64(b64);
          setDefaultTemplateB64(b64);
        } else {
          setAdrTemplateB64(b64);
          setDefaultTemplateB64(b64);
        }

        defaultTemplateLoadedRef.current[type] = true; // Mark as loaded only on success
        console.log(
          `✅ Default ${type.toUpperCase()} template loaded successfully`
        );
      } catch (error) {
        console.warn(
          `Failed to load default ${type.toUpperCase()} template:`,
          error
        );
      } finally {
        setIsLoadingDefaultTemplate(false);
      }
    },
    [alTemplateB64, adrTemplateB64]
  );

  const onChooseTemplate = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) {
      // Clear custom template, use default
      setTemplateFile(null);
      setTemplateB64(null);
      return;
    }
    if (
      !f.name.toLowerCase().endsWith(".docx") &&
      !f.name.toLowerCase().endsWith(".dotx")
    ) {
      toast?.error("Please upload a .docx or .dotx template");
      return;
    }
    setTemplateFile(f);
    const b64 = await fileToBase64(f);
    setTemplateB64(b64);
    toast?.success(`Custom template "${f.name}" will be used`);
  };

  const clearCustomTemplate = () => {
    setTemplateFile(null);
    setTemplateB64(null);
    setUseCustomTemplate(false);
    toast?.success("Using default template");
  };

  const handleCustomTemplateToggle = (checked: boolean | "indeterminate") => {
    const isChecked = checked === true;
    setUseCustomTemplate(isChecked);
    if (!isChecked) {
      // Clear custom template when unchecking
      setTemplateFile(null);
      setTemplateB64(null);
    }
  };

  const location = useLocation();
  const navigate = useNavigate();

  const getStagingDraftText = () => {
    if (modifiedOpinionText) return modifiedOpinionText;
    const d = currentOpinionDraft?.draft;
    if (typeof d === "string") return d;
    if (d && typeof d === "object" && d.draft) return d.draft as string;
    return "";
  };

  // Step management
  const [currentStep, setCurrentStep] = useState<OpinionStep>("configuration");
  const [selectedOpinionId, setSelectedOpinionId] = useState(() => {
    const query = new URLSearchParams(location.search);
    return query.get("id");
  });

  // Form state
  const [facts, setFacts] = useState<string>("");
  const [questions, setQuestions] = useState<string>("");
  const [assumptions, setAssumptions] = useState<string>("");
  const [clientName, setClientName] = useState<string>("");
  const [clientAddress, setClientAddress] = useState<string>("");
  const [title, setTitle] = useState<string>("");
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false);

  // Draft and version state
  const [currentOpinionDraft, setCurrentOpinionDraft] = useState<any>(null);
  const [currentOpinionVersionInfo, setCurrentOpinionVersionInfo] = useState<{
    version: number;
    name: string;
    draft_id: string;
  } | null>(null);

  // UI state
  const [showAdditionalDocs, setShowAdditionalDocs] = useState(false);
  const [showPrecedentCases, setShowPrecedentCases] = useState(false);
  const [copyingTextToClipboard, setCopyingTextToClipboard] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [hasAutoSavedDraft, setHasAutoSavedDraft] = useState<boolean>(false);
  const [lastGeneratedDraftId, setLastGeneratedDraftId] = useState<
    string | null
  >(null);
  const [modifiedOpinionText, setModifiedOpinionText] = useState<string>("");
  const [hasUnsavedTextChanges, setHasUnsavedTextChanges] = useState(false);
  const mutateApplyChangesToDraft = useMutateApplyChangesToDraft();

  const compileOpinion = async () => {
    if (!selectedOpinionId) return;

    try {
      if (hasUnsavedTextChanges) {
        await saveModifiedDraftText(modifiedOpinionText);
      }

      setCompileError(null);
      setCompileUrl(null);
      setCompileFileName(null);

      // Use custom template if provided, otherwise use selected default template
      const templateToUse = templateB64 || defaultTemplateB64;
      const templateFilename =
        templateFile?.name ||
        (defaultTemplateType === "al"
          ? "default-opinion-template.docx"
          : "ADR Opinion Memo Template (Sept 2024).dotx");

      mutateCompileOpinion.mutate(
        {
          opinion_id: selectedOpinionId,
          to: compileTo,
          date: compileDate,
          re: compileRe,
          staging_draft_text: getDraftTextForCompile(),
          template_docx_b64: templateToUse || undefined,
          template_filename: templateToUse ? templateFilename : undefined,
        },
        {
          onSuccess: (res) => {
            const payload = res?.data;
            if (payload?.success) {
              setCompileUrl(payload.url);
              setCompileFileName(payload.file_name || "Compiled_Opinion.docx");
              toast?.success("Compiled DOCX ready");
              window.open(payload.url, "_blank", "noopener,noreferrer");
            } else {
              const msg = payload?.error || "Failed to compile";
              setCompileError(msg);
              toast?.error(msg);
            }
          },
          onError: (err: any) => {
            const msg =
              err?.response?.data?.error ||
              err?.message ||
              "Could not call compile endpoint";
            setCompileError(msg);
            if (toast) toast.error(msg);
          },
        }
      );
    } catch (e: any) {
      const msg = e?.message || "Could not save/compile opinion";
      setCompileError(msg);
      if (toast) toast.error(msg);
    }
  };

  useEffect(() => {
    if (currentOpinionDraft?.draft) {
      setModifiedOpinionText(currentOpinionDraft.draft);
      setHasUnsavedTextChanges(false);
    }
  }, [currentOpinionDraft?.draft]);

  // Optimized change handler — now per-pane
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const handleOpinionTextChange = useCallback(
    (newText: string, appliedChange?: any) => {
      // Store original text before first AI change
      if (!originalTextBeforeChanges && appliedChange) {
        setOriginalTextBeforeChanges(
          modifiedOpinionText || getActiveDraftText()
        );
      }

      setModifiedOpinionText(newText);
      setHasUnsavedTextChanges(true);

      // Track the applied change(s)
      if (appliedChange) {
        if (Array.isArray(appliedChange)) {
          // Multiple changes applied at once
          setAppliedAIChanges((prev) => [...prev, ...appliedChange]);
        } else {
          // Single change applied
          setAppliedAIChanges((prev) => [...prev, appliedChange]);
        }
      }

      // store into the current pane working text
      setWorkingText((prev) =>
        activeView === "rewritten"
          ? { ...prev, rewritten: newText }
          : { ...prev, initial: newText }
      );

      if (autoSaveTimeoutRef.current) clearTimeout(autoSaveTimeoutRef.current);
      autoSaveTimeoutRef.current = setTimeout(() => {
        if (selectedOpinionId && newText !== currentOpinionDraft?.draft) {
          saveModifiedDraftText(newText);
        }
      }, 2000);
    },
    [
      selectedOpinionId,
      currentOpinionDraft?.draft,
      activeView,
      originalTextBeforeChanges,
      modifiedOpinionText,
    ]
  );

  const clearDiffTracking = () => {
    setAppliedAIChanges([]);
    setOriginalTextBeforeChanges("");
    setShowDiffView(false);
  };

  const handleRegenerateRequest = () => {
    if (hasUnsavedTextChanges) {
      setShowRegenerateConfirm(true);
    } else {
      regenerateOpinion();
    }
  };

  const regenerateOpinion = () => {
    if (!selectedOpinionId) return;
    setCurrentOpinionDraft(null);
    setCurrentOpinionVersionInfo(null);
    setModifiedOpinionText("");
    setHasUnsavedTextChanges(false);
    setOutputs({});
    setWorkingText({});
    setActiveView("rewritten");
    clearDiffTracking(); // ← ADD THIS LINE
    mutateGenerateOpinion.mutate({ id: selectedOpinionId });
    setShowRegenerateConfirm(false);
  };

  const cancelRegenerate = () => setShowRegenerateConfirm(false);

  useEffect(() => {
    return () => {
      if (autoSaveTimeoutRef.current) clearTimeout(autoSaveTimeoutRef.current);
    };
  }, []);

  const saveModifiedDraftText = async (newText: string) => {
    if (!selectedOpinionId) return;
    try {
      await mutateApplyChangesToDraft.mutateAsync({
        opinion_id: selectedOpinionId,
        draft_text: newText,
        draft_id: currentOpinionVersionInfo?.draft_id || "staging",
      });
      setCurrentOpinionDraft((prev: any) => ({ ...prev, draft: newText }));
      setHasUnsavedTextChanges(false);
      console.log("✅ Draft text changes saved successfully");
    } catch (error) {
      console.error("❌ Failed to save draft text changes:", error);
    }
  };

  const saveCurrentChanges = () => {
    if (selectedOpinionId && hasUnsavedTextChanges) {
      saveModifiedDraftText(modifiedOpinionText);
    }
  };

  // Hooks
  const mutateCreateOpinion = useMutateCreateOpinion();
  const mutateGetOpinionDraft = useMutateGetOpinionDraft();
  const mutateGetPrecedents = useMutateGetPrecedents();
  const mutateSaveOpinion = useMutateSaveOpinion();
  const mutateGenerateOpinion = useMutateGenerateOpinion();
  const mutateGetLink = useMutateGetLink();
  const { data: loadedOpinion, refetch: refetchOpinion } =
    useGetOpinion(selectedOpinionId);
  const { data: globalDocs, refetch: refetchGlobalDocs } =
    useGetGlobalOpinionDocs();

  const [isLoadingDraft, setIsLoadingDraft] = useState(false);

  // Load default templates on mount
  useEffect(() => {
    loadDefaultTemplate("al");
    loadDefaultTemplate("adr");
  }, []); // Only run once on mount

  // Update active default template when type changes
  useEffect(() => {
    if (useCustomTemplate) return; // Don't change if using custom template

    if (defaultTemplateType === "al" && alTemplateB64) {
      setDefaultTemplateB64(alTemplateB64);
    } else if (defaultTemplateType === "adr" && adrTemplateB64) {
      setDefaultTemplateB64(adrTemplateB64);
    } else if (!defaultTemplateLoadedRef.current[defaultTemplateType]) {
      // If selected template not loaded yet, load it
      loadDefaultTemplate(defaultTemplateType);
    }
  }, [defaultTemplateType, alTemplateB64, adrTemplateB64, useCustomTemplate]);

  // URL param syncing
  useEffect(() => {
    if (selectedOpinionId) {
      const params = new URLSearchParams(location.search);
      params.set("id", selectedOpinionId);
      navigate(`${location.pathname}?${params.toString()}`, { replace: true });
    } else {
      const params = new URLSearchParams(location.search);
      params.delete("id");
      const newSearch = params.toString();
      navigate(`${location.pathname}${newSearch ? `?${newSearch}` : ""}`, {
        replace: true,
      });
    }
  }, [selectedOpinionId, location.pathname]);

  useEffect(() => {
    const query = new URLSearchParams(location.search);
    const id = query.get("id");

    if (id !== selectedOpinionId) {
      setCurrentOpinionDraft(null);
      setCurrentOpinionVersionInfo(null);
      setModifiedOpinionText("");
      setHasAutoSavedDraft(false);
      setLastGeneratedDraftId(null);
      setOutputs({});
      setWorkingText({});
    }

    setSelectedOpinionId(id);

    if (!id) {
      clearForm();
      setCurrentStep("configuration");
    }
  }, [location.search]);

  const debugDraftState = () => {
    console.log("🐛 DEBUG - Current Draft State:", {
      selectedOpinionId,
      hasCurrentDraft: !!currentOpinionDraft,
      hasLoadedOpinion: !!loadedOpinion,
      hasStaging: !!loadedOpinion?.staging_draft,
      stagingDraftContent: loadedOpinion?.staging_draft?.draft?.substring?.(
        0,
        100
      ),
      hasAutoSavedDraft,
      lastGeneratedDraftId: lastGeneratedDraftId?.substring?.(0, 50),
      modifiedTextLength: modifiedOpinionText?.length || 0,
      activeView,
      outputs,
      workingText,
    });
  };

  useEffect(() => {
    if (mutateGenerateOpinion.isPending) {
      setHasAutoSavedDraft(false);
      setLastGeneratedDraftId(null);
      setCurrentOpinionDraft(null);
    }
  }, [mutateGenerateOpinion.isPending]);

  // when ID changes, refetch
  useEffect(() => {
    if (selectedOpinionId) {
      setIsLoadingDraft(true);
      refetchOpinion()
        .then((result) => {
          setIsLoadingDraft(false);
        })
        .catch(() => setIsLoadingDraft(false));
    } else {
      setIsLoadingDraft(false);
    }
  }, [selectedOpinionId]);

  // populate form
  useEffect(() => {
    if (selectedOpinionId && loadedOpinion) {
      setTitle(loadedOpinion.title || "");
      setFacts(loadedOpinion.facts || "");
      setQuestions(loadedOpinion.questions || "");
      setAssumptions(loadedOpinion.assumptions || "");
      setClientName(loadedOpinion.client_name || "");
      setClientAddress(loadedOpinion.client_address || "");
      setHasUnsavedChanges(false);
    }
  }, [selectedOpinionId, loadedOpinion]);

  const mutateSaveStagingDraft = useMutateSaveStagingDraft();

  // unsaved form changes
  useEffect(() => {
    if (selectedOpinionId && loadedOpinion) {
      const hasChanges =
        title !== (loadedOpinion.title || "") ||
        facts !== (loadedOpinion.facts || "") ||
        questions !== (loadedOpinion.questions || "") ||
        assumptions !== (loadedOpinion.assumptions || "") ||
        clientName !== (loadedOpinion.client_name || "") ||
        clientAddress !== (loadedOpinion.client_address || "");
      setHasUnsavedChanges(hasChanges);
    }
  }, [
    selectedOpinionId,
    loadedOpinion,
    title,
    facts,
    questions,
    assumptions,
    clientName,
    clientAddress,
  ]);

  // create opinion success
  useEffect(() => {
    if (!mutateCreateOpinion.isSuccess) return;
    const newOpinionId = (mutateCreateOpinion.data.data as any).id;
    setSelectedOpinionId(newOpinionId);
    setHasUnsavedChanges(false);
  }, [mutateCreateOpinion.isSuccess]);

  // save opinion success
  useEffect(() => {
    if (!mutateSaveOpinion.isSuccess) return;
    refetchOpinion();
    setHasUnsavedChanges(false);
  }, [mutateSaveOpinion.isSuccess]);

  // ==== NEW: handle generate success (normalize 3 artifacts) ====
  useEffect(() => {
    if (!mutateGenerateOpinion.isSuccess || !mutateGenerateOpinion.data?.data)
      return;
    const generatedDraft = mutateGenerateOpinion.data.data;
    const draftId = JSON.stringify(generatedDraft);
    if (lastGeneratedDraftId === draftId) return;

    const normalized = normalizeGeneratedPayload(generatedDraft);
    setOutputs(normalized);

    const nextView: OpinionView = normalized.rewrittenDraft
      ? "rewritten"
      : normalized.verificationReport
      ? "verification"
      : "initial";
    setActiveView(nextView);

    setWorkingText({
      initial: normalized.initialDraft ?? "",
      rewritten: normalized.rewrittenDraft ?? normalized.initialDraft ?? "",
    });

    // keep legacy fields for downstream usage
    const baseText =
      nextView === "verification"
        ? normalized.rewrittenDraft ?? normalized.initialDraft ?? ""
        : nextView === "rewritten"
        ? normalized.rewrittenDraft ?? normalized.initialDraft ?? ""
        : normalized.initialDraft ?? "";

    setLastGeneratedDraftId(draftId);
    setCurrentOpinionVersionInfo({
      version: 0,
      name: "Working Draft",
      draft_id: "staging",
    });
    setCurrentOpinionDraft({ draft: baseText, docs: normalized.docs ?? [] });
    setModifiedOpinionText(baseText);

    // save everything to staging
    if (selectedOpinionId && generatedDraft) {
      const { sizeDisplay } = getDraftStorageInfo(generatedDraft);
      console.log(`💾 Auto-saving staging draft (${sizeDisplay})`);
      mutateSaveStagingDraft.mutate(
        { opinion_id: selectedOpinionId, draft: generatedDraft },
        {
          onError: (error) => {
            console.error("❌ Failed to auto-save staging draft:", error);
          },
          onSuccess: () => {
            setHasAutoSavedDraft(true);
            setTimeout(() => refetchOpinion(), 500);
          },
        }
      );
    }
  }, [mutateGenerateOpinion.isSuccess, selectedOpinionId]);

  // draft version fetch success
  useEffect(() => {
    if (!mutateGetOpinionDraft.isSuccess) return;
    setCurrentOpinionDraft(mutateGetOpinionDraft.data.data.draft);
    setCurrentOpinionVersionInfo({
      version: mutateGetOpinionDraft.data.data.version,
      name: mutateGetOpinionDraft.data.data.name,
      draft_id: mutateGetOpinionDraft.data.data.draft_id,
    });
  }, [mutateGetOpinionDraft.isSuccess]);

  // precedents
  useEffect(() => {
    if (!mutateGetPrecedents.isSuccess) return;
    setShowPrecedentCases(true);
  }, [mutateGetPrecedents.isSuccess]);

  // get link
  useEffect(() => {
    if (!mutateGetLink.isSuccess) return;
    window.open(mutateGetLink.data.data.url, "_blank", "noopener,noreferrer");
  }, [mutateGetLink.isSuccess]);

  // ==== UPDATED: load from staging (handles both structured and simple string drafts) ====
  useEffect(() => {
    if (!loadedOpinion) return;

    if (loadedOpinion.staging_draft) {
      const stagingDraft = loadedOpinion.staging_draft;

      if (stagingDraft.draft_error || stagingDraft.draft_not_found) {
        setCurrentOpinionDraft(null);
        setCurrentOpinionVersionInfo(null);
        setModifiedOpinionText("");
        setOutputs({});
        setWorkingText({});
        return;
      }

      if (stagingDraft.draft) {
        const d = stagingDraft.draft;

        // ✅ DETECT FORMAT: Check if it's a structured object or plain string
        const isStructuredDraft = typeof d === "object" && d !== null;
        const isSimpleString = typeof d === "string";

        if (isStructuredDraft) {
          // Handle structured draft (from generation)
          const normalized = normalizeGeneratedPayload(d);
          setOutputs(normalized);

          const nextView: OpinionView = normalized.rewrittenDraft
            ? "rewritten"
            : normalized.verificationReport
            ? "verification"
            : "initial";
          setActiveView(nextView);

          setWorkingText({
            initial: normalized.initialDraft ?? "",
            rewritten:
              normalized.rewrittenDraft ?? normalized.initialDraft ?? "",
          });

          const baseText =
            normalized.rewrittenDraft ?? normalized.initialDraft ?? "";

          setCurrentOpinionDraft({
            draft: baseText,
            docs: normalized.docs ?? [],
          });
          setCurrentOpinionVersionInfo({
            version: 0,
            name: "Working Draft",
            draft_id: "staging",
          });
          setModifiedOpinionText(baseText);
        } else if (isSimpleString) {
          // ✅ Handle simple string draft (from AI changes)
          console.log("Loading simple string draft from AI changes");

          // Clear structured outputs since we have a simple draft
          setOutputs({});

          // Set the active view to show the modified draft
          setActiveView("rewritten");

          // Set the working text for the rewritten view
          setWorkingText({
            initial: "",
            rewritten: d,
          });

          // Set current draft state
          setCurrentOpinionDraft({
            draft: d,
            docs: [],
          });
          setCurrentOpinionVersionInfo({
            version: 0,
            name: stagingDraft.applied_changes
              ? "Working Draft - AI Modified"
              : "Working Draft",
            draft_id: "staging",
          });
          setModifiedOpinionText(d);

          console.log(`✅ Loaded AI-modified draft: ${d.length} characters`);
        }

        return;
      }
    }

    // fallback: highest versioned draft
    const highestDraft =
      loadedOpinion?.drafts?.length > 0
        ? loadedOpinion.drafts.reduce((max: any, item: any) =>
            item.version > max.version ? item : max
          )
        : null;

    if (highestDraft) {
      mutateGetOpinionDraft.mutate({
        opinion_id: selectedOpinionId,
        draft_id: highestDraft.draft_id,
      });
    } else {
      setCurrentOpinionDraft(null);
      setCurrentOpinionVersionInfo(null);
      setModifiedOpinionText("");
      setOutputs({});
      setWorkingText({});
    }
  }, [loadedOpinion, selectedOpinionId]);

  // ==== NEW: compile uses active pane (verification falls back to rewritten/initial) ====
  const getDraftTextForCompile = () => {
    if (activeView === "verification") {
      return (
        workingText.rewritten ??
        outputs.rewrittenDraft ??
        workingText.initial ??
        outputs.initialDraft ??
        ""
      );
    }
    return getActiveDraftText();
  };

  const getDraftStorageInfo = (
    draft: any
  ): { size: number; sizeDisplay: string } => {
    const draftJson = JSON.stringify(draft);
    const size = new Blob([draftJson]).size;
    const sizeDisplay =
      size > 1024 ? `${Math.round(size / 1024)}KB` : `${size}B`;
    return { size, sizeDisplay };
  };

  // utils
  const clearForm = () => {
    setTitle("");
    setFacts("");
    setQuestions("");
    setAssumptions("");
    setClientName("");
    setClientAddress("");
    setCurrentOpinionDraft(null);
    setCurrentOpinionVersionInfo(null);
    setHasUnsavedChanges(false);
  };

  const startNewOpinion = () => {
    setSelectedOpinionId(null);
    clearForm();
    setCurrentStep("configuration");
  };

  const createOpinion = () => {
    mutateCreateOpinion.mutate({
      title,
      facts,
      questions,
      assumptions,
      client_name: clientName,
      client_address: clientAddress,
    });
  };

  const saveOpinion = () => {
    if (!selectedOpinionId) return;
    mutateSaveOpinion.mutate({
      id: selectedOpinionId,
      title,
      facts,
      questions,
      assumptions,
      client_name: clientName,
      client_address: clientAddress,
    });
  };

  const generateOpinion = () => {
    if (!selectedOpinionId) return;
    mutateGenerateOpinion.mutate({ id: selectedOpinionId });
  };

  const getPrecedents = () => {
    if (!selectedOpinionId) return;
    mutateGetPrecedents.mutate({ opinion_id: selectedOpinionId });
  };

  // ==== NEW: copy respects active pane ====
  const copyToClipboard = () => {
    setCopyingTextToClipboard(true);
    let textToCopy = "";
    if (activeView === "verification") {
      textToCopy = outputs.verificationReport ?? "";
    } else {
      textToCopy = getActiveDraftText();
    }
    navigator.clipboard.writeText(textToCopy);
    setTimeout(() => setCopyingTextToClipboard(false), 1000);
  };

  const getLink = (doc_id: string) => mutateGetLink.mutate({ doc_id });
  const changeVersion = (value: string) => {
    if (!loadedOpinion) return;
    mutateGetOpinionDraft.mutate({
      opinion_id: loadedOpinion.id,
      draft_id: value,
    });
  };
  const uploadedSuccessfully = () => refetchOpinion();
  const refetchDocs = () => {
    if (selectedOpinionId) refetchOpinion();
    refetchGlobalDocs();
  };

  const canNavigateToStep = (step: OpinionStep): boolean => {
    switch (step) {
      case "configuration":
        return true;
      case "drafting":
        return !!selectedOpinionId;
      case "compilation":
        return !!selectedOpinionId && !!currentOpinionDraft;
      default:
        return false;
    }
  };

  const navigateToStep = (step: OpinionStep) => {
    if (canNavigateToStep(step)) setCurrentStep(step);
  };

  const isStepCompleted = (step: OpinionStep): boolean => {
    switch (step) {
      case "configuration":
        return !!selectedOpinionId && !!title && !!facts && !!questions;
      case "drafting":
        return !!currentOpinionDraft;
      case "compilation":
        return false;
      default:
        return false;
    }
  };

  const isFormValidForCreation = () =>
    !!title.trim() && !!facts.trim() && !!questions.trim();

  const StepIndicator = ({
    step,
    label,
    isActive,
    isCompleted,
    canNavigate,
    onClick,
  }: {
    step: string;
    label: string;
    isActive: boolean;
    isCompleted: boolean;
    canNavigate: boolean;
    onClick: () => void;
  }) => (
    <div
      className={cn(
        "flex items-center cursor-pointer",
        canNavigate ? "hover:opacity-80" : "cursor-not-allowed opacity-50"
      )}
      onClick={() => canNavigate && onClick()}
    >
      <div
        className={cn(
          "flex items-center justify-center w-8 h-8 rounded-full border-2 mr-3",
          isActive
            ? "border-blue-600 bg-blue-600 text-white"
            : isCompleted
            ? "border-green-600 bg-green-600 text-white"
            : "border-gray-300 bg-white text-gray-400"
        )}
      >
        {isCompleted ? (
          <CheckCircle2 className="w-5 h-5" />
        ) : (
          <Circle className="w-5 h-5" />
        )}
      </div>
      <div
        className={cn(
          "text-sm font-medium",
          isActive
            ? "text-blue-600"
            : isCompleted
            ? "text-green-600"
            : "text-gray-400"
        )}
      >
        {label}
      </div>
    </div>
  );

  const renderStepContent = () => {
    switch (currentStep) {
      case "configuration":
        return (
          <div className="space-y-6">
            {/* Header with New Opinion button */}
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold">
                  {selectedOpinionId ? "Edit Opinion" : "Create New Opinion"}
                </h2>
                {selectedOpinionId && (
                  <p className="text-sm text-gray-600 mt-1">
                    Opinion ID: {selectedOpinionId}
                    {hasUnsavedChanges && (
                      <span className="ml-2 text-orange-600 font-medium">
                        • Unsaved changes
                      </span>
                    )}
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={startNewOpinion}
                  className="flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  New Opinion
                </Button>
                {selectedOpinionId && (
                  <Button
                    variant="outline"
                    onClick={handleDeleteRequest}
                    className="flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
                  >
                    <X className="w-4 h-4" />
                    Delete Opinion
                  </Button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-[60%_1fr] bg-muted/50 rounded-xl border">
              <div className="p-4">
                <div className="space-y-4">
                  <div>
                    <div className="text-lg font-medium mb-2">Facts</div>
                    <Textarea
                      id="facts"
                      value={facts}
                      onChange={(evt) => setFacts(evt.target.value)}
                      className="h-[150px] resize-none border-0 p-3 shadow-none focus-visible:ring-0 bg-white"
                      placeholder="Enter the relevant facts for this opinion..."
                    />
                  </div>
                  <div>
                    <div className="text-lg font-medium mb-2">Questions</div>
                    <Textarea
                      id="questions"
                      value={questions}
                      onChange={(evt) => setQuestions(evt.target.value)}
                      className="h-[150px] resize-none border-0 p-3 shadow-none focus-visible:ring-0 bg-white"
                      placeholder="What questions need to be addressed in this opinion?"
                    />
                  </div>
                  <div>
                    <div className="text-lg font-medium mb-2">Assumptions</div>
                    <Textarea
                      id="assumptions"
                      value={assumptions}
                      onChange={(evt) => setAssumptions(evt.target.value)}
                      className="h-[150px] resize-none border-0 p-3 shadow-none focus-visible:ring-0 bg-white"
                      placeholder="Any assumptions to be made for this opinion..."
                    />
                  </div>
                </div>
              </div>
              <div className="bg-muted/50 border-l-2 border-gray-200 p-4">
                <div className="space-y-4">
                  <div>
                    <Label className="text-base font-medium">
                      Opinion Title
                    </Label>
                    <Input
                      className="mt-2 bg-white"
                      value={title}
                      onChange={(evt) => setTitle(evt.target.value)}
                      placeholder="Enter opinion title..."
                    />
                  </div>
                  <div>
                    <Label className="text-base font-medium">Client Name</Label>
                    <Input
                      className="mt-2 bg-white"
                      value={clientName}
                      onChange={(evt) => setClientName(evt.target.value)}
                      placeholder="Enter client name..."
                    />
                  </div>
                  <div>
                    <Label className="text-base font-medium">
                      Client Address
                    </Label>
                    <Input
                      className="mt-2 bg-white"
                      value={clientAddress}
                      onChange={(evt) => setClientAddress(evt.target.value)}
                      placeholder="Enter client address..."
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-between items-center">
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowAdditionalDocs(true)}
                  disabled={!selectedOpinionId}
                >
                  <Paperclip className="w-4 h-4 mr-2" />
                  Attach Documents
                  {!selectedOpinionId && (
                    <span className="ml-1 text-xs">(Save first)</span>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={getPrecedents}
                  disabled={mutateGetPrecedents.isPending || !selectedOpinionId}
                >
                  {mutateGetPrecedents.isPending && (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  )}
                  Find Case Law
                  {!selectedOpinionId && (
                    <span className="ml-1 text-xs">(Save first)</span>
                  )}
                </Button>
              </div>
              <div className="flex gap-2">
                {selectedOpinionId ? (
                  <>
                    <Button
                      onClick={saveOpinion}
                      disabled={
                        mutateSaveOpinion.isPending || !hasUnsavedChanges
                      }
                      variant={hasUnsavedChanges ? "default" : "outline"}
                    >
                      {mutateSaveOpinion.isPending && (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      )}
                      <Save className="w-4 h-4 mr-2" />
                      {hasUnsavedChanges ? "Save Changes" : "Saved"}
                    </Button>
                    {canNavigateToStep("drafting") && (
                      <Button onClick={() => navigateToStep("drafting")}>
                        Continue to Drafting
                      </Button>
                    )}
                  </>
                ) : (
                  <Button
                    onClick={createOpinion}
                    disabled={
                      mutateCreateOpinion.isPending || !isFormValidForCreation()
                    }
                  >
                    {mutateCreateOpinion.isPending && (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    )}
                    Save Opinion
                    <CornerDownLeft className="w-4 h-4 ml-2" />
                  </Button>
                )}
              </div>
            </div>
          </div>
        );

      case "drafting":
        return (
          <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold">Draft Opinion</h2>
                {selectedOpinionId && (
                  <p className="text-sm text-gray-600 mt-1">
                    Opinion: {title || `ID: ${selectedOpinionId}`}
                    {isLoadingDraft && (
                      <span className="ml-2 text-blue-600">• Loading...</span>
                    )}
                    {mutateGenerateOpinion.isPending && (
                      <span className="ml-2 text-blue-600">
                        • Generating...
                      </span>
                    )}
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                {currentOpinionDraft && !isLoadingDraft && (
                  <Button
                    variant="outline"
                    onClick={handleRegenerateRequest}
                    disabled={mutateGenerateOpinion.isPending}
                    className="flex items-center gap-2"
                  >
                    {mutateGenerateOpinion.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4" />
                    )}
                    {mutateGenerateOpinion.isPending
                      ? "Regenerating..."
                      : "Regenerate Draft"}
                  </Button>
                )}
                <Button
                  variant="outline"
                  onClick={startNewOpinion}
                  className="flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  New Opinion
                </Button>
                {selectedOpinionId && (
                  <Button
                    variant="outline"
                    onClick={handleDeleteRequest}
                    className="flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
                  >
                    <X className="w-4 h-4" />
                    Delete
                  </Button>
                )}
              </div>
            </div>

            {(isLoadingDraft || mutateGenerateOpinion.isPending) && (
              <div className="text-center py-8 bg-white rounded-xl border">
                <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-600" />
                <div className="text-gray-600">
                  {mutateGenerateOpinion.isPending
                    ? "Generating new draft..."
                    : "Loading opinion data..."}
                </div>
              </div>
            )}

            {!isLoadingDraft &&
              !mutateGenerateOpinion.isPending &&
              currentOpinionDraft && (
                <div className="grid grid-cols-[1fr_350px] gap-6">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <OpinionViewToggle
                        value={activeView}
                        onChange={setActiveView}
                      />
                      <span className="text-xs text-gray-500">
                        {activeView === "verification"
                          ? "Read-only verification"
                          : activeView === "initial"
                          ? "Editing initial draft"
                          : "Editing rewritten draft"}
                      </span>
                    </div>

                    {/* Content pane */}
                    {activeView === "verification" ? (
                      <div className="bg-white rounded-xl border p-0">
                        <div className="border-b p-3 text-sm text-gray-600">
                          Verification Report
                        </div>
                        <EnhancedOpinionDisplay
                          opinionText={
                            outputs.verificationReport ??
                            "_No verification report provided._"
                          }
                          currentOpinionVersionInfo={currentOpinionVersionInfo}
                          copyToClipboard={copyToClipboard}
                          copyingTextToClipboard={copyingTextToClipboard}
                          hasUnsavedChanges={false}
                          onSaveChanges={undefined}
                        />
                      </div>
                    ) : appliedAIChanges.length > 0 ? (
                      <DiffViewer
                        originalText={
                          originalTextBeforeChanges || getActiveDraftText()
                        }
                        currentText={getActiveDraftText()}
                        appliedChanges={appliedAIChanges}
                        showDiff={showDiffView}
                        onToggleDiff={() => setShowDiffView(!showDiffView)}
                      />
                    ) : (
                      <EnhancedOpinionDisplay
                        opinionText={getActiveDraftText()}
                        currentOpinionVersionInfo={currentOpinionVersionInfo}
                        copyToClipboard={copyToClipboard}
                        copyingTextToClipboard={copyingTextToClipboard}
                        hasUnsavedChanges={hasUnsavedTextChanges}
                        onSaveChanges={saveCurrentChanges}
                      />
                    )}
                  </div>

                  <div className="space-y-4">
                    <div className="bg-white rounded-xl border p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-lg font-semibold">Draft Actions</h3>
                      </div>
                      <Button
                        variant="outline"
                        onClick={handleRegenerateRequest}
                        disabled={mutateGenerateOpinion.isPending}
                        className="w-full flex items-center gap-2"
                      >
                        {mutateGenerateOpinion.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <RefreshCw className="w-4 h-4" />
                        )}
                        {mutateGenerateOpinion.isPending
                          ? "Regenerating..."
                          : "Regenerate Draft"}
                      </Button>
                      {hasUnsavedTextChanges && (
                        <p className="text-xs text-orange-600 mt-2">
                          ⚠️ You have unsaved changes that will be lost
                        </p>
                      )}
                    </div>

                    {loadedOpinion?.drafts &&
                      loadedOpinion.drafts.length > 0 && (
                        <div className="bg-white rounded-xl border p-4">
                          <h3 className="text-lg font-semibold mb-3">
                            Version
                          </h3>
                          <Select
                            value={currentOpinionVersionInfo?.draft_id}
                            onValueChange={changeVersion}
                          >
                            <SelectTrigger className="bg-white">
                              <SelectValue placeholder="Select version" />
                            </SelectTrigger>
                            <SelectContent className="bg-white">
                              <SelectGroup>
                                {loadedOpinion.drafts.map((draft: any) => (
                                  <SelectItem
                                    key={draft.draft_id}
                                    value={draft.draft_id}
                                  >
                                    {draft.name} (v{draft.version})
                                  </SelectItem>
                                ))}
                              </SelectGroup>
                            </SelectContent>
                          </Select>
                        </div>
                      )}

                    {activeView !== "verification" ? (
                      <AlchemioChat
                        opinionText={getActiveDraftText()}
                        opinionVersionInfo={currentOpinionVersionInfo}
                        selectedOpinionId={selectedOpinionId!}
                        onOpinionChange={handleOpinionTextChange}
                      />
                    ) : (
                      <div className="bg-white rounded-xl border p-4 text-sm text-gray-600">
                        Verification report is read-only. Switch to a draft to
                        apply AI changes.
                      </div>
                    )}
                  </div>
                </div>
              )}

            {!isLoadingDraft &&
              !mutateGenerateOpinion.isPending &&
              !currentOpinionDraft && (
                <div className="text-center py-12 bg-white rounded-xl border">
                  <div className="text-gray-500 mb-4">
                    No draft generated yet
                  </div>
                  <Button
                    onClick={generateOpinion}
                    disabled={mutateGenerateOpinion.isPending}
                    size="lg"
                  >
                    {mutateGenerateOpinion.isPending && (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    )}
                    Generate Draft
                  </Button>
                </div>
              )}

            <div className="flex justify-between items-center">
              <Button
                variant="outline"
                onClick={() => navigateToStep("configuration")}
              >
                Back to Configuration
              </Button>
              <div className="flex gap-2">
                {canNavigateToStep("compilation") && (
                  <Button onClick={() => navigateToStep("compilation")}>
                    Continue to Compilation
                  </Button>
                )}
              </div>
            </div>
          </div>
        );

      case "compilation":
        return (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold">Compile Opinion</h2>
                {selectedOpinionId && (
                  <p className="text-sm text-gray-600 mt-1">
                    Opinion: {title || `ID: ${selectedOpinionId}`}
                  </p>
                )}
              </div>
              <Button
                variant="outline"
                onClick={startNewOpinion}
                className="flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                New Opinion
              </Button>
            </div>

            <div className="grid grid-cols-[1fr_350px] gap-6">
              <div className="bg-white rounded-xl border p-4">
                <div className="grid md:grid-cols-3 gap-4">
                  <div>
                    <Label className="text-sm">To</Label>
                    <Input
                      className="mt-1 bg-white"
                      value={compileTo}
                      onChange={(e) => setCompileTo(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-sm">Date</Label>
                    <Input
                      type="date"
                      className="mt-1 bg-white"
                      value={compileDate}
                      onChange={(e) => setCompileDate(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-sm">Re</Label>
                    <Input
                      className="mt-1 bg-white"
                      value={compileRe}
                      onChange={(e) => setCompileRe(e.target.value)}
                    />
                  </div>
                </div>

                <div className="mt-4">
                  <div className="flex items-center justify-between mb-3">
                    <Label className="text-sm font-medium">DOCX Template</Label>
                    {isLoadingDefaultTemplate && (
                      <div className="text-xs text-gray-500 flex items-center gap-1">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        Loading template...
                      </div>
                    )}
                    {!isLoadingDefaultTemplate &&
                      defaultTemplateB64 &&
                      !useCustomTemplate && (
                        <span className="text-xs text-gray-500">
                          Default template available
                        </span>
                      )}
                  </div>

                  {/* Default template selection - shown when not using custom template */}
                  {!useCustomTemplate && (
                    <div className="mb-4">
                      <Label className="text-sm font-medium mb-2 block">
                        Select Default Template
                      </Label>
                      <RadioGroup
                        value={defaultTemplateType}
                        onValueChange={(value) =>
                          setDefaultTemplateType(value as "al" | "adr")
                        }
                        className="space-y-2"
                      >
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="al" id="template-al" />
                          <label
                            htmlFor="template-al"
                            className="text-sm font-medium leading-none cursor-pointer"
                          >
                            AL Memo Template
                          </label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="adr" id="template-adr" />
                          <label
                            htmlFor="template-adr"
                            className="text-sm font-medium leading-none cursor-pointer"
                          >
                            ADR Memo Template
                          </label>
                        </div>
                      </RadioGroup>
                    </div>
                  )}

                  {/* Checkbox to use custom template */}
                  <div className="flex items-center space-x-2 mb-3">
                    <Checkbox
                      id="use-custom-template"
                      checked={useCustomTemplate}
                      onCheckedChange={handleCustomTemplateToggle}
                    />
                    <label
                      htmlFor="use-custom-template"
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                    >
                      Use custom template
                    </label>
                  </div>

                  {/* File upload input - shown only when checkbox is checked */}
                  {useCustomTemplate && (
                    <div className="flex items-center gap-2 mb-2">
                      <Input
                        type="file"
                        accept=".docx,.dotx"
                        className="bg-white flex-1"
                        onChange={onChooseTemplate}
                      />
                      {templateFile && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={clearCustomTemplate}
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  )}

                  {/* Status messages */}
                  {templateFile ? (
                    <div className="text-xs text-gray-600 mt-1">
                      ✓ Using custom template:{" "}
                      <strong>{templateFile.name}</strong> (
                      {Math.round(templateFile.size / 1024)} KB)
                    </div>
                  ) : defaultTemplateB64 ? (
                    <div className="text-xs text-gray-600 mt-1">
                      ✓ Using default template:{" "}
                      <strong>
                        {defaultTemplateType === "al"
                          ? "AL Memo Template"
                          : "ADR Memo Template"}
                      </strong>
                      {!useCustomTemplate &&
                        " (check above to upload a custom template)"}
                    </div>
                  ) : (
                    <div className="text-xs text-orange-600 mt-1">
                      ⚠️ No default template found. Please check the box above
                      and upload a template.
                    </div>
                  )}
                </div>

                <div className="mt-6 flex items-center gap-3">
                  <Button
                    onClick={compileOpinion}
                    disabled={
                      !selectedOpinionId ||
                      !currentOpinionDraft ||
                      mutateCompileOpinion.isPending
                    }
                    className="flex items-center gap-2"
                  >
                    {mutateCompileOpinion.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    {mutateCompileOpinion.isPending ? "Sending…" : "Compile"}
                  </Button>

                  {hasUnsavedTextChanges && (
                    <span className="text-xs text-orange-600">
                      Unsaved edits will be saved first.
                    </span>
                  )}
                </div>

                <div className="text-xs text-gray-500 mt-2">
                  Compiling the{" "}
                  <span className="font-medium">
                    {activeView === "verification"
                      ? "rewritten (fallback)"
                      : activeView}
                  </span>{" "}
                  content.
                </div>

                <div className="mt-6">
                  {compileError && (
                    <div className="text-sm text-red-600">
                      ❌ {compileError}
                    </div>
                  )}
                  {compileUrl && (
                    <div className="p-3 bg-green-50 border border-green-200 rounded text-sm">
                      ✅ Compiled:&nbsp;
                      <a
                        href={compileUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline text-green-700"
                      >
                        {compileFileName || "Download DOCX"}
                      </a>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <div className="bg-white rounded-xl border p-4">
                  <h3 className="text-lg font-semibold mb-3">
                    Compilation Steps…
                  </h3>
                  <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1">
                    <li>Fill in the “To / Date / Re” fields</li>
                    <li>Upload your opinion template</li>
                    <li>Compile!</li>
                  </ul>
                </div>
                <Button
                  variant="outline"
                  onClick={() => navigateToStep("drafting")}
                >
                  Back to Drafting
                </Button>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        {/* Dialogs */}
        <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Delete Opinion?</DialogTitle>
              <DialogDescription>
                This action cannot be undone. This will permanently delete the
                opinion "{title || `ID: ${selectedOpinionId}`}" and all
                associated drafts.
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <div className="text-sm text-gray-600">
                <div className="mb-2">
                  The following will be permanently deleted:
                </div>
                <div className="bg-red-50 border border-red-200 rounded p-3">
                  <div className="text-red-800 text-xs space-y-1">
                    <div>• Opinion configuration and metadata</div>
                    <div>
                      • All draft versions (initial, rewritten, staging)
                    </div>
                    <div>• Associated documents and references</div>
                    <div>• Generated content and verification reports</div>
                  </div>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={cancelDelete}>
                Cancel
              </Button>
              <Button
                onClick={confirmDelete}
                disabled={mutateDeleteOpinion.isPending}
                className="bg-red-600 hover:bg-red-700"
              >
                {mutateDeleteOpinion.isPending && (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                )}
                Delete Opinion
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        <Dialog
          open={showRegenerateConfirm}
          onOpenChange={setShowRegenerateConfirm}
        ></Dialog>
        <Dialog
          open={showRegenerateConfirm}
          onOpenChange={setShowRegenerateConfirm}
        >
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Regenerate Draft?</DialogTitle>
              <DialogDescription>
                You have unsaved changes to your current draft. Regenerating
                will create a completely new draft and your current changes will
                be lost.
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <div className="text-sm text-gray-600">
                <div className="mb-2">Current changes that will be lost:</div>
                <div className="bg-orange-50 border border-orange-200 rounded p-3">
                  <div className="text-orange-800 text-xs">
                    • Unsaved text modifications • Any manual edits you've made
                  </div>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={cancelRegenerate}>
                Cancel
              </Button>
              <Button
                onClick={regenerateOpinion}
                disabled={mutateGenerateOpinion.isPending}
                className="bg-orange-600 hover:bg-orange-700"
              >
                {mutateGenerateOpinion.isPending && (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                )}
                Yes, Regenerate
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={showPrecedentCases} onOpenChange={setShowPrecedentCases}>
          <DialogContent className="max-w-[800px]">
            <DialogHeader>
              <DialogTitle>SAFLII case law</DialogTitle>
              <DialogDescription>
                Verified results from saflii.org for this matter
              </DialogDescription>
            </DialogHeader>
            <div>
              <PrecedentsListing
                precedentData={mutateGetPrecedents.data?.data}
              />
            </div>
            <DialogFooter>
              <Button onClick={() => setShowPrecedentCases(false)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={showAdditionalDocs} onOpenChange={setShowAdditionalDocs}>
          <DialogContent className="max-w-[1200px]">
            <DialogHeader>
              <DialogTitle>Document Management</DialogTitle>
              <DialogDescription>
                <div>
                  <Uploader
                    data={{
                      opinion_id: selectedOpinionId,
                      type: "save_for_opinion",
                    }}
                    onUploadedSuccessfully={uploadedSuccessfully}
                  />
                  <div className="flex gap-4 pt-4">
                    <div className="w-1/2 overflow-y-auto max-h-[600px]">
                      <DocLister
                        opinionId={selectedOpinionId}
                        docs={loadedOpinion?.documents}
                        refresh={refetchDocs}
                        title="Your documents for this opinion"
                        isGlobal={false}
                      />
                    </div>
                    <div className="w-1/2 overflow-y-auto max-h-[600px]">
                      <DocLister
                        opinionId={selectedOpinionId}
                        docs={loadedOpinion?.documents}
                        globalDocs={globalDocs?.global_documents}
                        title="Available Alchemy Opinion documents"
                        isGlobal={true}
                        refresh={refetchDocs}
                      />
                    </div>
                  </div>
                </div>
              </DialogDescription>
            </DialogHeader>
          </DialogContent>
        </Dialog>

        <div className="flex flex-col h-screen">
          <Top />
          <main className="flex-1 p-6">
            {/* Stepper Header */}
            <div className="mb-8">
              <div className="flex items-center justify-center space-x-8 p-6 bg-white rounded-xl border">
                <StepIndicator
                  step="configuration"
                  label="Configuration"
                  isActive={currentStep === "configuration"}
                  isCompleted={isStepCompleted("configuration")}
                  canNavigate={canNavigateToStep("configuration")}
                  onClick={() => navigateToStep("configuration")}
                />
                <div className="w-12 h-px bg-gray-300" />
                <StepIndicator
                  step="drafting"
                  label="Drafting"
                  isActive={currentStep === "drafting"}
                  isCompleted={isStepCompleted("drafting")}
                  canNavigate={canNavigateToStep("drafting")}
                  onClick={() => navigateToStep("drafting")}
                />
                <div className="w-12 h-px bg-gray-300" />
                <StepIndicator
                  step="compilation"
                  label="Compilation"
                  isActive={currentStep === "compilation"}
                  isCompleted={isStepCompleted("compilation")}
                  canNavigate={canNavigateToStep("compilation")}
                  onClick={() => navigateToStep("compilation")}
                />
              </div>
            </div>
            {/* Step Content */}
            <div className="max-w-full">{renderStepContent()}</div>
          </main>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
