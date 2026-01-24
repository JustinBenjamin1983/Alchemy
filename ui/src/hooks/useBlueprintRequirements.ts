// hooks/useBlueprintRequirements.ts
/**
 * Hook to fetch blueprint document requirements for a transaction type.
 * Used by Checkpoint A to show expected documents per category.
 */
import { useQuery } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export interface DocumentMatch {
  id: string;
  filename: string;
  document_type: string | null;
  confidence: number | null;
  classification_status: string;
  matched_type: string | null;
}

export interface CategoryRequirements {
  folder_name: string;
  relevance: "critical" | "high" | "medium" | "low" | "n/a";
  subcategories: string[];
  expected_documents: string[];
  found_documents: DocumentMatch[];
  missing_documents: string[];
  document_count: number;
  is_complete: boolean;
  requires_action?: boolean;
}

export interface BlueprintRequirements {
  transaction_type: string;
  transaction_name: string;
  description: string;
  jurisdiction: string;
  requirements: Record<string, CategoryRequirements>;
  summary: {
    total_expected: number;
    total_found: number;
    total_missing: number;
    needs_review_count: number;
    categories_complete: number;
    total_categories: number;
  };
}

/**
 * Fetch blueprint document requirements for a transaction type.
 *
 * @param transactionType - The blueprint code (e.g., "mining_resources", "ma_corporate")
 * @param ddId - Optional DD project ID to include found/missing document matching
 * @param enabled - Whether the query should run
 */
export function useBlueprintRequirements(
  transactionType: string | undefined,
  ddId?: string | null,
  enabled: boolean = true
) {
  const axios = useAxiosWithAuth();

  const fetchRequirements = async (): Promise<BlueprintRequirements> => {
    let url = `/dd-get-blueprint-requirements?transaction_type=${transactionType}`;
    if (ddId) {
      url += `&dd_id=${ddId}`;
    }

    const { data } = await axios.get(url);
    return data;
  };

  return useQuery({
    queryKey: ["blueprint-requirements", transactionType, ddId],
    queryFn: fetchRequirements,
    enabled: !!transactionType && enabled,
    staleTime: ddId ? 30000 : Infinity, // Cache longer if no DD context
  });
}

/**
 * Get the standard folder categories in display order.
 */
export const FOLDER_CATEGORIES = [
  { code: "01_Corporate", name: "Corporate & Governance" },
  { code: "02_Commercial", name: "Commercial Contracts" },
  { code: "03_Financial", name: "Financial Documents" },
  { code: "04_Regulatory", name: "Regulatory & Compliance" },
  { code: "05_Employment", name: "Employment & Labour" },
  { code: "06_Property", name: "Property & Real Estate" },
  { code: "07_Insurance", name: "Insurance" },
  { code: "08_Litigation", name: "Litigation & Disputes" },
  { code: "09_Tax", name: "Tax" },
  { code: "99_Needs_Review", name: "Needs Review" },
] as const;

/**
 * Get relevance color for a category.
 */
export function getRelevanceColor(relevance: string): string {
  switch (relevance) {
    case "critical":
      return "text-red-700 bg-red-50 border-red-200";
    case "high":
      return "text-orange-700 bg-orange-50 border-orange-200";
    case "medium":
      return "text-blue-700 bg-blue-50 border-blue-200";
    case "low":
      return "text-gray-600 bg-gray-50 border-gray-200";
    default:
      return "text-gray-500 bg-gray-50 border-gray-200";
  }
}

/**
 * Get relevance badge text.
 */
export function getRelevanceBadge(relevance: string): string {
  switch (relevance) {
    case "critical":
      return "Critical";
    case "high":
      return "High";
    case "medium":
      return "Medium";
    case "low":
      return "Low";
    default:
      return "";
  }
}
