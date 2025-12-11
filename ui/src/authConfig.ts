// Dev mode bypass - set to true to skip Azure AD auth when running locally
export const DEV_MODE = window.location.hostname === "localhost";

export const msalConfig = {
  auth: {
    clientId: "8d2ee583-07a6-47fc-b8c3-f0faefb83ac4",
    authority:
      "https://alchemyapps.b2clogin.com/alchemyapps.onmicrosoft.com/B2C_1_Alchemy_TheAIShop_SignInUpWithAD",

    knownAuthorities: ["alchemyapps.b2clogin.com"],

    // Production:
    redirectUri: DEV_MODE
      ? "http://localhost:5176"
      : "https://alchemyaitools-a2gwbmgthefwg9bm.z01.azurefd.net",
  },
  cache: {
    cacheLocation: "localStorage",
    storeAuthStateInCookie: false,
  },
};

// Mock user for dev mode
export const DEV_USER = {
  name: "Dev User",
  email: "dev@alchemy.local",
};

export const loginRequest = {
  scopes: [
    "openid",
    "profile",
    "email",
    "https://alchemyapps.onmicrosoft.com/73a5e1db-cf1d-4e21-b497-68c8979b4cce/access",
  ],
};
