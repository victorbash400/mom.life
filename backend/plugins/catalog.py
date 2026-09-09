import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Plugin:
    id: str
    name: str
    description: str
    group: str
    transport: str
    server_url: str | None
    auth: str
    permissions: tuple[str, ...]
    setup_message: str


PLUGINS = (
    Plugin("google-workspace", "Google Workspace", "Gmail, Calendar, Drive, and Docs", "Family essentials", "custom-mcp", None, "oauth", ("Gmail", "Google Drive", "Google Docs", "Google Calendar"), "Connect a Google account with access to the selected Workspace services."),
    Plugin("google-classroom", "Google Classroom", "Courses, assignments, announcements, and due dates", "Education", "custom-mcp", None, "oauth", ("Read the signed-in student's courses and class posts", "Read assignment and due-date details"), "Connect the Google account that belongs to the Classroom courses you want mom.life to read."),
    Plugin("todoist", "Todoist", "Household tasks, routines, and shared lists", "Family essentials", "mcp", "https://ai.todoist.net/mcp", "oauth", ("Read selected projects and tasks", "Create and update household tasks"), "Connect Todoist with its official OAuth flow."),
    Plugin("instacart", "Instacart", "Create grocery and recipe shopping lists", "Shopping and home", "mcp", "https://mcp.instacart.com/mcp", "bearer", ("Create recipe pages", "Prepare shopping-list pages for approval"), "Set MOM_LIFE_PLUGIN_INSTACART_TOKEN to an Instacart Developer Platform API key."),
    Plugin("google-maps", "Google Maps", "Find places, routes, travel times, and weather", "Family essentials", "mcp", "https://mapstools.googleapis.com/mcp", "api-key", ("Search places and local services", "Calculate routes and look up weather"), "Google Maps uses mom.life's restricted server key. It does not access family location sharing."),
    Plugin("notion", "Notion", "Shared family plans, notes, and routines", "Planning", "mcp", "https://mcp.notion.com/mcp", "oauth", ("Search authorized pages", "Create and update approved family content"), "Connect a Notion workspace with its official OAuth flow."),
    Plugin("canva", "Canva", "Invitations, routine charts, and family designs", "Planning", "mcp", "https://mcp.canva.com/mcp", "oauth", ("Search family designs", "Create, edit, and export approved designs"), "Connect a Canva account with its official OAuth flow."),
    Plugin("home-assistant", "Home Assistant", "Selected household devices and routines", "Shopping and home", "mcp", None, "oauth-or-bearer", ("Read exposed home state", "Control only explicitly exposed devices"), "Set MOM_LIFE_PLUGIN_HOME_ASSISTANT_URL to your /api/mcp endpoint and configure OAuth or a token."),
    Plugin("microsoft-family", "Microsoft Family", "Outlook mail, calendars, OneDrive, and Microsoft To Do", "Family essentials", "custom-mcp", None, "oauth", ("Read selected Microsoft Graph resources", "Create approved mail drafts, events, files, and tasks"), "The mom.life Graph MCP adapter needs a Microsoft OAuth app and delegated scopes."),
    Plugin("whatsapp", "WhatsApp", "Receive family messages and send approved updates", "Communication", "custom-mcp", None, "bearer", ("Receive messages sent to the mom.life business number", "Send approved replies and templates"), "The mom.life WhatsApp MCP adapter needs a Meta Business app, phone number, webhook, and access token."),
    Plugin("amazon-shopping", "Amazon Shopping", "Research products and prepare purchase options", "Shopping and home", "custom-mcp", None, "oauth-client-credentials", ("Search eligible Amazon catalog data", "Prepare product links for Mom to review"), "The mom.life adapter uses Amazon Creators API catalog access; consumer orders and checkout are not available through it."),
    Plugin("mychart", "MyChart", "Approved child health records from participating providers", "Health and care", "custom-mcp", None, "smart-on-fhir", ("Read only the approved health record categories", "Track care-plan follow-ups without making medical decisions"), "The mom.life SMART on FHIR adapter requires provider support and family proxy authorization."),
    Plugin("fitbit", "Fitbit", "Activity and sleep from an authorized Fitbit profile", "Health and care", "custom-mcp", None, "oauth", ("Read profile and daily activity summaries", "Read sleep summaries for selected dates"), "Connect Fitbit with read-only profile, activity, and sleep scopes."),
    Plugin("withings", "Withings", "Measurements, activity, and sleep from Withings devices", "Health and care", "custom-mcp", None, "oauth", ("Read authorized body measurements", "Read authorized activity and sleep summaries"), "Connect Withings with user.info, user.metrics, and user.activity scopes. Withings provides a demo account for integration testing."),
    Plugin("apple-health", "Apple Health", "Health and activity data stored on Apple devices", "Health and care", "companion", None, "device-consent", ("Read only health categories approved on the device",), "Apple Health requires a native iPhone companion app and per-category HealthKit permission."),
    Plugin("health-connect", "Health Connect", "Health and fitness data stored on Android devices", "Health and care", "companion", None, "device-consent", ("Read only health categories approved on the device",), "Health Connect requires an Android companion app and declared per-category permissions."),
    Plugin("agentcore-browser", "AgentCore Browser", "Complete permitted work on websites without an API", "Automation", "agentcore", None, "aws-iam", ("Open and inspect managed browser sessions", "Fill forms and prepare consequential actions for approval"), "Configure AWS IAM access to Amazon Bedrock AgentCore Browser."),
)


def plugin_by_id(plugin_id: str) -> Plugin:
    try:
        return next(plugin for plugin in PLUGINS if plugin.id == plugin_id)
    except StopIteration as error:
        raise ValueError("Unknown plugin.") from error


def plugin_snapshot(plugin: Plugin, installed: bool, permissions: dict[str, bool]) -> dict[str, object]:
    connected = False
    return {
        **asdict(plugin),
        "permissions": [{"id": f"{plugin.id}.{index}", "name": text, "enabled": permissions.get(f"{plugin.id}.{index}", True)} for index, text in enumerate(plugin.permissions)],
        "oauth_supported": plugin.auth in {"oauth", "oauth-or-bearer", "smart-on-fhir"},
        "installed": installed,
        "connected": connected,
        "connection_supported": plugin.transport in {"mcp", "agentcore", "custom-mcp"},
        "setup_message": None if connected else plugin.setup_message,
    }


def _env_name(plugin_id: str, suffix: str) -> str:
    return f"MOM_LIFE_PLUGIN_{plugin_id.replace('-', '_').upper()}_{suffix}"
