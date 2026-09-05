# mom.life durable work

## Architecture

Front Desk is the implementation reference: `backend/agents/goal_planner.py`, `agents/goals_chat_agent.py`, `app/goal_tasks.py`, `tools/goal_control.py`, and `tools/goal_tool_registry.py` in the sibling Front Desk checkout. mom.life keeps its existing Strands/Bedrock model configuration and UI.

The Ask agent is also the family goal supervisor. It reads persisted boards before reporting work, creates requested goals, and sends all plan changes through the dedicated planner. The planner emits create/reuse/update/steer/retry/cancel operations against the existing ledger. Plan operations commit atomically. Invalid references, duplicate titles, and edits to completed work are rejected. Retrying a failed assignment keeps its identity and history.

Each assignment constructs a fresh generic worker from its instruction, selected skill procedures, required inputs/expected outputs, family context, dependency evidence, answers, and prior tool receipts. Skills are procedures, not fixed agent personas. Plugin namespaces are loaded on demand. Google Workspace is divided by product; the worker never gets every installed tool by default.

Assignments persist in SQLite with progress, phase, next step, report, expected outputs and evidence. Open questions and exact action approvals persist independently. Answers resume the blocked assignment. Revisions invalidate obsolete open questions and unused approvals. Completion validates evidence for each expected output in both the worker tool and runtime. A user cannot mark an unfinished goal complete through the status API.

Updates use an SSE subscription and event-triggered snapshots, with a fresh snapshot after reconnect. There is no periodic fetch, scheduled polling loop, or background server started by this implementation. The task list shows current work in the existing expandable rows; each row exposes assignment details, evidence, questions, approval arguments, pause/resume, deletion and plan revision. Connections keeps its existing shell and gains install/validation/permission controls plus a skills library/editor.

## Recovery and deployment boundary

Database state survives process exits. Startup pauses interrupted queued/running/planning goals; it does not dispatch external work. Resume is explicit. Local advisory file locks prevent duplicate workers for the same goal across processes sharing the database directory. A server-side failure is recorded on the assignment and goal and requires a corrected retry, not an automatic repeated action. Tool dispatch receipts are retained; ambiguous interrupted actions are not assumed unsuccessful.

This remains the repository's single-family local application: the Next.js proxy uses `sarah-family`, and its current profile data is synchronized before chat or task creation. Family query parameters provide ownership checks, not production authentication. Deploy behind authenticated family identity before exposing the API publicly. SSE delivery is process-local; use one serving process with the local SQLite deployment. Multi-host cloud dispatch and cross-instance event transport from Front Desk are not copied into this local backend.

## Verification

Run without starting servers:

```sh
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q
pnpm lint
pnpm build
```

Tests use temporary databases, fake model boundaries and HTTP mock transports. They exercise planning transactions, dependency handling, retry identity, family ownership, recovery, approvals, runtime failures and bounded API requests. They do not claim a live Bedrock completion, OAuth connection, provider operation, or cloud deployment. See `family-plugins.md` for the verified provider contracts and credential/onboarding requirements.
