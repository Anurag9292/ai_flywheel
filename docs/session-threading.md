# Session Threading & Routing

How RunCord sessions maintain continuity across multiple prompts — ensuring follow-up messages, fix requests, and iterative builds all land in the same working thread.

---

## Why This Matters

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

---

## Core Concepts

### Session ID

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

### Reference ID

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

### Thread Messages

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

---

## API Contract

### Create Session

```
POST /api/v1/sessions
Authorization: Bearer cord_sk_...
Content-Type: application/json
```

**Request:**
```json
{
  "repository": "Anurag9292/ai_flywheel",
  "message": "Build a Next.js landing page with hero, features, and waitlist form.",
  "reference_id": "build_abc123",       // optional: your correlation key
  "branch": "feature/landing-page"      // optional: target branch
}
```

**Response:**
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

### Send Follow-Up Message (Thread Continuation)

```
POST /api/v1/sessions/{session_id}/messages
Authorization: Bearer cord_sk_...
Content-Type: application/json
```

**Request:**
```json
{
  "message": "Tests are failing with: AssertionError in test_waitlist.py. The form endpoint returns 404. Please fix the route handler."
}
```

**Response:**
```json
{
  "id": "msg_x7y8z9",
  "session_id": "ses_a1b2c3d4e5f6",
  "status": "delivered",
  "created_at": "2026-06-05T10:45:00Z"
}
```

### Get Session by Reference

```
GET /api/v1/sessions?reference_id=build_abc123
Authorization: Bearer cord_sk_...
```

**Response:**
```json
{
  "sessions": [
    {
      "id": "ses_a1b2c3d4e5f6",
      "status": "active",
      "reference_id": "build_abc123",
      "repository": "Anurag9292/ai_flywheel",
      "created_at": "2026-06-05T10:30:00Z"
    }
  ]
}
```

### Get Session Status

```
GET /api/v1/sessions/{session_id}
Authorization: Bearer cord_sk_...
```

**Response:**
```json
{
  "id": "ses_a1b2c3d4e5f6",
  "status": "idle",
  "repository": "Anurag9292/ai_flywheel",
  "reference_id": "build_abc123",
  "created_at": "2026-06-05T10:30:00Z",
  "last_activity_at": "2026-06-05T10:42:00Z",
  "message_count": 3,
  "sandbox": {
    "provider": "daytona",
    "preview_url": "https://ses-a1b2c3.preview.runcord.com",
    "status": "running"
  }
}
```

---

## Session Lifecycle

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

**States:**
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

---

## Implementation: Temporal Activities

### trigger_runcord_build (Updated)

```python
@activity.defn
async def trigger_runcord_build(prompt: str, repo: str, reference_id: str | None = None) -> dict:
    """Create a new RunCord session. Returns session info including ID for threading."""
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
        # Returns: {"id": "ses_...", "status": "active", ...}
```

### trigger_runcord_fix (Now Defined)

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

### Workflow Integration (Updated)

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
            # Exhausted retries, escalate to human
            await workflow.execute_activity(
                escalate_build_failure,
                args=[spec, pr_url, validation.feedback],
            )
            return BuildResult(status="failed", pr_url=pr_url)
        
        # Step 6-7: Merge and deploy (unchanged)
        ...
```

---

## Correlating Webhooks to Sessions

When a GitHub PR webhook fires, you need to map it back to the correct Temporal workflow. Two strategies:

### Strategy 1: Branch Name Convention

The BuildSpec dictates the branch name (`feature/{build_id}`). When the webhook fires:

```python
@webhook.handler("pull_request.opened")
async def handle_pr_opened(event: PREvent):
    # Extract build_id from branch name
    branch = event.pull_request.head.ref  # "feature/build_abc123"
    build_id = branch.replace("feature/", "")
    
    # Signal the waiting Temporal workflow
    await temporal_client.get_workflow_handle(
        workflow_id=f"build-{build_id}"
    ).signal("pr_opened", event.pull_request.html_url)
```

### Strategy 2: Reference ID Lookup

If the branch name isn't deterministic, use the reference_id:

```python
@webhook.handler("pull_request.opened")
async def handle_pr_opened(event: PREvent):
    # Ask RunCord which session opened this PR
    # (RunCord tracks which session opened which PR)
    session = await runcord_client.get_session_by_pr(event.pull_request.html_url)
    
    # Use the reference_id we set at creation to find the workflow
    workflow_id = f"build-{session['reference_id']}"
    await temporal_client.get_workflow_handle(workflow_id).signal(
        "pr_opened", event.pull_request.html_url
    )
```

---

## External Surface Bindings (Slack / Linear / GitHub)

RunCord sessions can be bound to external surfaces. When a session is triggered via Slack (tag @Cord), the Slack thread becomes the session's external surface. Any reply in that thread routes to the same session automatically.

| Trigger Source | External Surface | Follow-up Routing |
|---------------|-----------------|-------------------|
| Slack message (tag @Cord) | The Slack thread | Reply in thread → same session |
| Linear issue (tag @Cord) | The Linear issue | Comment on issue → same session |
| GitHub PR comment | The PR | Reply on PR → same session |
| API (`POST /sessions`) | None (API-only) | Must use `POST /sessions/{id}/messages` |

**For API-triggered sessions** (which is what the Builder Engine uses), there is no external surface binding. You must explicitly route via session ID.

---

## Error Handling & Edge Cases

### Session Expired Mid-Build

If the session expires (24h idle) before you send a fix:

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

In the workflow, catch this and create a new session with context:

```python
try:
    await workflow.execute_activity(trigger_runcord_fix, args=[self.session_id, feedback])
except SessionExpiredError:
    # Create a fresh session, but include the PR URL for context
    new_prompt = f"Continue fixing PR {pr_url}. Previous feedback:\n{feedback}"
    session = await workflow.execute_activity(
        trigger_runcord_build,
        args=[new_prompt, spec.repo, spec.build_id],
    )
    self.session_id = session["id"]  # Update stored session ID
```

### Idempotent Session Creation

If your workflow retries (Temporal activity retry), you don't want duplicate sessions. Use `reference_id` for idempotency:

```python
# If a session with this reference_id already exists, RunCord returns it
# instead of creating a duplicate
payload = {
    "repository": repo,
    "message": prompt,
    "reference_id": f"{spec.build_id}-attempt-{attempt_number}",
}
```

### Race Condition: Message Sent While Agent is Active

If you send a fix message while the agent is still processing the previous one, RunCord queues it. The agent will see it when it finishes the current task. No special handling needed — messages are delivered in order.

---

## Persistent Storage vs. Session State

These are different concepts:

| Concept | Scope | Lifetime | What's Stored |
|---------|-------|----------|---------------|
| **Session state** | One session | Until session expires (24h idle) | Conversation history, sandbox filesystem, running processes |
| **Persistent storage** | Per repository | Indefinite (survives session expiry) | `.claude/` folder, dotfiles, test artifacts |

This means:
- A **new session** for the same repo starts with persistent storage intact (agent preferences, learned patterns)
- But it does **not** have the conversation history from the previous session
- If you need context from a prior session, include it in your message explicitly

---

## Summary

| Concern | Solution |
|---------|----------|
| Route fix to same agent | `POST /sessions/{session_id}/messages` |
| Correlate session to workflow | Store `session_id` in workflow state + use `reference_id` |
| Map webhook to workflow | Branch name convention or reference_id lookup |
| Handle expired sessions | Catch 410, create new session with context |
| Prevent duplicate sessions | Use `reference_id` for idempotency |
| External surface routing | Automatic for Slack/Linear/GitHub triggers; manual for API |
| Persistent context across sessions | `.claude/` folder persists per-repo; conversation does not |
