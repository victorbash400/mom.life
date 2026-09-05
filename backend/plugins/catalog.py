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
    Plugin("google-workspace", "Google Workspace", "Gmail, Calendar, Drive, Docs, and family contacts", "Family essentials", "mcp", None, "oauth", ("Read selected mail, calendars, files, and contacts", "Draft messages and create approved events and documents"), "Google Workspace MCP is in Developer Preview; configure its enabled product endpoints and OAuth access."),
    Plugin("todoist", "Todoist", "Household tasks, routines, and shared lists", "Family essentials", "mcp", "https://ai.todoist.net/mcp", "oauth", ("Read selected projects and tasks", "Create and update household tasks"), "Connect Todoist with OAuth."),
    Plugin("instacart", "Instacart", "Create grocery and recipe shopping lists", "Shopping and home", "mcp", "https://mcp.instacart.com/mcp", "bearer", ("Create recipe pages", "Prepare shopping-list pages for approval"), "Set MOM_LIFE_PLUGIN_INSTACART_TOKEN to an Instacart Developer Platform API key."),
    Plugin("google-maps", "Google Maps", "Find places, routes, travel times, and weather", "Family essentials", "mcp", "https://mapstools.googleapis.com/mcp", "api-key", ("Search places and local services", "Calculate routes and look up weather"), "Set MOM_LIFE_PLUGIN_GOOGLE_MAPS_TOKEN to a Maps Grounding Lite key or OAuth token."),
    Plugin("notion", "Notion", "Shared family plans, notes, and routines", "Planning", "mcp", "https://mcp.notion.com/mcp", "oauth", ("Search authorized pages", "Create and update approved family content"), "Connect Notion with OAuth."),
    Plugin("canva", "Canva", "Invitations, routine charts, and family designs", "Planning", "mcp", "https://mcp.canva.com/mcp", "oauth", ("Search family designs", "Create, edit, and export approved designs"), "Canva requires per-user OAuth; custom product redirects may require allowlisting."),
    Plugin("home-assistant", "Home Assistant", "Selected household devices and routines", "Shopping and home", "mcp", None, "oauth-or-bearer", ("Read exposed home state", "Control only explicitly exposed devices"), "Set MOM_LIFE_PLUGIN_HOME_ASSISTANT_URL to your /api/mcp endpoint and configure OAuth or a token."),
    Plugin("microsoft-family", "Microsoft Family", "Outlook mail, calendars, OneDrive, and Microsoft To Do", "Family essentials", "custom-mcp", None, "oauth", ("Read selected Microsoft Graph resources", "Create approved mail drafts, events, files, and tasks"), "The mom.life Graph MCP adapter needs a Microsoft OAuth app and delegated scopes."),
    Plugin("whatsapp", "WhatsApp", "Receive family messages and send approved updates", "Communication", "custom-mcp", None, "bearer", ("Receive messages sent to the mom.life business number", "Send approved replies and templates"), "The mom.life WhatsApp MCP adapter needs a Meta Business app, phone number, webhook, and access token."),
    Plugin("amazon-shopping", "Amazon Shopping", "Research products and prepare purchase options", "Shopping and home", "custom-mcp", None, "oauth-client-credentials", ("Search eligible Amazon catalog data", "Prepare product links for Mom to review"), "The mom.life adapter uses Amazon Creators API catalog access; consumer orders and checkout are not available through it."),
    Plugin("mychart", "MyChart", "Approved child health records from participating providers", "Health and care", "custom-mcp", None, "smart-on-fhir", ("Read only the approved health record categories", "Track care-plan follow-ups without making medical decisions"), "The mom.life SMART on FHIR adapter requires provider support and family proxy authorization."),
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
        "connection_supported": plugin.transport in {"mcp", "agentcore"} or plugin.id in {"microsoft-family", "mychart", "whatsapp", "amazon-shopping"},
        "setup_message": None if connected else plugin.setup_message,
    }


def _env_name(plugin_id: str, suffix: str) -> str:
    return f"MOM_LIFE_PLUGIN_{plugin_id.replace('-', '_').upper()}_{suffix}"
