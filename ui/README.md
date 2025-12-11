# deploy

alchemysitehosting | Static website
Storage account
$web container

alchemyaisite
Front Door and CDN profile

endpoint: alchemyaitools-a2gwbmgthefwg9bm.z01.azurefd.net

remember to purge cache for alchemyaisite (Front Door and CDN profile)

## when changing deployment URLs

- change client side authConfig.ts redirectUri
- add new CORS origin to each endpoint on API M

- in Alchemy Law Africa Directory
  -- B2 federation, manage>authentication
  -- add SPA redirect uri otherwise redirect_uri_mismatch

% not this below
% - swop to Alchemy-AIShop-Apps Azure Directory
% - - go to App registrations
% - - select Alchemy-TheAIShop-App-ForUserflows
% - - select Authentication
% - - add redirect uri under "Single-page application"

% # deploy OLD

% https://www.youtube.com/watch?v=F11Ndl9Ok8A
% swa init
% swa start
% swa build  
% swa deploy --deployment-token acbaf48d24759c9bd2dc5ee8480553a9535382a3910cd9c1244a5759258a610806-4bde6d13-cb78-43ce-aa8c-62fa7bdb51b300301290c0ee6703

% site live URL:
% https://black-flower-0c0ee6703-preview.westeurope.6.azurestaticapps.net/

% brew update && brew install azure-cli

% brew tap azure/functions
% brew install azure-functions-core-tools@4

# test data

Fact:
James Smith, a South African resident, is the owner of a property in Benoni and is a director of two companies, namely ABC (a South African private company that owns various properties in Boksburg) and XYZ (a South African company listed on the JSE that operates a mining business in Gauteng). James Smith also holds 75% of the shares in ABC and holds 20% of the shares in XYZ. XYZ wishes to buy assets from both ABC (namely one of their properties in Boksburg) and from James Smith himself (namely the property in Benoni). The total purchase price for these assets is worth more than 10% of XYZ's market capitalisation on the JSE.

Questions:
Is James Smith entitled to participate and vote at the meeting of the board of directors of ABC that is required to approve the sale of the Boksburg property to XYZ? If so, explain why. If not, explain why and also what he must do in the circumstances.

Assumptions:

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type aware lint rules:

- Configure the top-level `parserOptions` property like this:

```js
export default {
  // other rules...
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    project: ["./tsconfig.json", "./tsconfig.node.json"],
    tsconfigRootDir: __dirname,
  },
};
```

- Replace `plugin:@typescript-eslint/recommended` to `plugin:@typescript-eslint/recommended-type-checked` or `plugin:@typescript-eslint/strict-type-checked`
- Optionally add `plugin:@typescript-eslint/stylistic-type-checked`
- Install [eslint-plugin-react](https://github.com/jsx-eslint/eslint-plugin-react) and add `plugin:react/recommended` & `plugin:react/jsx-runtime` to the `extends` list
