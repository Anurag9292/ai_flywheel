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
            # Retry with feedback
            await workflow.execute_activity(
                trigger_runcord_fix,
                args=[pr_url, validation.feedback],
                start_to_close_timeout=timedelta(minutes=5),
            )
            # Wait again...
        
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

### Triggering a Build

**Option A: Slack trigger (simplest)**
```
Module 18 posts to Slack channel where Cord is tagged:

"@cord Build a Next.js landing page for [venture name].
 Repo: github.com/user/venture-landing
 Branch: feature/build-001
 [full compiled prompt attached as thread]"
```

**Option B: Linear ticket (structured)**
```
Module 18 creates a Linear issue assigned to Cord:

Title: "Build: landing page for AI Finance Coach"
Description: [compiled prompt]
Labels: ["build", "auto-merge"]
```

**Option C: API (when available)**
```python
# Direct API integration (future — check RunCord docs for API access)
await runcord_client.create_session(
    repo="github.com/user/venture-landing",
    prompt=compiled_prompt,
    agent="claude-code",
    branch=f"feature/{build_id}",
)
```

### Monitoring Build Progress

The Temporal workflow sleeps after triggering, then wakes on:
- **GitHub webhook** → PR opened (signal: `pr_opened`)
- **Timeout** → 2 hours max (escalate if exceeded)
- **RunCord notification** → build failed (signal: `build_failed`)

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
| Verification | Automated (build, lint, acceptance criteria) |
| Deployment | Auto-merge + Vercel/Fly.io (or human review for sensitive builds) |
| Budget control | Per-build cost cap, escalate on exceed |
| Cost | ~$100/mo RunCord + $2-60/build (LLM) |
| Migration | Direct Daytona SDK when volume justifies |
