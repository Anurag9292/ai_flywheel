# Temporal Patterns & Frontend Integration

How workflows, agents, and the Next.js UI work together through Temporal.io. Covers the critical implementation patterns for durable multi-agent execution with human-in-the-loop.

---

## The Three Temporal Realities

### 1. The Determinism Trap (The Golden Rule)

Temporal replays event history to reconstruct state after a crash. This means **Workflow code must be 100% deterministic** — given the same inputs and history, it must produce the same execution path.

**The Risk:** AI generation is inherently non-deterministic. Even `temperature=0` doesn't guarantee identical outputs across API calls. Latency varies. Providers update models silently.

**The Rule:** Never place these inside a Workflow function:
- LLM calls
- API requests
- `datetime.now()` or random number generation
- File I/O
- Any external system call

**All non-deterministic operations must be isolated in Activities.**

```python
# ❌ WRONG — non-deterministic code in Workflow
@workflow.defn
class ScreeningWorkflow:
    @workflow.run
    async def run(self, candidate, job):
        # This breaks replay determinism!
        result = await llm_gateway.complete(messages=[...])
        return result

# ✓ CORRECT — non-deterministic code in Activity
@activity.defn
async def screen_candidate(candidate, job) -> ScreeningResult:
    # Activities are NOT replayed — they run once, result is stored
    result = await llm_gateway.complete(messages=[...])
    return result

@workflow.defn
class ScreeningWorkflow:
    @workflow.run
    async def run(self, candidate, job):
        # Workflow just orchestrates — deterministic
        result = await workflow.execute_activity(
            screen_candidate,
            args=[candidate, job],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        return result
```

**Mental model:** The Workflow is the **rigid conductor** — it decides WHAT runs in WHAT order. Activities are the **musicians** — they do the actual work (LLM calls, API requests, DB writes).

---

### 2. Cost-Aware Idempotency

Temporal aggressively retries failing Activities. Consider this scenario:

```
Activity starts → LLM call succeeds ($0.03) → DB write fails → Activity throws →
Temporal retries Activity → LLM call runs AGAIN ($0.03) → DB write succeeds
```

You just paid for the LLM call twice. At scale, this compounds.

**The Fix:** Cache LLM responses keyed by Temporal Activity ID.

```python
@activity.defn
async def screen_candidate(candidate, job) -> ScreeningResult:
    # Use Temporal's activity info for idempotency key
    activity_id = activity.info().activity_id
    
    # LLM Gateway checks cache first
    result = await llm_gateway.complete(
        messages=[...],
        idempotency_key=activity_id,  # If retried, return cached response
    )
    
    # Even if this write fails and Activity retries,
    # the LLM call won't be re-executed (cache hit)
    await db.save_screening_result(result)
    return result
```

**LLM Gateway (Module 7) implementation:**

```python
async def complete(self, request: LLMRequest, idempotency_key: str = None) -> LLMResponse:
    # Check idempotency cache (Redis, keyed by activity ID)
    if idempotency_key:
        cached = await self._cache.get(f"idem:{idempotency_key}")
        if cached:
            return cached  # Return cached response, don't call LLM again
    
    # Make the actual call
    response = await self._call_llm(request)
    
    # Cache for idempotency (TTL: 24 hours)
    if idempotency_key:
        await self._cache.set(f"idem:{idempotency_key}", response, ttl=86400)
    
    return response
```

---

### 3. The "Sleep" Superpower

For validation pipelines, A/B tests, and campaigns that run over days/weeks:

```python
@workflow.defn
class ValidationPipeline:
    @workflow.run
    async def run(self, config: ValidationConfig):
        # Rung 4: Launch ad campaign
        campaign = await workflow.execute_activity(
            launch_ad_campaign, args=[config.ad_config],
            start_to_close_timeout=timedelta(minutes=5),
        )
        
        # Sleep for 14 days while campaign runs
        # Temporal unloads workflow from memory entirely
        # Zero compute cost during sleep
        # Wakes up the exact millisecond the timer fires
        await workflow.sleep(timedelta(days=14))
        
        # Evaluate campaign results
        results = await workflow.execute_activity(
            evaluate_campaign, args=[campaign.id],
            start_to_close_timeout=timedelta(minutes=5),
        )
        
        # Make decision
        if results.cpa < config.target_cpa:
            return ValidationResult(status="pass", results=results)
        else:
            return ValidationResult(status="fail", results=results)
```

**What happens during sleep:**
- Workflow is unloaded from memory (zero RAM usage)
- Timer stored in Temporal's database
- No worker resources consumed
- When timer fires: workflow loaded back, execution continues from exact point

This means you can have **thousands** of sleeping validation pipelines simultaneously with negligible infrastructure cost.

---

## Frontend ↔ Temporal Architecture

### The Core Challenge

Temporal workflows can be:
- **Active** (seconds) — show real-time progress
- **Paused** (hours/days) — waiting for human signal, needs notification + action
- **Sleeping** (days/weeks) — show countdown, no active connection needed

The Next.js frontend cannot hold a WebSocket open for 14 days. The UI must handle all three states gracefully.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  TEMPORAL WORKFLOWS                                          │
│                                                              │
│  workflow executes ──┐                                       │
│  workflow pauses  ───┤── emits events ──┐                   │
│  workflow sleeps  ───┤                  │                   │
│  workflow wakes   ───┘                  │                   │
└─────────────────────────────────────────┼───────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────┐
│  EVENT BUS (bridges Temporal → Channels)                     │
│                                                              │
│  ├── If user on page → SSE stream → real-time UI update    │
│  ├── If action needed → Slack push notification             │
│  ├── If action needed → Browser push notification           │
│  └── Always → DB status update (for dashboard queries)      │
└─────────────────────────────────────────────────────────────┘
                                          │
              ┌───────────────────────────┼──────────────────┐
              ▼                           ▼                  ▼
┌──────────────────┐  ┌──────────────────────┐  ┌──────────────┐
│  SLACK           │  │  NEXT.JS WEB APP     │  │  CLI         │
│                  │  │                      │  │              │
│  "Campaign done" │  │  Dashboard (polling) │  │  flywheel    │
│  "Approve?" [Y/N]│  │  Progress (SSE)      │  │   status     │
│                  │  │  Approval queue      │  │   approve    │
│  User clicks ────┼──┼─▶ Temporal signal    │  │              │
└──────────────────┘  │  Agent stream (AI SDK)│  └──────────────┘
                      └──────────────────────┘
```

### Three UI Modes

| Workflow State | Frontend Pattern | Connection | Example |
|---------------|-----------------|------------|---------|
| **Active** (running) | Server-Sent Events (SSE) | Persistent stream while on page | Agent generating JD, showing tokens live |
| **Paused** (needs human) | Push notification + REST action | No persistent connection | "Approve this campaign?" button |
| **Sleeping** (timer) | Static render on page load | No connection | "A/B test running. Wakes June 17th." |

---

### Pattern 1: Real-Time Progress (SSE)

For workflows actively executing (agent running, pipeline processing):

```typescript
// Next.js API Route: /api/workflows/[id]/stream
// Bridges Event Bus → SSE → Browser

export async function GET(req: Request, { params }: { params: { id: string } }) {
  const encoder = new TextEncoder();
  
  const stream = new ReadableStream({
    async start(controller) {
      // Subscribe to this workflow's events
      const unsubscribe = eventBus.subscribe(
        `workflow.${params.id}.*`,
        (event) => {
          const data = `data: ${JSON.stringify(event)}\n\n`;
          controller.enqueue(encoder.encode(data));
        }
      );
      
      // Cleanup on disconnect
      req.signal.addEventListener('abort', () => {
        unsubscribe();
        controller.close();
      });
    }
  });
  
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    }
  });
}
```

```typescript
// Client component: shows real-time workflow steps
'use client';

function WorkflowProgress({ workflowId }: { workflowId: string }) {
  const [steps, setSteps] = useState<WorkflowEvent[]>([]);
  const [status, setStatus] = useState<'running' | 'paused' | 'done'>('running');
  
  useEffect(() => {
    const source = new EventSource(`/api/workflows/${workflowId}/stream`);
    
    source.onmessage = (e) => {
      const event = JSON.parse(e.data);
      setSteps(prev => [...prev, event]);
      
      if (event.type === 'workflow.paused') setStatus('paused');
      if (event.type === 'workflow.completed') {
        setStatus('done');
        source.close();
      }
    };
    
    return () => source.close();
  }, [workflowId]);
  
  return (
    <div>
      {steps.map(step => <StepIndicator key={step.id} step={step} />)}
      {status === 'running' && <Spinner />}
      {status === 'paused' && <ApprovalPrompt workflowId={workflowId} />}
      {status === 'done' && <CompletedBadge />}
    </div>
  );
}
```

---

### Pattern 2: Approval Actions (REST + Optimistic UI)

When a workflow pauses for human input:

```typescript
// Approval component with optimistic update
function ApprovalQueue() {
  const { data: approvals } = useQuery({
    queryKey: ['approvals'],
    queryFn: fetchPendingApprovals,
    refetchInterval: 30000, // Poll every 30s for new approvals
  });
  
  const approveMutation = useMutation({
    mutationFn: async ({ workflowId, decision }) => {
      await fetch(`/api/workflows/${workflowId}/signal`, {
        method: 'POST',
        body: JSON.stringify({ 
          signal: 'human_decision', 
          payload: { decision } 
        }),
      });
    },
    // Optimistic update: remove from queue immediately
    onMutate: ({ workflowId }) => {
      queryClient.setQueryData(['approvals'], (old) =>
        old.filter(a => a.workflowId !== workflowId)
      );
    },
    // Reconcile with server after
    onSettled: () => queryClient.invalidateQueries(['approvals']),
  });
  
  return (
    <div>
      {approvals?.map(item => (
        <ApprovalCard
          key={item.workflowId}
          item={item}
          onApprove={() => approveMutation.mutate({ 
            workflowId: item.workflowId, decision: 'approve' 
          })}
          onReject={() => approveMutation.mutate({ 
            workflowId: item.workflowId, decision: 'reject' 
          })}
        />
      ))}
    </div>
  );
}
```

```python
# Backend: Next.js API route sends signal to Temporal
# /api/workflows/[id]/signal

@app.post("/api/workflows/{workflow_id}/signal")
async def send_signal(workflow_id: str, body: SignalRequest):
    handle = temporal_client.get_workflow_handle(workflow_id)
    await handle.signal("human_decision", body.payload)
    return {"status": "signal_sent"}
```

---

### Pattern 3: Streaming Agent Output (Vercel AI SDK)

When an agent is generating text (JD, outreach email, interview guide):

```typescript
'use client';
import { useChat } from 'ai/react';

function JDOptimizer({ jobBrief }: { jobBrief: string }) {
  const { messages, isLoading, error } = useChat({
    api: '/api/agents/jd-optimizer/stream',
    body: { brief: jobBrief },
  });
  
  return (
    <div>
      {messages.map(m => (
        <div key={m.id}>
          {m.role === 'assistant' && (
            <JDPreview content={m.content} isStreaming={isLoading} />
          )}
        </div>
      ))}
      {isLoading && <TypingIndicator />}
    </div>
  );
}
```

```typescript
// Next.js API Route: /api/agents/jd-optimizer/stream
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';

export async function POST(req: Request) {
  const { brief } = await req.json();
  
  const result = await streamText({
    model: openai('gpt-4o-mini'),
    system: `You generate structured job descriptions...`,
    prompt: brief,
  });
  
  return result.toDataStreamResponse();
}
```

---

### Pattern 4: Sleeping Workflow Status (Static + Countdown)

No active connection needed. Just render state on page load:

```typescript
// Server Component (fetches once on page load)
async function WorkflowStatus({ workflowId }: { workflowId: string }) {
  const workflow = await fetchWorkflowState(workflowId);
  
  if (workflow.status === 'sleeping') {
    return (
      <Card>
        <Badge variant="sleeping">Sleeping</Badge>
        <p>{workflow.description}</p>
        <p>Wakes: {format(workflow.sleepUntil, 'PPP')}</p>
        <Progress 
          value={percentElapsed(workflow.sleepStarted, workflow.sleepUntil)} 
        />
        <p className="text-muted">
          No compute resources used while sleeping.
        </p>
      </Card>
    );
  }
  
  // ... other states
}
```

---

### Pattern 5: Dashboard Overview (Smart Polling)

```typescript
function VentureDashboard({ ventureId }: { ventureId: string }) {
  const { data } = useQuery({
    queryKey: ['venture-workflows', ventureId],
    queryFn: () => fetchVentureWorkflows(ventureId),
    // Smart polling: frequent when active workflows exist, rare otherwise
    refetchInterval: (query) => {
      const hasActive = query.data?.some(
        w => w.status === 'RUNNING' || w.status === 'PAUSED'
      );
      if (hasActive) return 5000;   // 5s when things are happening
      return 60000;                  // 60s when everything is idle/sleeping
    },
  });
  
  return (
    <div>
      <section>
        <h3>Needs Your Attention ({data?.paused.length})</h3>
        {data?.paused.map(w => <ApprovalCard key={w.id} workflow={w} />)}
      </section>
      
      <section>
        <h3>Running Now ({data?.active.length})</h3>
        {data?.active.map(w => <ActiveWorkflowRow key={w.id} workflow={w} />)}
      </section>
      
      <section>
        <h3>Sleeping ({data?.sleeping.length})</h3>
        {data?.sleeping.map(w => <SleepingWorkflowRow key={w.id} workflow={w} />)}
      </section>
    </div>
  );
}
```

---

## Dev Environment

For local development, Temporal is lightweight:

```bash
# One command — runs in-memory, no Docker needed for basic dev
temporal server start-dev

# Or in docker-compose.yml for full environment:
services:
  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"   # gRPC
      - "8233:8233"   # UI
    environment:
      - DB=postgres
      - DB_PORT=5432
      - POSTGRES_USER=temporal
      - POSTGRES_PWD=temporal
```

Access Temporal UI at `localhost:8233` — shows all workflows, their state, history, and allows manual signal injection (useful for testing human-in-the-loop flows without building UI first).

---

## Summary: The Full Picture

```
User Action (Next.js)
     │
     ├── "Start validation" → POST /api/ventures/:id/validate
     │                          → starts Temporal workflow
     │                          → returns workflow_id
     │                          → UI subscribes to SSE for progress
     │
     ├── "Approve campaign"  → POST /api/workflows/:id/signal
     │                          → sends signal to paused workflow
     │                          → workflow resumes, continues execution
     │                          → UI shows progress via SSE
     │
     └── "Check status"      → GET /api/workflows/:id/status
                                → queries Temporal for current state
                                → returns: running/paused/sleeping/done
                                → UI renders appropriate view
```

Every interaction follows the same pattern:
1. **Start** something → Temporal workflow begins
2. **Stream** progress → SSE while active
3. **Notify** when human needed → Slack + browser push + approval queue
4. **Signal** when human decides → REST → Temporal signal → workflow resumes
5. **Sleep** when waiting → no resources, countdown in UI
6. **Complete** → final state rendered, metrics recorded

---

## Pattern: Embedding Model Migration

When upgrading to a better/cheaper embedding model, a Temporal workflow handles the migration:

```python
@workflow.defn
class EmbeddingMigrationWorkflow:
    """Gradually re-embeds all documents from old model to new model."""
    
    @workflow.run
    async def run(self, old_collection_id: str, new_model_config: dict):
        # 1. Create new collection (new model, new dimensions)
        new_collection = await workflow.execute_activity(
            create_collection, args=[new_model_config],
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        # 2. Re-embed in batches (can take days for large collections)
        total = await workflow.execute_activity(
            count_documents, args=[old_collection_id]
        )
        
        for offset in range(0, total, 100):
            await workflow.execute_activity(
                re_embed_batch,
                args=[old_collection_id, new_collection.id, offset, 100],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            # Rate limit: don't overwhelm the embedding API
            await workflow.sleep(timedelta(seconds=2))
        
        # 3. Activate new collection (queries now route here)
        await workflow.execute_activity(
            activate_collection, args=[new_collection.id]
        )
        
        # 4. Deprecate old (keep 30 days for rollback)
        await workflow.execute_activity(
            deprecate_collection, args=[old_collection_id]
        )
```

Key properties:
- **Zero downtime** — queries served from v1 until v2 is fully populated
- **Cost-controlled** — batches with sleep intervals prevent API cost spikes
- **Resumable** — if worker dies mid-migration, Temporal resumes from last completed batch
- **Rollbackable** — old collection kept for 30 days, can reactivate instantly
