// File: ui/src/hooks/useWizardDraft.ts
// Hooks for saving and loading DD wizard drafts

import { useMutation, useQuery } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export interface WizardDraftData {
  id?: string;
  currentStep: number;
  transactionType: string | null;
  transactionName: string;
  clientName: string;
  targetEntityName: string;
  clientRole: string | null;
  dealStructure: string | null;
  estimatedValue: number | null;
  targetClosingDate: string | null;
  dealRationale: string;
  knownConcerns: string[];
  criticalPriorities: string[];
  knownDealBreakers: string[];
  deprioritizedAreas: string[];
  targetCompanyName: string;
  keyIndividuals: string[];
  keySuppliers: string[];
  keyCustomers: any[];  // CounterpartyStakeholder[]
  keyLenders: any[];    // LenderStakeholder[]
  keyRegulators: string[];
  keyOther: any[];      // OtherStakeholder[]
  shareholderEntityName: string;
  shareholders: any[];  // Shareholder[]
  createdAt?: string;
  updatedAt?: string;
}

// Hook to fetch all drafts for the current user
export function useGetWizardDrafts() {
  const axios = useAxiosWithAuth();

  return useQuery({
    queryKey: ["wizard-drafts"],
    queryFn: async () => {
      const response = await axios.get("/dd-wizard-draft");
      return response.data.drafts as WizardDraftData[];
    },
    // Always refetch on mount and window focus to keep drafts up-to-date
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
    staleTime: 0,
  });
}

// Hook to fetch a specific draft by ID
export function useGetWizardDraft(draftId: string | null) {
  const axios = useAxiosWithAuth();

  return useQuery({
    queryKey: ["wizard-draft", draftId],
    queryFn: async () => {
      if (!draftId) return null;
      const response = await axios.get(`/dd-wizard-draft?draft_id=${draftId}`);
      return response.data as WizardDraftData;
    },
    enabled: !!draftId,
  });
}

// Hook to create a new draft
export function useCreateWizardDraft() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async (data: Partial<WizardDraftData>) => {
      const response = await axios.post("/dd-wizard-draft", data);
      return response.data as WizardDraftData;
    },
    onSuccess: () => {
      aishopQueryClient.invalidateQueries({ queryKey: ["wizard-drafts"] });
    },
  });
}

// Hook to update an existing draft
export function useUpdateWizardDraft() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async ({
      draftId,
      data,
    }: {
      draftId: string;
      data: Partial<WizardDraftData>;
    }) => {
      const response = await axios.put("/dd-wizard-draft", {
        draftId,
        ...data,
      });
      return response.data as WizardDraftData;
    },
    onSuccess: (_, variables) => {
      aishopQueryClient.invalidateQueries({ queryKey: ["wizard-drafts"] });
      aishopQueryClient.invalidateQueries({
        queryKey: ["wizard-draft", variables.draftId],
      });
    },
  });
}

// Hook to delete a draft
export function useDeleteWizardDraft() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async (draftId: string) => {
      const response = await axios.delete(
        `/dd-wizard-draft?draft_id=${draftId}`
      );
      return response.data;
    },
    onSuccess: () => {
      aishopQueryClient.invalidateQueries({ queryKey: ["wizard-drafts"] });
    },
  });
}
