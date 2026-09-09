# Family plugin adapters

Verified against provider documentation on September 9, 2026. The directory describes provider capabilities; installing a plugin does not claim that credentials, provider approval, or live access exist.

## Runtime contract

`backend/plugins/runtime.py` owns one run's connections. Workers see a compact permitted namespace directory, call `load_goal_tools`, inspect the returned JSON schemas, then call `call_plugin`. Unknown namespace/tool names fail. Connections close when a worker completes, blocks, fails, or is cancelled. MCP discovery supports pagination.

Credentials are server-side environment variables or `backend/.env`. Each connection needs `MOM_LIFE_PLUGIN_<ID>_FAMILY_ID` matching the requesting family and `MOM_LIFE_PLUGIN_<ID>_TOKEN`. Convert hyphens to underscores and uppercase IDs. A URL override is `MOM_LIFE_PLUGIN_<ID>_URL`. Never put credentials in a goal, skill, browser storage, or frontend variable.

The UI's Install action persists installation. Check connection performs actual MCP discovery or a read-only API probe and records when that succeeded. Authorize starts OAuth using PKCE S256 and a one-use state. The callback exchanges the authorization code, encrypts family-bound tokens, and validates the real provider before marking the connection complete. Google uses the registered mom.life client. Todoist, Notion, and Canva use their published authorization-server metadata and dynamic client registration; those client credentials are encrypted in the connection store. Expired access tokens refresh on demand when the provider issued a refresh token. The app does not silently switch providers. A previously validated timestamp is evidence of that check, not a promise that access can never expire.

Google Workspace is presented as one connected account with separate Gmail, Drive, Docs, and Calendar service switches. Each switch controls its matching namespace. The OAuth callback validates every enabled service and marks the plugin connected without a second user action. When Google returns OpenID identity claims, the account row uses the connected user's name, email, and profile image.

MCP methods with no application-defined read contract require approval of the exact namespace, tool name, and arguments. The approval is bound to one assignment and consumed once, before dispatch. API adapters expose bounded read operations and explicitly identify writes. A disabled coarse permission stops use of that provider rather than guessing which arbitrary third-party method it covers. Removing a plugin revokes access on the next tool call.

## Google Workspace adapter

`google_workspace_adapter.py` exposes bounded tools over the official Gmail, Drive, Docs, and Calendar REST APIs using the connected user's OAuth token. It supports Gmail search/read/draft creation, Drive search/metadata, Docs read/append, and Calendar event reads. Write tools remain subject to exact assignment approval. This is the immediate runtime because Google Workspace MCP remains in Developer Preview and requires separate program enrollment. The matching MCP services are enabled in the Google Cloud project so the transport can move to Google's hosted servers after that project is accepted into the preview.

## Official MCP connections

| Plugin | Adapter / endpoint | Authorization and limits |
| --- | --- | --- |
| Todoist | `https://ai.todoist.net/mcp` | OAuth with dynamic client registration. Shared projects/tasks depend on the authorized account. |
| Instacart | `https://mcp.instacart.com/mcp` | Developer Platform API key as bearer token. Produces shopping and recipe pages; do not imply it purchases groceries. |
| Google Maps | `https://mapstools.googleapis.com/mcp` | A restricted mom.life server key is supplied through `X-Goog-Api-Key`. Families can add the capability without sharing the credential. Grounding Lite provides place search, weather, and routes; it does not expose a child's live location or Google location sharing. |
| Notion | `https://mcp.notion.com/mcp` | OAuth with dynamic client registration; only the selected workspace and the user's existing access. |
| Canva | `https://mcp.canva.com/mcp` | Per-user OAuth with dynamic client registration. The server's exact tools are discovered at run time and consequential calls still require assignment approval. |

Sources: [Workspace MCP configuration](https://developers.google.com/workspace/guides/configure-mcp-servers), [Todoist developer documentation](https://developer.todoist.com/api/v1/), [Instacart MCP](https://docs.instacart.com/developer_platform_api/guide/tutorials/mcp/), [Maps Grounding Lite](https://developers.google.com/maps/ai/grounding-lite), [Notion connection guide](https://developers.notion.com/guides/mcp/get-started-with-mcp), [Canva MCP](https://www.canva.dev/docs/mcp/).

## Education adapter

Google Classroom exposes read-only `list_courses`, `list_coursework`, and `list_announcements` tools through the official Classroom REST API. It reuses mom.life's registered Google OAuth client while requesting a separate, narrow set of Classroom scopes and retaining a separate family-bound token. Standard Google accounts can use Classroom; school-managed features still depend on the school's licensing and policy. A guardian relationship can provide summaries but does not silently grant the parent student-level API access.

The Education Agent reviews each newly persisted incoming item without keyword rules. It can discover read-only tools from connected Education-category plugins, then maintains one evidence-linked natural-language snapshot per known child. It records what the evidence supports about what the child is learning, how things appear to be going, meaningful changes, and anything important for the parent. It does not impose fixed subjects, progress labels, attendance, or a guessed curriculum. Existing incoming items without an education review are recovered on application startup; live items are dispatched by the intake manager. No polling is used.

Source: [Google Classroom API overview](https://developers.google.com/workspace/classroom/guides/get-started), [Classroom users and guardians](https://developers.google.com/workspace/classroom/guides/key-concepts/user-types).

## Health and activity adapters

Fitbit exposes read-only profile, dated activity, and dated sleep tools through its Web API. Withings exposes measurements, dated activity, and dated sleep through its Health Data API; Withings also provides a demo user for integration testing. Both adapters require the profile owner to authorize access and are health-tracking inputs, not clinical diagnosis or treatment tools.

Apple Health is a companion connection because HealthKit data remains on the iPhone and has no server-side account API. After the signed-in mom.life iPhone companion receives per-category HealthKit permission, it pushes anchored changes and deletions to `/api/plugins/apple-health/sync`. The backend normalizes only steps, active energy, walking or running distance, heart rate, and sleep stages. The worker runtime exposes `read_daily_activity`, `read_sleep`, `read_heart_rate`, and `latest_sync` as bounded tools. It does not poll HealthKit, fabricate samples, or mark the connection valid before a real sample is synchronized.

Sources: [Fitbit Web API](https://dev.fitbit.com/build/reference/web-api/explore/), [Withings OAuth flow](https://developer.withings.com/developer-guide/v3/integration-guide/public-health-data-api/get-access/oauth-web-flow/), [Apple HealthKit authorization](https://developer.apple.com/documentation/HealthKit/authorizing-access-to-health-data), [HealthKit anchored queries](https://developer.apple.com/documentation/healthkit/executing-anchored-object-queries).

## Alexa boundary

Alexa's public developer surface is designed for building skills and controlling cloud-connected devices; it is not a general API for reading a family's Alexa history or Amazon household account. mom.life therefore does not show a misleading Alexa data plugin. A later mom.life Alexa skill can expose selected agent actions to voice without treating Alexa as an unrestricted data source.

Source: [Alexa Smart Home Skills](https://developer.amazon.com/en-US/alexa/alexa-skills-kit/get-deeper/smart-home-skills).

## WhatsApp Business adapter

Implemented `send_text` calls the configured business phone's Graph `/messages` resource. It requires `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_API_VERSION`, authorized token, family binding, `WHATSAPP_VERIFY_TOKEN`, and `WHATSAPP_APP_SECRET` (all with the `MOM_LIFE_PLUGIN_` prefix). The worker approval gate binds the exact recipient and text. This is business messaging, not access to Mom's personal WhatsApp history or groups. Business policy, customer-service windows, and template rules remain provider-enforced. A provider response accepting a message is not delivery evidence.

Incoming message integration contract: Meta webhook verification challenge, signature verification over the raw payload using the app secret, deduplication by message ID, business-phone-to-family binding, and a persisted message event. Only an explicitly subscribed assignment should resume from that event. An HTTP arrival must never become a fabricated user instruction. The validation probe reads the configured business phone identity; it never sends a test message. Incoming webhook onboarding remains a separate integration requirement.

Source: [Meta-maintained business messaging sample and permissions](https://github.com/fbsamples/business-messaging-sample-tech-provider-app/blob/main/README.md), [Meta webhook reference collection](https://www.postman.com/meta/whatsapp-business-platform/folder/tduohwq/webhook-payload-reference).

## Browser adapter boundary

AgentCore Browser is listed with setup required, not connected from the mere presence of an AWS region. Its adapter contract is IAM-authorized session creation, session-scoped browser/CDP operations, observed page evidence, and explicit session cleanup. The implemented `browser_adapter.py` exposes inspect, navigate, click by exact observed role/name, and fill by exact observed label. It uses the AgentCore SDK and Playwright CDP connection; no local browser or server is launched. Ambiguous targets fail. Runs close their session on completion or failure. A human approval pause retains the assignment-bound session for up to its 15-minute TTL and disconnects the local CDP client. Resume reconnects to that exact session; expiry fails visibly instead of silently opening a blank browser. Plan revision and goal deletion explicitly stop retained sessions. Connection validation lists sessions to check the IAM identity without creating one; the first approved action establishes session creation access. Installing the directory entry alone does not establish IAM access.

Source: [AgentCore Browser](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-tool.html).

The local backend uses the dedicated `mom-life-app` IAM user through the `mom-life` AWS profile. Its inline `MomLifeApplicationAccess` policy permits Bedrock model invocation and AgentCore Browser operations only; it does not inherit the shared Operator identity. Production AWS compute should replace the local access key with an equivalent workload role.


## OAuth client setup

Google Workspace uses `MOM_LIFE_PLUGIN_GOOGLE_WORKSPACE_OAUTH_AUTHORIZE_URL`, `TOKEN_URL`, `CLIENT_ID`, `CLIENT_SECRET`, `REDIRECT_URI`, and `SCOPES`. Google Classroom reuses those client credentials but requests and stores its own Classroom authorization. Providers that do not publish dynamic registration use the equivalent `MOM_LIFE_PLUGIN_<ID>_OAUTH_` variables. Only HTTPS provider endpoints are accepted, and local HTTP callbacks are limited to loopback hosts.

Todoist, Notion, and Canva publish OAuth authorization-server metadata and dynamic client registration. mom.life discovers their endpoints, registers the current callback, encrypts the returned client material, and includes the MCP resource audience during authorization and token exchange. A deployment with a different callback needs its own registration. Access tokens are never reused across plugin resources.

Tokens are encrypted with a server-local key in the ignored backend data directory. Back up that key with the database. Callback state expires after ten minutes and is consumed before token exchange. Disconnect removes tokens and pending authorization attempts. Credentials refresh on demand before use, retaining a rotated refresh token when issued. No background polling is used. A rejected refresh produces a visible reconnect requirement. Concurrent refreshes use an advisory lock, and a conditional write prevents removed or replaced authorization from being restored.
