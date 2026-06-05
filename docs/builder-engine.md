# Builder Engine (Module 18)

How the platform generates, tests, and deploys code — turning validated ideas into functional MVPs without manual development.

---

## Why This Module Exists

The platform can validate ideas (research, interviews, experiments) but without a Builder Engine it cannot:
- Generate landing pages for demand tests
- Build micro-MVPs for retention tests (B2C validation Stage 4)
- Deploy tracking scripts and ad pixels
- Create functional prototypes from validated BuildSpecs
- Iterate on code based on test results

The Builder Engine closes the loop: **Validation → Build → Deploy → Learn.**

---

## Architecture

```
                  ┌──────────────────────────────┐
                  │      Core Event Bus           │
                  └──────────────┬───────────────┘
                                 │
                   Trigger Event │ (e.g., "venture.build_mvp")
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ MODULE 18: BUILDER ENGINE                                        │
│                                                                  │
│  1. Context Assembler ──▶ Pulls specs from Core contracts        │
│  2. Prompt Compiler   ──▶ Renders BuildSpec into agent prompt    │
│  3. RunCord Trigger   ──▶ Triggers coding agent in sandbox       │
│  4. Monitor & Verify  ──▶ Watches PR, validates output           │
└──────────────────────────────────────────────────────────────────┘
                                 │
                   Success Event │ (e.g., "build.completed")
                                 ▼
                  ┌──────────────────────────────┐
                  │   Deployment Engine           │
                  └──────────────────────────────┘
```

---

## Execution Layer: RunCord

RunCord (runcord.com) provides the sandboxed execution infrastructure. The Builder Engine orchestrates; RunCord executes.

### What RunCord Provides

| Capability | Details |
|-----------|---------|
| **Coding agents** | Claude Code, OpenCode (any model provider) |
| **Sandbox isolation** | Daytona (default), Modal (for scale). Agent code never touches platform infra. |
| **Triggers** | Slack, Linear, GitHub — tag Cord, agent spins up |
| **Live preview** | Each sandbox runs a dev server with unique preview URL |
| **Persistent storage** | `.claude` folder, dotfiles, test artifacts carry across sessions |
| **Env vars** | Encrypted, auto-injected into every sandbox |
| **Docker** | Fully supported inside sandboxes |
| **Git workflow** | Agent writes code → opens PR → human/automation merges |
| **Self-hosting** | Enterprise plan — deploy on your own infrastructure |

### Why RunCord (vs. Building Our Own)

| Consideration | RunCord | Build from scratch |
|--------------|---------|-------------------|
| Time to integrate | Hours (Slack/API trigger) | Weeks (sandbox infra, agent lifecycle, previews) |
| Cost | $100/dev/month (solo founder = 1 seat) | Daytona hosting + custom orchestration |
| Sandbox security | Their problem (Daytona handles isolation) | Your problem |
| Agent quality | Claude Code / OpenCode (proven) | Same agents, but you manage them |
| Live previews | Built-in | Build yourself |
| Temporal integration | Via webhook signals (PR opened → signal workflow) | Direct (but more work) |
| Migration path | Self-host when you outgrow managed | Already self-hosted |

**Decision:** Use RunCord for Phase 3+. Migrate to direct Daytona SDK integration only if RunCord becomes a bottleneck.

---

## The Build Pipeline (Temporal Workflow)

```python
@workflow.defn
class BuildMVPWorkflow:
    """Orchestrates code generation via RunCord.
    
    Steps:
    1. Assemble context from validated specs
    2. Compile into structured agent prompt
    3. Trigger RunCord (via Slack/API)
    4. Wait for PR (GitHub webhook → Temporal signal)
    5. Validate PR (tests pass, preview works)
    6. Auto-merge or request human review
    7. Deploy
    """
    
    @workflow.run
    async def run(self, spec: BuildSpec) -> BuildResult:
        # Step 1: Assemble context
        context = await workflow.execute_activity(
            assemble_build_context,
            args=[spec],
            start_to_close_timeout=timedelta(minutes=2),
        )
        
        # Step 2: Compile prompt
        prompt = await workflow.execute_activity(
            compile_agent_prompt,
            args=[context],
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        # Step 3: Trigger RunCord
        await workflow.execute_activity(
            trigger_runcord_build,
            args=[prompt, spec.repo, spec.branch],
            start_to_close_timeout=timedelta(minutes=5),
        )
        
        # Step 4: Wait for PR (webhook → signal)
        pr_url = await workflow.wait_condition(
            self.pr_opened,
            timeout=timedelta(hours=2),
        )
        
        # Step 5: Validate
        validation = await workflow.execute_activity(
            validate_build_output,
            args=[pr_url, spec.acceptance_criteria],
            start_to_close_timeout=timedelta(minutes=10),
        )
        
        if not validation.passed:
            # Retry with feedback — routes to the SAME session (see session-threading.md)
            await workflow.execute_activity(
                trigger_runcord_fix,
                args=[session["id"], validation.feedback],
                start_to_close_timeout=timedelta(minutes=5),
            )
            # Wait for agent to push fixes...
        
        # Step 6: Merge
        if spec.auto_merge and validation.passed:
            await workflow.execute_activity(merge_pr, args=[pr_url])
        else:
            await workflow.execute_activity(
                request_human_review, args=[pr_url]
            )
            await workflow.wait_condition(self.review_approved)
        
        # Step 7: Deploy
        deploy_url = await workflow.execute_activity(
            deploy_build, args=[spec.deploy_target]
        )
        
        return BuildResult(
            pr_url=pr_url,
            deploy_url=deploy_url,
            cost_usd=self.total_cost,
        )
```

---

## The BuildSpec Contract

The Builder Engine never receives open-ended prompts. It receives a structured `BuildSpec` produced by earlier validation modules (Offer Design, Product Experience Engine, Workflow Blueprint).

```python
# core/contracts/schemas.py (addition)

class BuildSpec(BaseModel):
    """Structured specification for code generation.
    
    Produced by Product Experience Engine or Offer Design Engine.
    Consumed by Builder Engine (Module 18).
    """
    
    # Identity
    venture_id: str
    build_id: str
    build_type: BuildType  # "landing_page", "micro_mvp", "api_endpoint", "full_app"
    
    # What to build
    description: str  # Human-readable summary
    requirements: list[str]  # Specific functional requirements
    tech_stack: TechStackSpec  # Framework, language, hosting target
    
    # Structure
    pages: list[PageSpec] | None = None  # For landing pages / apps
    api_endpoints: list[EndpointSpec] | None = None  # For backends
    integrations: list[IntegrationSpec] | None = None  # Stripe, Plaid, etc.
    
    # Constraints
    template_repo: str | None = None  # Start from template (not blank slate)
    max_budget_usd: float = 10.0  # Cost cap for this build
    deadline_hours: float = 4.0  # Max time before escalating
    
    # Acceptance criteria
    acceptance_criteria: list[str]  # Must pass before merge
    # e.g., ["builds without errors", "lighthouse score > 90", "stripe webhook works"]
    
    # Deployment
    repo: str  # GitHub repo for the PR
    branch: str = "main"  # Base branch
    deploy_target: str  # "vercel", "fly.io", "static"
    auto_merge: bool = False  # Auto-merge if criteria pass, or wait for human


class BuildType(str, Enum):
    LANDING_PAGE = "landing_page"
    MICRO_MVP = "micro_mvp"
    API_ENDPOINT = "api_endpoint"
    FULL_APP = "full_app"
    TRACKING_SCRIPT = "tracking_script"
    INTEGRATION = "integration"


class TechStackSpec(BaseModel):
    framework: str = "next.js"  # next.js, fastapi, static
    language: str = "typescript"  # typescript, python
    styling: str = "tailwind"  # tailwind, css
    hosting: str = "vercel"  # vercel, fly.io, cloudflare-pages


class PageSpec(BaseModel):
    route: str  # e.g., "/" or "/pricing"
    purpose: str  # e.g., "Landing page with waitlist signup"
    sections: list[str]  # e.g., ["hero", "features", "pricing", "cta"]
    copy: dict[str, str] | None = None  # Pre-written copy from Offer Design


class EndpointSpec(BaseModel):
    method: str  # GET, POST, etc.
    path: str  # e.g., "/api/waitlist"
    purpose: str
    request_schema: dict | None = None
    response_schema: dict | None = None


class IntegrationSpec(BaseModel):
    service: str  # "stripe", "plaid", "sendgrid", "twilio"
    purpose: str  # "process $5/mo subscription"
    config: dict = {}
```

---

## Prompt Compilation

The Context Assembler takes a `BuildSpec` and renders it into a detailed, structured prompt for the coding agent:

```python
@activity.defn
async def compile_agent_prompt(context: BuildContext) -> str:
    """Compile BuildSpec + venture context into agent prompt.
    
    This is NOT a vague "build me a SaaS." It's a structured specification
    with exact requirements, acceptance criteria, and tech stack constraints.
    """
    spec = context.build_spec
    
    prompt = f"""## Build Task: {spec.build_type.value}

### Description
{spec.description}

### Tech Stack
- Framework: {spec.tech_stack.framework}
- Language: {spec.tech_stack.language}
- Styling: {spec.tech_stack.styling}
- Hosting target: {spec.tech_stack.hosting}

### Requirements
{chr(10).join(f'- {r}' for r in spec.requirements)}

### Pages/Routes
{render_pages(spec.pages)}

### API Endpoints
{render_endpoints(spec.api_endpoints)}

### Integrations
{render_integrations(spec.integrations)}

### Acceptance Criteria (ALL must pass)
{chr(10).join(f'- [ ] {c}' for c in spec.acceptance_criteria)}

### Constraints
- Start from template: {spec.template_repo or 'blank Next.js app'}
- Budget: ${spec.max_budget_usd} max
- Branch: feature/{spec.build_id}
- Open PR to: {spec.branch}

### Instructions
1. Create a new branch feature/{spec.build_id}
2. Implement all requirements
3. Ensure all acceptance criteria pass
4. Run build and tests
5. Open a PR with a clear description of what was built
"""
    return prompt
```

---

## Guardrails

### 1. Execution Sandbox (Non-Negotiable)

RunCord handles this via Daytona. The coding agent runs in an isolated sandbox — if it hallucinates a destructive command or enters an infinite loop, it affects nothing outside the sandbox.

### 2. Git Branches as Workspace

The agent never touches production code directly:
- Build starts → new branch `feature/{build_id}`
- Agent commits to this branch only
- PR opened for review (human or automated)
- Only merged after acceptance criteria pass
- Failed builds = branch deleted, no harm done

### 3. Budget Cap

```python
# The Temporal workflow tracks spend
if self.total_cost > spec.max_budget_usd:
    # Stop the build, escalate to founder
    await workflow.execute_activity(
        escalate_budget_exceeded,
        args=[spec, self.total_cost],
    )
    return BuildResult(status="budget_exceeded")
```

### 4. Template-First, Generate-Second

For common patterns, use pre-built templates:

| Build Type | Template | Agent's Job |
|-----------|----------|-------------|
| Landing page | Next.js + Tailwind + waitlist | Fill in copy, add sections, customize styling |
| API endpoint | FastAPI scaffold | Add route logic, connect integrations |
| Stripe integration | Stripe template | Configure products, prices, webhooks |
| Tracking script | Analytics template | Wire up events, configure pixels |

Full code generation from scratch is only for novel requirements. Templates reduce cost 5-10x and improve reliability dramatically.

### 5. Verification Loop

Before any PR is merged, the Builder Engine validates:
- `npm run build` / `pip install` succeeds (no syntax errors)
- Tests pass (if tests exist)
- Linting passes
- Acceptance criteria checked (Lighthouse score, endpoint responds, etc.)
- Preview URL loads correctly

If verification fails, the agent gets feedback and retries (up to 3 attempts before escalating to human).

---

## Integration with Validation Flows

### B2C Flow (from b2c-validation-flow.md)

```
Stage 2: Demand Test
├── Offer Design Engine produces positioning + copy
├── Product Experience Engine produces PageSpec
├── Builder Engine receives BuildSpec:
│   └── build_type: "landing_page"
│   └── pages: [hero, features, waitlist_form]
│   └── acceptance_criteria: ["loads < 2s", "form submits to API"]
│   └── deploy_target: "vercel"
├── RunCord builds it in sandbox
├── PR opened → auto-merged (landing page, low risk)
└── Deployed to Vercel → live URL for ad testing

Stage 4: Retention Test (Micro-MVP)
├── Workflow Blueprint Engine produces BuildSpec:
│   └── build_type: "micro_mvp"
│   └── integrations: [plaid, twilio]
│   └── api_endpoints: [/api/connect-bank, /api/send-insight]
│   └── acceptance_criteria: ["Plaid sandbox connects", "SMS sends"]
├── RunCord builds it
├── PR opened → human review (handles money/PII)
└── Deployed to Fly.io → ready for beta users
```

### ProspectForge Flow

```
Building the outreach sender:
├── Workflow Blueprint produces BuildSpec:
│   └── build_type: "integration"
│   └── integrations: [sendgrid, linkedin_api]
│   └── api_endpoints: [/api/send-email, /api/connect-linkedin]
├── RunCord builds integration code
├── PR opened → human review
└── Deployed as Temporal Activity
```

---

## RunCord Integration Details

### API

RunCord exposes two endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/repositories` | List repos the API key can access |
| `POST` | `/api/v1/sessions` | Start a coding session (agent writes code, opens PR) |

**Base URL:** `https://api.runcord.com/api/v1`

**Auth:** Bearer token (`cord_sk_...`)

### Creating a Build Session

```bash
curl -X POST https://api.runcord.com/api/v1/sessions \
  -H "Authorization: Bearer $RUNCORD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "Anurag9292/ai_flywheel",
    "message": "Build a Next.js landing page with hero section, features, and waitlist form. Deploy to Vercel."
  }'
```

RunCord handles the rest:
1. Spins up a sandbox (Daytona)
2. Clones the repository
3. Runs a coding agent (Claude Code / OpenCode)
4. Agent writes code based on your message
5. Opens a PR

### Temporal Activity (The Integration)

```python
@activity.defn
async def trigger_runcord_build(prompt: str, repo: str, reference_id: str | None = None) -> dict:
    """Trigger RunCord to execute a build. Returns session info including ID for threading.
    
    The returned dict includes 'id' (session_id) which MUST be stored in workflow state
    for sending follow-up messages via trigger_runcord_fix.
    See: docs/session-threading.md
    """
    async with httpx.AsyncClient() as client:
        payload = {
            "repository": repo,
            "message": prompt,
        }
        if reference_id:
            payload["reference_id"] = reference_id
        
        response = await client.post(
            f"{settings.runcord_base_url}/sessions",
            headers={"Authorization": f"Bearer {settings.runcord_api_key}"},
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
        # Returns: {"id": "ses_...", "status": "active", "repository": "...", ...}
```

### Listing Available Repositories

```python
@activity.defn
async def list_runcord_repos() -> list[str]:
    """List repositories accessible by the RunCord API key."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.runcord_base_url}/repositories",
            headers={"Authorization": f"Bearer {settings.runcord_api_key}"},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()
```

### Verifying Your Setup

Test that your API key works:

```bash
# List accessible repositories (should return your repos)
curl https://api.runcord.com/api/v1/repositories \
  -H "Authorization: Bearer $RUNCORD_API_KEY"

# Trigger a test build
curl -X POST https://api.runcord.com/api/v1/sessions \
  -H "Authorization: Bearer $RUNCORD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "Anurag9292/ai_flywheel",
    "message": "Add a hello world test file at tests/test_hello.py that asserts True. Open a PR."
  }'
```

### Session Threading (Follow-Up Prompts)

A typical build is not a single prompt. The Builder Engine:
1. Sends an initial build prompt → creates a session
2. Waits for results (PR opened)
3. Validates the output
4. If validation fails → sends a **fix prompt to the same session**
5. Repeats until acceptance criteria pass or retries are exhausted

Without session threading, each fix prompt would spin up a **fresh sandbox** with no context — losing the agent's working state, file changes, and conversation history. Proper routing ensures:
- The agent remembers what it already built
- File system state (node_modules, build artifacts, .claude folder) persists
- The conversation context accumulates (the agent knows what failed and why)

#### Session ID

Every RunCord session has a unique identifier returned in the creation response. This is the primary key for routing follow-up messages.

```json
// POST /api/v1/sessions response
{
  "id": "ses_a1b2c3d4e5f6",
  "status": "active",
  "repository": "Anurag9292/ai_flywheel",
  "created_at": "2026-06-05T10:30:00Z"
}
```

**Rule:** Store this `id` in your workflow state. Every subsequent message to this session uses it.

#### Reference ID

An optional, caller-defined identifier you attach at session creation. Useful when you want to correlate a session with your own domain objects (venture ID, build ID, PR URL, etc.) without maintaining a separate mapping table.

```json
// POST /api/v1/sessions request
{
  "repository": "Anurag9292/ai_flywheel",
  "message": "Build a landing page...",
  "reference_id": "build_abc123"
}
```

Later, you can look up the session by reference:
```
GET /api/v1/sessions?reference_id=build_abc123
```

**When to use reference IDs:**
- You need to find a session from a webhook callback (e.g., GitHub PR event → which session opened this PR?)
- You want idempotent session creation (same reference_id = same session, not a duplicate)
- You're correlating across systems (Temporal workflow ID → RunCord session)

#### Thread Messages

Once a session exists, you send follow-up prompts to the same thread:

```
POST /api/v1/sessions/{session_id}/messages
```

```json
{
  "message": "The PR failed CI. Error: TypeError in src/index.ts line 42. Fix the type mismatch and push again."
}
```

This delivers the message to the **same sandbox, same agent, same conversation context**. The agent picks up where it left off.

#### Session Threading API Contract

**Create Session:**
```
POST /api/v1/sessions
Authorization: Bearer cord_sk_...
Content-Type: application/json
```

Request:
```json
{
  "repository": "Anurag9292/ai_flywheel",
  "message": "Build a Next.js landing page with hero, features, and waitlist form.",
  "reference_id": "build_abc123",       // optional: your correlation key
  "branch": "feature/landing-page"      // optional: target branch
}
```

Response:
```json
{
  "id": "ses_a1b2c3d4e5f6",
  "status": "active",
  "repository": "Anurag9292/ai_flywheel",
  "reference_id": "build_abc123",
  "created_at": "2026-06-05T10:30:00Z",
  "sandbox": {
    "provider": "daytona",
    "preview_url": "https://ses-a1b2c3.preview.runcord.com"
  }
}
```

**Send Follow-Up Message (Thread Continuation):**
```
POST /api/v1/sessions/{session_id}/messages
Authorization: Bearer cord_sk_...
Content-Type: application/json
```

Request:
```json
{
  "message": "Tests are failing with: AssertionError in test_waitlist.py. The form endpoint returns 404. Please fix the route handler."
}
```

Response:
```json
{
  "id": "msg_x7y8z9",
  "session_id": "ses_a1b2c3d4e5f6",
  "status": "delivered",
  "created_at": "2026-06-05T10:45:00Z"
}
```

**Get Session by Reference:**
```
GET /api/v1/sessions?reference_id=build_abc123
Authorization: Bearer cord_sk_...
```

**Get Session Status:**
```
GET /api/v1/sessions/{session_id}
Authorization: Bearer cord_sk_...
```

#### Session Lifecycle

```
┌─────────────────────────────────────────────────────┐
│                  SESSION LIFECYCLE                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│   POST /sessions ──► ACTIVE (agent working)         │
│                          │                          │
│                          ▼                          │
│                       IDLE (waiting for input)      │
│                          │                          │
│   POST /sessions/{id}/   │                          │
│     messages ──────────► ACTIVE (agent working)     │
│                          │                          │
│                          ▼                          │
│                       IDLE ◄──── (loop until done)  │
│                          │                          │
│                          ▼                          │
│                    COMPLETED / EXPIRED               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

| State | Meaning | Can Send Messages? |
|-------|---------|-------------------|
| `active` | Agent is currently processing | Yes (queued) |
| `idle` | Agent finished last task, sandbox still running | Yes (immediate) |
| `completed` | Session ended normally (agent or user closed it) | No |
| `expired` | Session timed out (default: 24h idle timeout) | No — create a new session |

**Timeouts:**
- Idle timeout: 24 hours (sandbox destroyed after this)
- Active timeout: 2 hours per message (agent killed if stuck)
- Persistent storage (`.claude`, dotfiles): survives across sessions for same repo

#### trigger_runcord_fix (Implementation)

```python
@activity.defn
async def trigger_runcord_fix(session_id: str, feedback: str) -> dict:
    """Send a fix request to an existing RunCord session.
    
    Routes the feedback to the same sandbox/agent that created the original build.
    The agent retains full context: what it built, what was attempted, file state.
    
    Args:
        session_id: The RunCord session ID from trigger_runcord_build response.
        feedback: Validation failure details — what failed and what to fix.
    
    Returns:
        Message delivery confirmation.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.runcord_base_url}/sessions/{session_id}/messages",
            headers={"Authorization": f"Bearer {settings.runcord_api_key}"},
            json={
                "message": f"The build failed validation. Please fix the following:\n\n{feedback}\n\nPush the fixes to the same branch and update the PR.",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
```

#### Workflow with Session Threading (Full Retry Loop)

```python
@workflow.defn
class BuildMVPWorkflow:
    """Orchestrates code generation via RunCord with session threading."""
    
    def __init__(self):
        self.pr_url: str | None = None
        self.session_id: str | None = None
        self.retry_count: int = 0
        self.max_retries: int = 3
    
    @workflow.run
    async def run(self, spec: BuildSpec) -> BuildResult:
        # Step 1-2: Context assembly and prompt compilation (unchanged)
        context = await workflow.execute_activity(
            assemble_build_context, args=[spec],
            start_to_close_timeout=timedelta(minutes=2),
        )
        prompt = await workflow.execute_activity(
            compile_agent_prompt, args=[context],
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        # Step 3: Create session (store the session_id for threading)
        session = await workflow.execute_activity(
            trigger_runcord_build,
            args=[prompt, spec.repo, spec.build_id],  # build_id as reference_id
            start_to_close_timeout=timedelta(minutes=5),
        )
        self.session_id = session["id"]  # ← KEY: store for follow-ups
        
        # Step 4: Wait for PR
        pr_url = await workflow.wait_condition(
            self.pr_opened,
            timeout=timedelta(hours=2),
        )
        
        # Step 5: Validate (with retry loop using same session)
        validation = await workflow.execute_activity(
            validate_build_output,
            args=[pr_url, spec.acceptance_criteria],
            start_to_close_timeout=timedelta(minutes=10),
        )
        
        while not validation.passed and self.retry_count < self.max_retries:
            self.retry_count += 1
            
            # Send fix to the SAME session (threaded)
            await workflow.execute_activity(
                trigger_runcord_fix,
                args=[self.session_id, validation.feedback],  # ← uses stored session_id
                start_to_close_timeout=timedelta(minutes=5),
            )
            
            # Wait for the agent to push fixes
            await workflow.wait_condition(
                self.pr_updated,
                timeout=timedelta(hours=1),
            )
            
            # Re-validate
            validation = await workflow.execute_activity(
                validate_build_output,
                args=[pr_url, spec.acceptance_criteria],
                start_to_close_timeout=timedelta(minutes=10),
            )
        
        if not validation.passed:
            await workflow.execute_activity(
                escalate_build_failure,
                args=[spec, pr_url, validation.feedback],
            )
            return BuildResult(status="failed", pr_url=pr_url)
        
        # Step 6-7: Merge and deploy (unchanged)
        ...
```

#### Correlating Webhooks to Sessions

When a GitHub PR webhook fires, map it back to the correct Temporal workflow:

**Strategy 1: Branch Name Convention**

```python
@webhook.handler("pull_request.opened")
async def handle_pr_opened(event: PREvent):
    branch = event.pull_request.head.ref  # "feature/build_abc123"
    build_id = branch.replace("feature/", "")
    await temporal_client.get_workflow_handle(
        workflow_id=f"build-{build_id}"
    ).signal("pr_opened", event.pull_request.html_url)
```

**Strategy 2: Reference ID Lookup**

```python
@webhook.handler("pull_request.opened")
async def handle_pr_opened(event: PREvent):
    session = await runcord_client.get_session_by_pr(event.pull_request.html_url)
    workflow_id = f"build-{session['reference_id']}"
    await temporal_client.get_workflow_handle(workflow_id).signal(
        "pr_opened", event.pull_request.html_url
    )
```

#### External Surface Bindings (Slack / Linear / GitHub)

RunCord sessions can be bound to external surfaces. When triggered via Slack (tag @Cord), the thread becomes the session's surface — any reply routes to the same session automatically.

| Trigger Source | External Surface | Follow-up Routing |
|---------------|-----------------|-------------------|
| Slack message (tag @Cord) | The Slack thread | Reply in thread → same session |
| Linear issue (tag @Cord) | The Linear issue | Comment on issue → same session |
| GitHub PR comment | The PR | Reply on PR → same session |
| API (`POST /sessions`) | None (API-only) | Must use `POST /sessions/{id}/messages` |

**For API-triggered sessions** (which is what the Builder Engine uses), there is no external surface binding. You must explicitly route via session ID.

#### Error Handling & Edge Cases

**Session Expired Mid-Build:**

```python
@activity.defn
async def trigger_runcord_fix(session_id: str, feedback: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.runcord_base_url}/sessions/{session_id}/messages",
            headers={"Authorization": f"Bearer {settings.runcord_api_key}"},
            json={"message": feedback},
            timeout=30.0,
        )
        if response.status_code == 410:  # Gone — session expired
            raise SessionExpiredError(session_id)
        response.raise_for_status()
        return response.json()
```

In the workflow, catch and recover:

```python
try:
    await workflow.execute_activity(trigger_runcord_fix, args=[self.session_id, feedback])
except SessionExpiredError:
    new_prompt = f"Continue fixing PR {pr_url}. Previous feedback:\n{feedback}"
    session = await workflow.execute_activity(
        trigger_runcord_build, args=[new_prompt, spec.repo, spec.build_id],
    )
    self.session_id = session["id"]  # Update stored session ID
```

**Idempotent Session Creation:**

If your workflow retries (Temporal activity retry), you don't want duplicate sessions. Use `reference_id`:

```python
payload = {
    "repository": repo,
    "message": prompt,
    "reference_id": f"{spec.build_id}-attempt-{attempt_number}",
}
# If a session with this reference_id exists, RunCord returns it (no duplicate)
```

**Race Condition — Message Sent While Agent is Active:**

If you send a fix message while the agent is still processing, RunCord queues it. The agent sees it when it finishes the current task. Messages are delivered in order — no special handling needed.

#### Persistent Storage vs. Session State

| Concept | Scope | Lifetime | What's Stored |
|---------|-------|----------|---------------|
| **Session state** | One session | Until session expires (24h idle) | Conversation history, sandbox filesystem, running processes |
| **Persistent storage** | Per repository | Indefinite (survives session expiry) | `.claude/` folder, dotfiles, test artifacts |

- A **new session** for the same repo starts with persistent storage intact (agent preferences, learned patterns)
- But it does **not** have the conversation history from the previous session
- If you need context from a prior session, include it in your message explicitly

### Monitoring Build Progress

After triggering a session, the Temporal workflow:
1. Receives the session response (contains session ID for threading)
2. Waits for GitHub webhook → PR opened (Temporal signal: `pr_opened`)
3. Validates the PR (tests pass, acceptance criteria met)
4. If validation fails → sends fix to same session via `POST /sessions/{id}/messages`
5. Repeats validation loop (up to 3 retries)
6. Auto-merges or requests human review

---

## Cost Model

| Build Type | Typical Cost | Time | Template Available |
|-----------|-------------|------|-------------------|
| Landing page | $2-5 | 15-30 min | Yes |
| Tracking script | $1-2 | 5-10 min | Yes |
| API endpoint | $3-8 | 20-40 min | Yes |
| Micro-MVP | $10-25 | 1-3 hours | Partial |
| Full app scaffold | $30-60 | 3-6 hours | No |

Plus RunCord sandbox cost: ~$0.40/hour of compute.

**Budget defaults by build type:**
- Landing page: $10 max
- Micro-MVP: $30 max
- Full app: $75 max (requires explicit approval)

---

## Migration Path

```
Phase 3-4: RunCord managed (Slack/Linear triggers)
           → Fastest to integrate, minimal infrastructure
           
Phase 5+:  Evaluate based on usage:
           → If <10 builds/month: stay on RunCord ($100/mo)
           → If >50 builds/month: migrate to Daytona SDK direct
           → If need tighter Temporal control: Daytona + custom agent runner

Self-host trigger: When you need:
  - Sub-second build triggers (not Slack latency)
  - Custom agent loops with mid-execution injection
  - Your own model fine-tuned for your codebase
  - Air-gapped environments
```

---

## Summary

| Aspect | Decision |
|--------|----------|
| Execution layer | RunCord (managed sandboxes) |
| Sandbox provider | Daytona (via RunCord) |
| Coding agents | Claude Code + OpenCode |
| Trigger mechanism | Slack / Linear (Phase 3), API (future) |
| Input format | Structured BuildSpec (Pydantic, never open-ended prompts) |
| Output | Git PR with passing tests |
| Session threading | Store `session_id`, route follow-ups via `POST /sessions/{id}/messages` |
| Verification | Automated (build, lint, acceptance criteria) |
| Deployment | Auto-merge + Vercel/Fly.io (or human review for sensitive builds) |
| Budget control | Per-build cost cap, escalate on exceed |
| Cost | ~$100/mo RunCord + $2-60/build (LLM) |
| Migration | Direct Daytona SDK when volume justifies |
