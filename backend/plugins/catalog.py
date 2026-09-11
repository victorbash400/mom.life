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
    Plugin("google-workspace", "Google Workspace", "Gmail, Calendar, Drive, Docs, and Classroom", "Family essentials", "custom-mcp", None, "oauth", ("Gmail", "Google Drive", "Google Docs", "Google Calendar"), "Connect one Google account for Workspace and Classroom."),
    Plugin("google-classroom", "Google Classroom", "Courses, assignments, announcements, and due dates", "Education", "custom-mcp", None, "oauth", ("Read courses", "Read coursework and due dates", "Read announcements"), "Connect the Google account that belongs to the Classroom courses you want mom.life to read."),
    Plugin("todoist", "Todoist", "Household tasks, routines, and shared lists", "Family essentials", "mcp", "https://ai.todoist.net/mcp", "oauth", ("Read selected projects and tasks", "Create and update household tasks"), "Connect Todoist with its official OAuth flow."),
    Plugin("instacart", "Instacart", "Create grocery and recipe shopping lists", "Shopping and home", "mcp", "https://mcp.instacart.com/mcp", "bearer", ("Create recipe pages", "Create requested shopping-list pages"), "Set MOM_LIFE_PLUGIN_INSTACART_TOKEN to an Instacart Developer Platform API key."),
    Plugin("google-maps", "Google Maps", "Find places, routes, travel times, and weather", "Family essentials", "mcp", "https://mapstools.googleapis.com/mcp", "api-key", ("Search places and local services", "Calculate routes and look up weather"), "Google Maps uses mom.life's restricted server key. It does not access family location sharing."),
    Plugin("notion", "Notion", "Shared family plans, notes, and routines", "Planning", "mcp", "https://mcp.notion.com/mcp", "oauth", ("Search authorized pages", "Create and update requested family content"), "Connect a Notion workspace with its official OAuth flow."),
    Plugin("canva", "Canva", "Invitations, routine charts, and family designs", "Planning", "mcp", "https://mcp.canva.com/mcp", "oauth", ("Search family designs", "Create, edit, and export requested designs"), "Connect a Canva account with its official OAuth flow."),
    Plugin("whatsapp", "WhatsApp", "Receive family messages and send requested updates", "Communication", "custom-mcp", None, "bearer", ("Receive messages sent to the mom.life business number", "Send requested replies and templates"), "The mom.life WhatsApp MCP adapter needs a Meta Business app, phone number, webhook, and access token."),
    Plugin("fitbit", "Fitbit", "Activity and sleep from an authorized Fitbit profile", "Health and care", "custom-mcp", None, "oauth", ("Read profile and daily activity summaries", "Read sleep summaries for selected dates"), "Connect Fitbit with read-only profile, activity, and sleep scopes."),
    Plugin("withings", "Withings", "Measurements, activity, and sleep from Withings devices", "Health and care", "custom-mcp", None, "oauth", ("Read authorized body measurements", "Read authorized activity and sleep summaries"), "Connect Withings with user.info, user.metrics, and user.activity scopes. Withings provides a demo account for integration testing."),
    Plugin("apple-health", "Apple Health", "Health and activity data approved on an iPhone", "Health and care", "custom-mcp", None, "device-consent", ("Read synced activity, sleep, and heart-rate samples",), "Connect through the mom.life iPhone companion after granting HealthKit permission."),
    Plugin("agentcore-browser", "AgentCore Browser", "Complete permitted work on websites without an API", "Automation", "agentcore", None, "aws-iam", ("Open and inspect managed browser sessions", "Fill forms and complete requested actions"), "Configure AWS IAM access to Amazon Bedrock AgentCore Browser."),
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
