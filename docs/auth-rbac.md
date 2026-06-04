# Authentication & Authorization (RBAC)

Industry-standard auth architecture: **Clerk** as the Identity Provider, bridged to **Neon's Row-Level Security** via Custom JWTs.

---

## Architecture Overview

```
User → Clerk (login/OAuth/MFA) → Custom JWT with claims →
  → Next.js (verify JWT, set DB session vars) →
  → Neon Postgres (RLS reads JWT claims, enforces isolation)
```

**Clerk** handles all authentication complexity: login UI, OAuth providers (Google, GitHub, SSO), MFA, session management, organization management.

**Custom JWT claims** carry the authorization context: venture, customer, role, permissions.

**Neon RLS** reads those claims directly from the database session — no application-level filtering needed for data access.

---

## The Auth Hierarchy

```
Platform (you, the founder)
  └── Venture (IntelliBase, MatchHire, etc.)
       └── Customer / Organization (Acme Corp, Globex, etc.)
            └── User (Alice, Bob, etc.)
                 └── Role (org_admin, user, candidate, etc.)
```

---

## Custom JWT Claims

Clerk issues JWTs with custom claims that encode the full authorization context:

```json
{
  "sub": "user_abc123",
  "email": "alice@acme.com",
  "org_id": "org_acme",
  "org_role": "org:admin",
  "metadata": {
    "venture_id": "intellibase",
    "customer_id": "acme_corp",
    "role": "org_admin",
    "permissions": ["sources:*", "knowledge:*", "team:*", "analytics:*", "settings:*"]
  }
}
```

Clerk's **Organizations** feature maps directly to your customers:
- Each customer (Acme Corp) = a Clerk Organization
- Each user's role within that org = their app role
- Clerk handles invites, role assignment, and member management UI

---

## Neon RLS Integration

JWT claims are set as Postgres session variables, and RLS policies read them directly:

```sql
-- Set session variables from JWT (done by the connection middleware)
SET request.jwt.claims.venture_id = 'intellibase';
SET request.jwt.claims.customer_id = 'acme_corp';
SET request.jwt.claims.user_id = 'user_abc123';
SET request.jwt.claims.role = 'org_admin';

-- RLS policies read these directly
ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY venture_isolation ON knowledge_chunks
  USING (venture_id = current_setting('request.jwt.claims.venture_id')::text);

CREATE POLICY customer_isolation ON knowledge_chunks
  USING (customer_id = current_setting('request.jwt.claims.customer_id')::text);

-- Combined policy (both must match)
CREATE POLICY full_isolation ON knowledge_chunks
  USING (
    venture_id = current_setting('request.jwt.claims.venture_id')::text
    AND customer_id = current_setting('request.jwt.claims.customer_id')::text
  );
```

**Result:** No application code can bypass isolation. Even LLM-generated queries, raw SQL, or RAG retrieval are automatically scoped to the correct venture + customer.

---

## Three Levels of Roles

### Level 1: Platform Roles (You + Your Team)

| Role | Access | Who |
|------|--------|-----|
| `platform_owner` | Everything — all ventures, all configs, all data | You |
| `platform_admin` | Full access to assigned ventures | Co-founder, technical partner |
| `platform_viewer` | Read-only dashboards and metrics | Advisor, investor |

These are managed in Clerk as a special "platform" organization.

### Level 2: Venture Management Roles

| Role | Access | Who |
|------|--------|-----|
| `venture_owner` | Full control of this venture | You (always) |
| `venture_admin` | Manage agents, prompts, experiments, configs | Technical collaborator |
| `venture_ops` | Monitor, handle approval queues, escalations | Ops person |

### Level 3: App Roles (Per-Venture, Customer-Facing)

Each venture defines its own roles. These are configured when setting up the venture:

**IntelliBase:**
```yaml
roles:
  org_admin:
    display_name: "Admin"
    permissions: ["sources:*", "knowledge:*", "team:*", "analytics:*", "settings:*", "billing:*"]
  org_manager:
    display_name: "Manager"
    permissions: ["knowledge:read", "knowledge:feedback", "team:read", "team:invite", "analytics:read"]
  org_user:
    display_name: "User"
    permissions: ["knowledge:read", "knowledge:feedback", "history:own", "profile:own"]
    is_default: true
```

**MatchHire:**
```yaml
roles:
  employer_admin:
    display_name: "Employer Admin"
    permissions: ["jobs:*", "candidates:*", "team:*", "analytics:*", "settings:*", "billing:*"]
  hiring_manager:
    display_name: "Hiring Manager"
    permissions: ["jobs:read", "candidates:read", "candidates:review", "interviews:*", "analytics:own_jobs"]
  candidate:
    display_name: "Candidate"
    permissions: ["jobs:browse", "applications:create", "applications:own", "profile:own", "messages:own"]
```

---

## Permission Model

Permissions follow `resource:action` format with wildcard support:

```yaml
# Pattern: "resource:action"
# Wildcard: "resource:*" = all actions on that resource
# Own-scoped: "resource:own" = only records belonging to this user

examples:
  "jobs:*"              # Create, read, update, delete any job
  "jobs:read"           # Read any job
  "candidates:own"      # Only see candidates for your own jobs
  "knowledge:read"      # Query the knowledge base
  "knowledge:feedback"  # Submit feedback on answers
  "settings:*"          # Full access to settings
  "billing:*"           # Manage billing
  "team:invite"         # Invite new team members
  "analytics:read"      # View analytics
  "history:own"         # Only your own history
```

### Permission Check in Code

```python
# FastAPI dependency that checks permissions
def require_permission(permission: str):
    async def check(request: Request):
        user_permissions = request.state.jwt_claims.get("permissions", [])
        if not matches_permission(user_permissions, permission):
            raise HTTPException(403, f"Missing permission: {permission}")
    return Depends(check)

# Usage
@router.post("/jobs")
async def create_job(
    data: JobCreate,
    _auth = require_permission("jobs:create"),
    db: AsyncSession = Depends(get_session),
):
    # RLS already scopes to correct venture + customer
    # Permission check ensures user has "jobs:create" role
    ...
```

---

## Request Flow (End to End)

```
1. User opens IntelliBase app
     │
2. Clerk handles login (OAuth, email, SSO)
     │ → Issues JWT with custom claims
     │
3. Next.js receives request with JWT
     │ → Verifies with Clerk SDK (middleware)
     │ → Extracts claims: venture_id, customer_id, role, permissions
     │
4. Next.js API route / Server Component calls FastAPI backend
     │ → Passes JWT or extracted claims
     │
5. FastAPI middleware:
     │ → Verifies JWT signature
     │ → Sets Postgres session variables from claims
     │ → Attaches permissions to request context
     │
6. Route handler executes
     │ → Permission decorator checks action permission
     │ → Database query executes with RLS active
     │ → Results automatically scoped to venture + customer
     │
7. If route triggers an agent:
     │ → Agent inherits user's context (venture_id, customer_id)
     │ → Policy Engine checks what agent can do for this user's role
     │ → Agent's DB queries also scoped by RLS
     │
8. Response returned (only data this user should see)
```

---

## Clerk Configuration

### Organizations = Customers

```typescript
// When a new company signs up for IntelliBase:
const org = await clerk.organizations.create({
  name: "Acme Corp",
  publicMetadata: {
    venture_id: "intellibase",
    customer_id: "acme_corp",
    plan: "pro",
  },
});

// Invite a user to the organization with a role:
await clerk.organizations.createMembership({
  organizationId: org.id,
  userId: user.id,
  role: "org:admin",  // Maps to your org_admin role
});
```

### Custom JWT Template (in Clerk Dashboard)

```json
{
  "venture_id": "{{org.publicMetadata.venture_id}}",
  "customer_id": "{{org.publicMetadata.customer_id}}",
  "role": "{{org.membership.role}}",
  "permissions": "{{org.membership.permissions}}"
}
```

### Next.js Middleware

```typescript
import { clerkMiddleware, getAuth } from '@clerk/nextjs/server';

export default clerkMiddleware(async (auth, req) => {
  const { userId, orgId, orgRole, sessionClaims } = await auth();
  
  if (!userId) {
    return redirectToSignIn();
  }
  
  // Claims are now available throughout the request
  // sessionClaims.venture_id, sessionClaims.customer_id, etc.
});
```

---

## Database Schema for RBAC

```sql
-- Role definitions (per venture)
CREATE TABLE roles (
  id TEXT PRIMARY KEY,
  venture_id TEXT NOT NULL,
  name TEXT NOT NULL,
  display_name TEXT,
  permissions JSONB NOT NULL DEFAULT '[]',
  is_default BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(venture_id, name)
);

-- RLS: only see roles for your venture
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY roles_venture_isolation ON roles
  USING (venture_id = current_setting('request.jwt.claims.venture_id')::text);

-- API keys (for programmatic access — e.g., customer integrations)
CREATE TABLE api_keys (
  id TEXT PRIMARY KEY,
  venture_id TEXT NOT NULL,
  customer_id TEXT NOT NULL,
  key_hash TEXT NOT NULL,
  name TEXT,
  permissions JSONB DEFAULT '[]',
  last_used_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auth audit log
CREATE TABLE auth_events (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  event_type TEXT NOT NULL,  -- "login", "permission_denied", "role_changed", "api_key_used"
  venture_id TEXT,
  customer_id TEXT,
  metadata JSONB DEFAULT '{}',
  ip_address TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Agent Auth (Policy Engine Integration)

When a user triggers an agent, the agent operates within the user's permission scope:

```yaml
agent_execution_context:
  triggered_by: user_alice
  role: org_user
  venture: intellibase
  customer: acme_corp
  
  agent_can:
    - query knowledge base (user has "knowledge:read")
    - return answers with citations
    - record feedback (user has "knowledge:feedback")
    
  agent_cannot:
    - access other customers' data (RLS prevents)
    - modify knowledge base (user lacks "knowledge:write")
    - access billing (user lacks "billing:*")
    - connect new data sources (user lacks "sources:*")
    
  enforced_by:
    - RLS: data-level isolation (DB layer)
    - Permission check: action-level control (API layer)
    - Policy Engine: agent behavior constraints (agent layer)
```

---

## Multi-Tenancy Summary

| Layer | Mechanism | What it prevents |
|-------|-----------|-----------------|
| **Authentication** | Clerk (JWT) | Unauthorized access |
| **Venture isolation** | RLS on `venture_id` | Cross-venture data leakage |
| **Customer isolation** | RLS on `customer_id` | Cross-customer data leakage within a venture |
| **Role permissions** | JWT claims + middleware | Users doing actions beyond their role |
| **Agent constraints** | Policy Engine | Agents exceeding user's permission scope |
| **API key scoping** | Permissions field on key | Programmatic access limited to declared scope |

---

## Cost

| Component | Cost |
|-----------|------|
| Clerk (auth) | Free up to 10K MAU, then $0.02/MAU |
| Custom JWT claims | Included in Clerk |
| Neon RLS | No additional cost (Postgres feature) |
| RBAC logic | Custom code (no external service) |

For early stage (< 1000 users across all ventures): **$0 additional cost** (Clerk free tier).
