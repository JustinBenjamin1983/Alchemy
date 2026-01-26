import { useAuthToken } from "./useAuthToken";
import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import { DEV_MODE } from "@/authConfig";

// Production API base URL
const PROD_API_BASE = "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker";
// Dev mode uses local Azure Functions (via Vite proxy)
const DEV_API_BASE = "/api";

export function useAxiosWithAuth() {
  const { getAccessToken } = useAuthToken();

  // Enhanced call function that also supports axios instance methods
  const call = async (options: any) => {
    const token = await getAccessToken();

    const client = axios.create({
      baseURL: DEV_MODE ? DEV_API_BASE : PROD_API_BASE,
    });
    client.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    client.defaults.headers.common["Ocp-Apim-Subscription-Key"] =
      "1d1cb334ca62490e936f77eb1da89bdd";
    // Function key required for Azure Functions in dev mode
    if (DEV_MODE) {
      client.defaults.headers.common["function-key"] = "local-dev-key";
    }
    return client(options);
  };

  // Helper to create configured axios client
  const createClient = async () => {
    const token = await getAccessToken();
    const client = axios.create({
      baseURL: DEV_MODE ? DEV_API_BASE : PROD_API_BASE,
    });
    client.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    client.defaults.headers.common["Ocp-Apim-Subscription-Key"] =
      "1d1cb334ca62490e936f77eb1da89bdd";
    if (DEV_MODE) {
      client.defaults.headers.common["function-key"] = "local-dev-key";
    }
    return client;
  };

  // Add convenience methods for axios-like API
  call.get = async (url: string, config?: AxiosRequestConfig) => {
    const client = await createClient();
    return client.get(url, config);
  };

  call.post = async (url: string, data?: any, config?: AxiosRequestConfig) => {
    const client = await createClient();
    return client.post(url, data, config);
  };

  call.put = async (url: string, data?: any, config?: AxiosRequestConfig) => {
    const client = await createClient();
    return client.put(url, data, config);
  };

  call.delete = async (url: string, config?: AxiosRequestConfig) => {
    const client = await createClient();
    return client.delete(url, config);
  };

  call.patch = async (url: string, data?: any, config?: AxiosRequestConfig) => {
    const client = await createClient();
    return client.patch(url, data, config);
  };

  return call;
}
