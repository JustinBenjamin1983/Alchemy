// File: ui/src/App.tsx

import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Toaster } from "./components/ui/toaster.tsx";
import { ThemeProvider } from "./components/theme-provider.tsx";
import { Login } from "./pages/Login.tsx";
import { ActivityChooser } from "./pages/ActivityChooser.tsx";
import { OpinionMain } from "./pages/OpinionWriter/OpinionMain.tsx";
import { QueryClientProvider } from "@tanstack/react-query";
import { aishopQueryClient } from "./hooks/reactQuerySetup.ts";
import { useEffect } from "react";
import { useMsal } from "@azure/msal-react";
import { loginRequest, DEV_MODE, DEV_USER } from "./authConfig.ts";
import { useMutateUser } from "./hooks/useMutateUser.tsx";
import { DDMainEnhanced } from "./pages/DD/DDMainEnhanced.tsx";
import { AgreementMain } from "./pages/Agreement/AgreementMain.tsx";
import { DocumentViewerTest } from "./pages/DD/FindingsExplorer/DocumentViewerTest.tsx";
import { DDEvaluationMain } from "./pages/DDEvaluation/DDEvaluationMain.tsx";

const AuthRedirectHandler = () => {
  const { instance } = useMsal();
  const changeUser = useMutateUser();

  useEffect(() => {
    // In dev mode, set mock user immediately and skip MSAL
    if (DEV_MODE) {
      console.log("🔧 Dev mode: Bypassing Azure AD authentication");
      changeUser.mutate({ name: DEV_USER.name, email: DEV_USER.email });
      return;
    }

    instance.handleRedirectPromise().then(async (response) => {
      if (response) {
        const tokenResponse = await instance.acquireTokenSilent({
          account: response.account,
          scopes: loginRequest.scopes,
        });
      }
      const account = instance.getAllAccounts()[0];

      if (account) {
        try {
          const tokenResponse = await instance.acquireTokenSilent({
            account,
            scopes: loginRequest.scopes,
          });
          changeUser.mutate({ name: account.name, email: account.username });
        } catch (err) {
          console.error("Silent token error", err);
          changeUser.mutate({ name: null, email: null, likelyLoggedOut: true });
        }
      } else {
        changeUser.mutate({ name: null, email: null, likelyLoggedOut: true });
      }
    });
  }, []);

  useEffect(() => {
    // Skip in dev mode
    if (DEV_MODE) return;

    const bootstrap = async () => {
      const response = await instance.handleRedirectPromise();

      const account =
        response?.account || instance.getAllAccounts()?.[0] || null;

      if (account) {
        const tokenResponse = await instance.acquireTokenSilent({
          account,
          scopes: loginRequest.scopes,
        });
      } else {
        console.warn("⚠️ No account found — user not signed in yet.");
      }
    };

    bootstrap();
  }, []);

  return null;
};
function App() {
  const router = createBrowserRouter([
    {
      path: "/",
      element: <Login />,
    },
    {
      path: "/login",
      element: <Login />,
    },
    {
      path: "/activity",
      element: <ActivityChooser />,
    },
    {
      path: "/opinion",
      element: <OpinionMain />,
    },
    {
      path: "/dd",
      element: <DDMainEnhanced />,
    },
    {
      path: "/agreement",
      element: <AgreementMain />,
    },
    {
      path: "/dd-viewer-test",
      element: <DocumentViewerTest />,
    },
    {
      path: "/dd-evaluation",
      element: <DDEvaluationMain />,
    },
    {
      path: "*",
      element: <ActivityChooser />,
    },
  ]);

  return (
    <>
      <QueryClientProvider client={aishopQueryClient}>
        <AuthRedirectHandler />
        <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
          <div className="font-alchemy">
            <Toaster />
            <RouterProvider router={router} />
          </div>
        </ThemeProvider>
      </QueryClientProvider>
    </>
  );
}

export default App;
