# Family plugin adapters

Verified against provider documentation on September 9, 2026. The directory describes provider capabilities; installing a plugin does not claim that credentials, provider approval, or live access exist.

## Runtime contract

`backend/plugins/runtime.py` owns one run's connections. Workers see a compact permitted namespace directory, call `load_goal_tools`, inspect the returned JSON schemas, then call `call_plugin`. Unknown namespace/tool names fail. Connections close when a worker completes, blocks, fails, or is cancelled. MCP discovery supports pagination.

Credentials are server-side environment variables or `backend/.env`. Each connection needs `MOM_LIFE_PLUGIN_<ID>_FAMILY_ID` matching the requesting family and `MOM_LIFE_PLUGIN_<ID>_TOKEN`. Convert hyphens to underscores and uppercase IDs. A URL override is `MOM_LIFE_PLUGIN_<ID>_URL`. Never put credentials in a goal, skill, browser storage, or frontend variable.

The UI's Install action persists installation. Check connection performs actual MCP discovery or a read-only API probe and records when that succeeded. Authorize starts the registered OAuth client flow using PKCE S256 and a one-use state. The callback exchanges the authorization code and encrypts family-bound tokens in SQLite. Provider registration must be configured beforehand. Expired tokens fail visibly and require renewed authorization. The app does not silently switch providers. A previously validated timestamp is evidence of that check, not a promise that access can never expire.

Google Workspace is presented as one connected account with separate Gmail, Drive, Docs, and Calendar service switches. Each switch controls its matching namespace. When Google returns OpenID identity claims, the account row uses the connected user's name, email, and profile image.

MCP methods with no application-defined read contract require approval of the exact namespace, tool name, and arguments. The approval is bound to one assignment and consumed once, before dispatch. API adapters expose bounded read operations and explicitly identify writes. A disabled coarse permission stops use of that provider rather than guessing which arbitrary third-party method it covers. Removing a plugin revokes access on the next tool call.

## Official MCP connections

| Plugin | Adapter / endpoint | Authorization and limits |
| --- | --- | --- |
| Google Workspace | `workspace.gmail`, `workspace.drive`, `workspace.docs`, `workspace.calendar` use their respective `https://<product>mcp.googleapis.com/mcp/v1` endpoints | Workspace Developer Preview, enabled MCP APIs, OAuth scopes for each selected product. Shared `GOOGLE_WORKSPACE_TOKEN` and `GOOGLE_WORKSPACE_FAMILY_ID`; optional `WORKSPACE_GMAIL_URL`, etc. overrides. Validation checks only enabled service namespaces, and at least one service must remain enabled. |
| Todoist | `https://ai.todoist.net/mcp` | Provider OAuth access token. Shared projects/tasks depend on the authorized account. |
| Instacart | `https://mcp.instacart.com/mcp` | Developer Platform API key as bearer token. Produces shopping and recipe pages; do not imply it purchases groceries. |
| Google Maps | `https://mapstools.googleapis.com/mcp` | Grounding Lite key supplied through `X-Goog-Api-Key`. Enable the required Google service. |
| Notion | `https://mcp.notion.com/mcp` | OAuth; only authorized workspace content. |
| Canva | `https://mcp.canva.com/mcp` | OAuth and applicable client onboarding. |
| Home Assistant | Operator-configured HTTPS URL ending in `/api/mcp` | Instance authorization and explicitly exposed entities. No unrestricted home-device access is implied. |

Sources: [Workspace MCP configuration](https://developers.google.com/workspace/guides/configure-mcp-servers), [Todoist developer documentation](https://developer.todoist.com/api/v1/), [Instacart MCP](https://docs.instacart.com/developer_platform_api/guide/tutorials/mcp/), [Maps Grounding Lite](https://developers.google.com/maps/ai/grounding-lite), [Notion connection guide](https://developers.notion.com/guides/mcp/get-started-with-mcp), [Canva MCP](https://www.canva.dev/docs/mcp/), [Home Assistant MCP](https://www.home-assistant.io/integrations/mcp_server).

## Microsoft family adapter

Implemented in `api_adapters.py` using Microsoft Graph v1.0. `list_events`, `list_messages`, and `list_task_lists` address the signed-in user; `create_draft` creates a plain-text Outlook draft without sending it. No arbitrary URL/method passthrough exists. OAuth is delegated, supporting applicable personal Microsoft accounts. Request only the permissions actually needed: `Calendars.Read`, `Mail.Read`, `Tasks.Read`, and `Mail.ReadWrite` for drafts. Validate uses the To Do lists read endpoint, so this configured subset needs `Tasks.Read`.

A future separately scoped capability can extend this adapter with event/task creation. Do not mistake Microsoft Family Safety device controls for these Graph mail/calendar/task APIs. No suitable official family-wide MCP surface was established in this research; the implementation uses the documented Graph API directly.

Sources: [Outlook mail API](https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview?view=graph-rest-1.0), [Graph permissions](https://learn.microsoft.com/en-us/graph/permissions-reference).

## Education adapter

Google Classroom exposes read-only `list_courses`, `list_coursework`, and `list_announcements` tools through the official Classroom REST API. The signed-in Google Workspace for Education user and the school's licensing and permissions determine what is visible. A guardian relationship can provide summaries but does not silently grant the parent student-level API access. Configure a registered Google OAuth client with the narrow Classroom read scopes required by these tools.

Source: [Google Classroom API overview](https://developers.google.com/workspace/classroom/guides/get-started), [Classroom users and guardians](https://developers.google.com/workspace/classroom/guides/key-concepts/user-types).

## Health and activity adapters

Fitbit exposes read-only profile, dated activity, and dated sleep tools through its Web API. Withings exposes measurements, dated activity, and dated sleep through its Health Data API; Withings also provides a demo user for integration testing. Both adapters require the profile owner to authorize access and are health-tracking inputs, not clinical diagnosis or treatment tools.

Apple Health and Android Health Connect appear in the directory as companion-app integrations, not web connections. Both stores live on the user's device and require native platform code plus explicit permission for each health-data category. Their Add controls remain unavailable until mom.life has the corresponding iOS or Android companion.

Sources: [Fitbit Web API](https://dev.fitbit.com/build/reference/web-api/explore/), [Withings OAuth flow](https://developer.withings.com/developer-guide/v3/integration-guide/public-health-data-api/get-access/oauth-web-flow/), [Apple HealthKit authorization](https://developer.apple.com/documentation/HealthKit/authorizing-access-to-health-data), [Android Health Connect data types](https://developer.android.com/health-and-fitness/health-connect/data-types).

## Alexa boundary

Alexa's public developer surface is designed for building skills and controlling cloud-connected devices; it is not a general API for reading a family's Alexa history or Amazon household account. mom.life therefore does not show a misleading Alexa data plugin. Home Assistant remains the practical smart-home connection, and a later mom.life Alexa skill can expose selected agent actions to voice without treating Alexa as an unrestricted data source.

Source: [Alexa Smart Home Skills](https://developer.amazon.com/en-US/alexa/alexa-skills-kit/get-deeper/smart-home-skills).

## WhatsApp Business adapter

Implemented `send_text` calls the configured business phone's Graph `/messages` resource. It requires `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_API_VERSION`, authorized token, and family binding (all with the `MOM_LIFE_PLUGIN_` prefix). The worker approval gate binds the exact recipient and text. This is business messaging, not access to Mom's personal WhatsApp history or groups. Business policy, customer-service windows, and template rules remain provider-enforced. A provider response accepting a message is not delivery evidence.

Incoming message integration contract: Meta webhook verification challenge, signature verification over the raw payload using the app secret, deduplication by message ID, business-phone-to-family binding, and a persisted message event. Only an explicitly subscribed assignment should resume from that event. An HTTP arrival must never become a fabricated user instruction. The validation probe reads the configured business phone identity; it never sends a test message. Incoming webhook onboarding remains a separate integration requirement.

Source: [Meta-maintained business messaging sample and permissions](https://github.com/fbsamples/business-messaging-sample-tech-provider-app/blob/main/README.md), [Meta webhook reference collection](https://www.postman.com/meta/whatsapp-business-platform/folder/tduohwq/webhook-payload-reference).

## MyChart / SMART on FHIR adapter

Implemented read-only `read_patient`, `read_observations`, and `read_care_plans`. Configure `MYCHART_URL` to the provider FHIR R4 base and `MYCHART_PATIENT_ID` to the patient returned by authorization, plus token and family binding. The agent cannot supply or override the patient ID. Provider/proxy authorization is required separately for each child; this local configuration binds one authorized patient, not all children. No prescribing, diagnosis, treatment changes, or appointment booking is exposed.

SMART discovery and authorization must be completed through the participating provider. Child access cannot be inferred from a parent's login. The adapter is an API tool source in the same registry; a separate MCP server is unnecessary for internal worker use.

Sources: [Epic FHIR interfaces and SMART support](https://open.epic.com/interface/FHIR), [Epic provider endpoints](https://open.epic.com/MyApps/Endpoints).

## Amazon shopping adapter

Implemented `get_product` using Creators API `POST https://creatorsapi.amazon/catalog/v1/getItems`, a known ASIN, server-configured marketplace and partner tag. Configure `AMAZON_SHOPPING_MARKETPLACE`, `AMAZON_SHOPPING_PARTNER_TAG`, authorized Creators API token, and family binding. Token acquisition uses the region-appropriate Login with Amazon OAuth client-credentials endpoint. No consumer orders, account scraping, cart, checkout, or payment tools exist. Connection validation uses the operator-configured `AMAZON_SHOPPING_VALIDATION_ASIN` and requires a returned product; it never invents a test ASIN.

Sources: [Creators API purpose](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction), [Creators API authentication and GetItems contract](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/get-started/using-curl).

## Browser adapter boundary

AgentCore Browser is listed with setup required, not connected from the mere presence of an AWS region. Its adapter contract is IAM-authorized session creation, session-scoped browser/CDP operations, observed page evidence, and explicit session cleanup. The implemented `browser_adapter.py` exposes inspect, navigate, click by exact observed role/name, and fill by exact observed label. It uses the AgentCore SDK and Playwright CDP connection; no local browser or server is launched. Ambiguous targets fail. Runs close their session on completion or failure. A human approval pause retains the assignment-bound session for up to its 15-minute TTL and disconnects the local CDP client. Resume reconnects to that exact session; expiry fails visibly instead of silently opening a blank browser. Plan revision and goal deletion explicitly stop retained sessions. Connection validation lists sessions to check the IAM identity without creating one; the first approved action establishes session creation access. Installing the directory entry alone does not establish IAM access.

Source: [AgentCore Browser](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-tool.html).


## Registered OAuth client setup

Configure `MOM_LIFE_PLUGIN_<ID>_OAUTH_AUTHORIZE_URL`, `TOKEN_URL`, `CLIENT_ID`, `REDIRECT_URI`, and `SCOPES` under the same OAuth prefix. `CLIENT_SECRET` and `RESOURCE` are optional, depending on the registered provider client. Register the exact frontend callback URL, such as `http://localhost:3000/api/oauth/callback`, with the provider. Only HTTPS provider endpoints are accepted. This is a registered-client integration, not automatic MCP dynamic client registration. Use the authorization server and resource audience documented by the actual provider; do not reuse an access token across unrelated resources.

Tokens are encrypted with a server-local key in the ignored backend data directory. Back up that key with the database. Callback state expires after ten minutes and is consumed before token exchange. Disconnect removes tokens and pending authorization attempts. Credentials refresh on demand before use, retaining a rotated refresh token when issued. No background polling is used. A rejected refresh produces a visible reconnect requirement. Concurrent refreshes use an advisory lock, and a conditional write prevents removed or replaced authorization from being restored.
