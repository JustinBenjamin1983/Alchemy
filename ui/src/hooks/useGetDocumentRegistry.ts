import { useQuery } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export interface DocumentRegistryDocument {
  name: string;
  category: string;
  folder: string;
  priority: "critical" | "required" | "recommended" | "optional";
  description: string;
  classification_patterns?: string[];
  content_keywords?: string[];
  request_template?: string;
}

export interface DocumentRegistryCategory {
  name: string;
  description: string;
  folder: string;
}

export interface FolderStructure {
  name: string;
  subfolders?: FolderStructure[];
}

export interface DocumentRegistry {
  transaction_type: string;
  folder_structure: FolderStructure[];
  categories: DocumentRegistryCategory[];
  documents: DocumentRegistryDocument[];
  priority_counts: {
    critical: number;
    required: number;
    recommended: number;
    optional: number;
  };
}

export function useGetDocumentRegistry(transactionType: string | null) {
  const axios = useAxiosWithAuth();

  return useQuery({
    queryKey: ["document-registry", transactionType],
    queryFn: async () => {
      if (!transactionType) return null;

      const response = await axios.get("/dd-document-registry", {
        params: {
          action: "get_registry",
          transaction_type: transactionType,
        },
      });

      return response.data.data as DocumentRegistry;
    },
    enabled: !!transactionType,
  });
}
