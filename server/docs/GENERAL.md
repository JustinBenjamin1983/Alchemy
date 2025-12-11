# TODO

- security check
  - IP restrictions on function apps - 102.133.236.223/32 (incl for async processors?)?
- set API policy at API function app level
  embedding model used — typically:
  -text-embedding-ada-002 (OpenAI)
  -textembedding-gpt-3.5 (Azure OpenAI)

# DB drop scripts

<!-- DELETE FROM perspective_risk;
DELETE FROM perspective;
DELETE FROM document_history;
DELETE FROM document;
DELETE FROM folder;
DELETE FROM due_diligence_member;
DELETE FROM due_diligence; -->

# Billing alerts:

https://portal.azure.com/#view/Microsoft_Azure_CostManagement/CostAnalysis/scope/%2Fsubscriptions%2Fd98044c4-5c04-4ad9-8775-9656750361ec
https://portal.azure.com/#view/Microsoft_Azure_CostManagement/BudgetCreateBlade/id/%2Fsubscriptions%2Fd98044c4-5c04-4ad9-8775-9656750361ec/openedBy/ACM.Budgets

# APIM

IP addresses
https://www.microsoft.com/en-us/download/details.aspx?id=56519

apim-func-test-123123123412

aishop-test-32434 inbound processing:
<policies>
<inbound>

<base />
<!-- CORS Settings -->
<cors>
<allowed-origins>
<origin>https://black-flower-0c0ee6703-preview.westeurope.6.azurestaticapps.net</origin>
<origin>http://localhost:5174</origin>
<origin>http://localhost:5173</origin>
</allowed-origins>
<allowed-methods>
<method>GET</method>
<method>POST</method>
<method>OPTIONS</method>
</allowed-methods>
<allowed-headers>
<header>_</header>
</allowed-headers>
<expose-headers>
<header>_</header>
</expose-headers>
</cors>
<!-- Step 1: Validate the JWT and store claims in a variable -->
<validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized" output-token-variable-name="jwt">
<openid-config url="https://alchemyapps.b2clogin.com/alchemyapps.onmicrosoft.com/B2C_1_Alchemy_TheAIShop_SignInUpWithAD/v2.0/.well-known/openid-configuration" />
<required-claims>
<claim name="aud">
<value>73a5e1db-cf1d-4e21-b497-68c8979b4cce</value>
</claim>
</required-claims>
</validate-jwt>
<set-backend-service id="apim-generated-policy" backend-id="aishop-test-32434" />
<set-header name="function-key" exists-action="override">
<value>{{Function-Key}}</value>
</set-header>
</inbound>
<backend>
<base />
</backend>
<outbound>
<base />
<set-header name="function-key" exists-action="delete" />
</outbound>
<on-error>
<base />
</on-error>
</policies>

alchemy-aishop-func-app-test-docker inbound processing

<!--
    - Policies are applied in the order they appear.
    - Position <base/> inside a section to inherit policies from the outer scope.
    - Comments within policies are not preserved.
-->
<!-- Add policies as children to the <inbound>, <outbound>, <backend>, and <on-error> elements -->
<policies>
    <!-- Throttle, authorize, validate, cache, or transform the requests -->
    <inbound>
        <base />
        <!-- CORS Settings -->
        <cors>
            <allowed-origins>
                <origin>https://black-flower-0c0ee6703-preview.westeurope.6.azurestaticapps.net</origin>
                <origin>http://localhost:5174</origin>
                <origin>http://localhost:5173</origin>
            </allowed-origins>
            <allowed-methods>
                <method>GET</method>
                <method>POST</method>
                <method>OPTIONS</method>
            </allowed-methods>
            <allowed-headers>
                <header>*</header>
            </allowed-headers>
            <expose-headers>
                <header>*</header>
            </expose-headers>
        </cors>
        <!-- Step 1: Validate the JWT and store claims in a variable -->
        <validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized" output-token-variable-name="jwt">
            <openid-config url="https://alchemyapps.b2clogin.com/alchemyapps.onmicrosoft.com/B2C_1_Alchemy_TheAIShop_SignInUpWithAD/v2.0/.well-known/openid-configuration" />
            <required-claims>
                <claim name="aud">
                    <value>73a5e1db-cf1d-4e21-b497-68c8979b4cce</value>
                </claim>
            </required-claims>
        </validate-jwt>
        <set-backend-service id="apim-generated-policy" backend-id="alchemy-aishop-func-app-test-docker" />
        <set-header name="function-key" exists-action="override">
            <value>{{Function-Key}}</value>
        </set-header>
    </inbound>
    <!-- Control if and how the requests are forwarded to services  -->
    <backend>
        <base />
    </backend>
    <!-- Customize the responses -->
    <outbound>
        <base />
        <set-header name="function-key" exists-action="delete" />
    </outbound>
    <!-- Handle exceptions and customize error responses  -->
    <on-error>
        <base />
    </on-error>
</policies>
