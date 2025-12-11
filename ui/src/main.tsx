import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { PublicClientApplication, EventType } from "@azure/msal-browser";
import { MsalProvider, useMsal } from "@azure/msal-react";
import { msalConfig } from "./authConfig";

const initializeApp = async () => {
  const msalInstance = new PublicClientApplication(msalConfig);
  await msalInstance.initialize();

  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <MsalProvider instance={msalInstance}>
        <App />
      </MsalProvider>
    </StrictMode>
  );
};

initializeApp();

// createRoot(document.getElementById("root")!).render(
//   <StrictMode>
//     <MsalProvider instance={msalInstance}>
//       <AuthRedirectHandler />
//       <App />
//     </MsalProvider>
//   </StrictMode>
// );
