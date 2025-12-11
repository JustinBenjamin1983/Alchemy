// hooks/useAlchemioChat.ts - INTELLIGENT VERSION
import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export type AlchemioChatRequest = {
  opinion_id: string;
  message: string;
  opinion_text: string;
  chat_history?: Array<{
    role: "user" | "assistant";
    content: string;
    timestamp?: string;
  }>;
  request_changes?: boolean;
};

export type AlchemioChatResponse = {
  changes: any;
  response: string;
  timestamp: string;
  status: string;
};

export const useAlchemioChat = () => {
  const axios = useAxiosWithAuth();

  const sendChatMessage = async (chatRequest: AlchemioChatRequest) => {
    // ALWAYS request change analysis - let the LLM decide on the backend
    // This removes the rigid keyword matching and makes it much more intelligent
    const enhancedRequest = {
      ...chatRequest,
      request_changes: true, // Always true - LLM will decide if changes are actually needed
    };

    const axiosOptions = {
      url: `https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/alchemiochat`,
      method: "POST",
      data: enhancedRequest,
    };
    const { data } = await axios(axiosOptions);
    return data;
  };

  return useMutation<AlchemioChatResponse, Error, AlchemioChatRequest>({
    mutationFn: sendChatMessage,
    onError: (error) => {
      console.error("AlchemioChat error:", error);
    },
  });
};

// Removed the shouldRequestChanges function entirely since we always let the LLM decide
