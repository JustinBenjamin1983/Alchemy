import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

interface ChatMutationData {
  question: string;
  dd_id: string;
  document_id?: string; // Legacy support - single document
  folder_id?: string; // Legacy support - single folder
  document_ids?: string[]; // New - multiple documents
  folder_ids?: string[]; // New - multiple folders
}

interface ChatRequestData {
  question: string;
  dd_id: string;
  document_ids?: string[];
  folder_ids?: string[];
}

export function useMutateChat() {
  const axios = useAxiosWithAuth();

  async function _mutateChat(data: ChatMutationData) {
    // Transform the data to ensure backward compatibility and support for arrays
    const requestData: ChatRequestData = {
      question: data.question,
      dd_id: data.dd_id,
      document_ids: [],
      folder_ids: [],
    };

    // Handle legacy single references
    if (data.document_id) {
      requestData.document_ids = [data.document_id];
    }
    if (data.folder_id) {
      requestData.folder_ids = [data.folder_id];
    }

    // Handle new array references
    if (data.document_ids && data.document_ids.length > 0) {
      requestData.document_ids = data.document_ids;
    }
    if (data.folder_ids && data.folder_ids.length > 0) {
      requestData.folder_ids = data.folder_ids;
    }

    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-chat",
      method: "PUT",
      data: requestData,
    };

    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateChat,
  });
}
