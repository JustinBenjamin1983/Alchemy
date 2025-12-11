import { useMsal } from "@azure/msal-react";
import { InteractionRequiredAuthError } from "@azure/msal-browser";
import { loginRequest, DEV_MODE } from "@/authConfig";

// Dev mode token - used when DEV_MODE is true
const DEV_TOKEN = "dev-mode-token-for-local-testing";

export function useAuthToken() {
  const { instance, accounts } = useMsal();

  async function getAccessToken() {
    // In dev mode, return a mock token
    if (DEV_MODE) {
      console.log("🔧 Dev mode: Using mock auth token");
      return DEV_TOKEN;
    }

    const request = {
      account: accounts[0],
      scopes: loginRequest.scopes,
    };

    try {
      const response = await instance.acquireTokenSilent(request);
      //   console.log(response.accessToken);
      return response.accessToken;
    } catch (error) {
      if (error instanceof InteractionRequiredAuthError) {
        // Token expired or refresh failed silently — fallback to popup
        try {
          const response = await instance.acquireTokenPopup(request);
          return response.accessToken;
        } catch (popupError) {
          console.error("Popup failed", popupError);
          throw popupError;
        }
      } else {
        console.error("Token acquisition failed", error);
        throw error;
      }
    }
  }

  return { getAccessToken };
}
