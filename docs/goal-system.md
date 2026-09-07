# mom.life durable work

## Architecture

Front Desk is the implementation reference: `backend/agents/goal_planner.py`, `agents/goals_chat_agent.py`, `app/goal_tasks.py`, `tools/goal_control.py`, and `tools/goal_tool_registry.py` in the sibling Front Desk checkout. mom.life keeps its existing Strands/Bedrock model configuration and UI.

The Ask agent is also the family goal supervisor. It reads persisted boards before reporting work, creates requested goals, and sends all plan changes through the dedicated planner. The planner emits create/reuse/update/steer/retry/cancel operations against the existing ledger. Plan operations commit atomically. Invalid references, duplicate titles, and edits to completed work are rejected. Retrying a failed assignment keeps its identity and history.

Each assignment constructs a fresh generic worker from its instruction, selected skill procedures, required inputs/expected outputs, family context, dependency evidence, answers, and prior tool receipts. Skills are procedures, not fixed agent personas. Plugin namespaces are loaded on demand. Google Workspace is divided by product; the worker never gets every installed tool by default.

Assignments persist in PostgreSQL with progress, phase, next step, report, expected outputs and evidence. Open questions and exact action approvals persist independently. Answers resume the blocked assignment. Revisions invalidate obsolete open questions and unused approvals. Completion validates evidence for each expected output in both the worker tool and runtime. A user cannot mark an unfinished goal complete through the status API.

Updates use an SSE subscription and event-triggered snapshots, with a fresh snapshot after reconnect. There is no periodic fetch, scheduled polling loop, or background server started by this implementation. The task list shows current work in the existing expandable rows; each row exposes assignment details, evidence, questions, approval arguments, pause/resume, deletion and plan revision. Connections keeps its existing shell and gains install/validation/permission controls plus a skills library/editor.

## Recovery and deployment boundary

Database state survives process exits. Startup pauses interrupted queued/running/planning goals; it does not dispatch external work. Resume is explicit. PostgreSQL advisory locks prevent duplicate workers for the same goal across hosts. A server-side failure is recorded on the assignment and goal and requires a corrected retry, not an automatic repeated action. Tool dispatch receipts are retained; ambiguous interrupted actions are not assumed unsuccessful.

Each registered account owns its family. The Next.js proxy uses the authenticated session family, and current profile data is synchronized before chat or task creation. An opaque session now gates the application and family APIs. The backend validates session expiry and family ownership independently of the Next.js UI. Registration creates a private family workspace; Sarah remains a separate shared demo. SSE delivery is process-local; use one serving process with the PostgreSQL deployment. Multi-host cloud dispatch and cross-instance event transport from Front Desk are not copied into this local backend.

## Verification

Run without starting servers:

```sh
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q
pnpm lint
pnpm build
```

Tests use explicit SQLite fixtures and isolated PostgreSQL test records, fake model boundaries and HTTP mock transports. They exercise planning transactions, dependency handling, retry identity, family ownership, recovery, approvals, runtime failures and bounded API requests. They do not claim a live Bedrock completion, OAuth connection, provider operation, or cloud deployment. See `family-plugins.md` for the verified provider contracts and credential/onboarding requirements.

## Task board parity pass

The expandable mom.life task row now includes Front Desk's ordered assignment/milestone board. Worker updates come from the persisted activity ledger, are grouped by assignment, and repeated milestone text is shown once. Only an active running assignment marks its latest line active. Assignment details expose the operational instruction, currently selected skill procedures, permitted namespaces, and expected outputs. These displayed skills describe the current configuration, not an immutable historical skill-version snapshot.

Tool starts, results, and errors publish immediate family-scoped SSE invalidations. Each assignment displays its tool call status, including an explicit missing-result state for interrupted calls. Worker progress accepts planning, working, and checking phases; only verified completion can set completion. Progress tools execute asynchronously on the runtime event loop. Tests exercise the actual worker tool wrappers through an approval/resume cycle, persisted milestone retrieval, and family event isolation.

Browser implementation and live provider onboarding were outside this parity pass. The UI changes use mom.life's existing task-row spacing and colors rather than Front Desk's visual theme.

## Demo authentication

Open `/sign-in`. Use `demo@mom.life` and `MomLifeDemo!`, or the demo-fill button. `/sign-up` shares the same fixed-size organic SVG shell and creates an account with name, email, and password. Sign out from Sarah's profile. The demo is a shared account, not a private family account.

Next.js sets a 24-hour HttpOnly, SameSite=Lax cookie (Secure over HTTPS), forwards its opaque token to the backend, and rejects cross-origin mutations. The backend stores only token digests in PostgreSQL, checks expiry on every family API request, rejects mismatched family IDs, and revokes the token on logout. Health and Meta's signature-verified webhook remain public. Existing provider OAuth is separate from account login. Auth checks follow the Next.js guidance to enforce access at the data boundary, not just routing: https://nextjs.org/docs/app/guides/authentication .

Password reset and email verification are not part of this release.

## PostgreSQL family storage

The running application requires `MOM_LIFE_DATABASE_URL` with a PostgreSQL URL. Local development uses the existing PostgreSQL service and database `mom_life`; no development server is started by setup. Run `PYTHONPATH=backend backend/.venv/bin/python backend/scripts/migrate_postgres.py` once to import local SQLite task/session records. Source files are retained. SQL fixture tests can still explicitly use SQLite paths; production cannot silently fall back to SQLite.

Registration creates a new family and account with an Argon2 password hash. New families start without children. Sarah's demo children and original folder names are imported once. Child records own their photos, notification preferences, and folder tree. PostgreSQL foreign keys enforce family/child/parent relationships and cascade folder/file deletion. Child deletion pauses existing child work; completed history remains retained. Uploaded pictures are decoded and re-encoded as JPEG; file downloads use attachment disposition. Pictures (5 MB input limit) and files (10 MB limit) are stored as PostgreSQL bytea in this release, so a database backup includes them. An S3 storage backend is not implemented or required for this local release.

The same schema works with an RDS PostgreSQL connection; AWS provisioning and deployment are separate. Configure TLS and credentials in the deployment environment. Runtime goal locks use PostgreSQL advisory locks. SSE notifications remain process-local, so run one serving process until a cross-instance event transport is added. Provider OAuth encryption still requires the existing connection key alongside the database.
