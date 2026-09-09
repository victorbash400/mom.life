WORKSPACE_ENDPOINTS = {
    'workspace.gmail':'https://gmailmcp.googleapis.com/mcp/v1',
    'workspace.drive':'https://drivemcp.googleapis.com/mcp/v1',
    'workspace.docs':'https://docsmcp.googleapis.com/mcp/v1',
    'workspace.calendar':'https://calendarmcp.googleapis.com/mcp/v1',
}

WORKSPACE_PERMISSION_IDS = {
    namespace: f'google-workspace.{index}'
    for index, namespace in enumerate(WORKSPACE_ENDPOINTS)
}


def namespaces(plugin_ids):
    return [namespace for identity in plugin_ids for namespace in (WORKSPACE_ENDPOINTS if identity == 'google-workspace' else [identity])]


def owner(namespace):
    return 'google-workspace' if namespace in WORKSPACE_ENDPOINTS else namespace
