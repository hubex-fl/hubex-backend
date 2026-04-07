# Phase 8.7 — Org/Settings Pages (Mission Control Design)

## Context
You are working on HUBEX, an IoT device hub backend with a Vue 3 + TypeScript + Tailwind CSS frontend. Phases 8.1-8.6 established the design system, Dashboard, Devices, Entities/Groups, Alerts, and OTA pages. Now we build the Organization & Settings management pages.

## Current State
- Backend API fully implemented: `app/api/v1/orgs.py` (475 lines) with complete Org CRUD, member management, role changes
- Backend auth: `POST /api/v1/auth/switch-org` for switching active organization
- Models: Organization (name, slug, plan, max_devices, max_users), OrganizationUser (role: owner/admin/member/viewer)
- Plans: free (10 devices, 3 users), pro (100 devices, 20 users), enterprise (unlimited)
- Capabilities: org.read, org.write, org.admin, org.members.read, org.members.write
- Frontend has NO org/settings pages yet (only `SettingsAuth.vue` with raw HTML)
- Design system: 17 UI components available (UCard, UTable, UModal, UTabs, UTab, UBadge, UButton, UInput, USelect, UToggle, etc.)

## Goal
Create a comprehensive Organization & Settings page using the Mission Control design system. Two new pages: Organizations management and a revamped Settings page with tabs (Profile, Auth, Preferences).

## Requirements

### 1. Composable: `useOrganizations.ts`
- Pattern: same as `useMetrics.ts` — returns `{ orgs, members, loading, error }` with `createPoller`
- Functions: `fetchOrgs()`, `fetchMembers(orgId)`, `createOrg(data)`, `updateOrg(orgId, data)`, `deleteOrg(orgId)`, `inviteMember(orgId, email, role)`, `updateMemberRole(orgId, userId, role)`, `removeMember(orgId, userId)`, `switchOrg(orgId)`
- Use `apiFetch` from `../lib/api`
- Poll orgs list every 30s

### 2. Organizations Page (`OrganizationsPage.vue`)
- Route: `/organizations`
- **Org List Section** (UCard):
  - Show all user's orgs in a UTable (columns: Name, Slug, Plan, Members, Devices, Created)
  - Plan column: UBadge with status (free=neutral, pro=info, enterprise=ok)
  - Click row to select org and show details below
  - "Create Organization" UButton in card header
- **Selected Org Detail Section** (UCard, only shown when org selected):
  - Org info: name, slug (read-only), plan, limits
  - Edit form: name, plan (USelect) — only for admin/owner (cap: org.write)
  - Delete button — only for owner (cap: org.admin), with UModal confirmation
  - "Switch to this Org" UButton that calls switch-org and stores new token
- **Members Section** (UCard, only shown when org selected):
  - UTable with columns: Email, Role, Joined, Actions
  - Role column: UBadge (owner=ok, admin=info, member=neutral, viewer=warn)
  - Invite member: UInput (email) + USelect (role) + UButton — cap: org.members.write
  - Change role: USelect inline in table — cap: org.members.write
  - Remove member: danger UButton with confirmation — cap: org.members.write

### 3. Settings Page Revamp (`SettingsPage.vue`)
- Route: `/settings` (replaces `/settings/auth`)
- Use UTabs with 3 tabs: Profile, Auth, Preferences
- **Profile Tab**:
  - Show current user info (email from token decode)
  - Show active org name + plan badge
  - Show capabilities list as UBadge pills
- **Auth Tab**:
  - Migrate existing SettingsAuth.vue content into design system
  - Token paste field (UInput) + Save/Clear (UButton)
  - Login form: email (UInput) + password (UInput type=password) + Sign In (UButton)
  - Token status UBadge (present=ok, missing=bad)
- **Preferences Tab**:
  - Theme toggle (UToggle) for dark/light mode
  - Polling interval setting (USelect: 5s, 10s, 30s, 60s)
  - Sidebar collapsed default (UToggle)

### 4. Navigation Updates
- Add "Organizations" nav item in DefaultLayout.vue (cap: org.read)
- Rename "Auth Settings" to "Settings" and change route to `/settings`
- Icon for Organizations: building/office icon
- Icon for Settings: cog/gear icon

### 5. Visual Design
- Follow Dashboard page patterns: `space-y-6`, UCard sections, UBadge for status
- Monospace for slugs, plan names (`font-mono`)
- Success/error toasts for all mutations (useToastStore)
- Loading states: USkeleton for table rows
- Empty states: UEmpty when no orgs or no members

## Technical Constraints
- Keep `<script setup lang="ts">` pattern
- Use CSS custom properties from design system (not hardcoded colors)
- Use `apiFetch` from `../lib/api` for all API calls
- Use `hasCap` from `../lib/capabilities` for capability guards
- Use `useToastStore` for success/error feedback
- Use `createPoller` from `../lib/poller` for polling
- DO NOT modify any backend code
- DO NOT modify any existing UI components
- DO NOT create new UI components (use the 17 existing ones)
- Keep SettingsAuth.vue as-is (the new SettingsPage.vue absorbs its logic)

## Files to Create/Modify
1. **CREATE** `frontend/src/composables/useOrganizations.ts`
2. **CREATE** `frontend/src/pages/OrganizationsPage.vue`
3. **CREATE** `frontend/src/pages/SettingsPage.vue`
4. **MODIFY** `frontend/src/router.ts` — add `/organizations`, change `/settings/auth` to `/settings`
5. **MODIFY** `frontend/src/layouts/DefaultLayout.vue` — add Organizations nav, rename Auth Settings

## API Endpoints Reference
```
GET    /api/v1/orgs                              → List[OrgOut]
POST   /api/v1/orgs                              → OrgOut  {name, slug, plan?}
GET    /api/v1/orgs/{org_id}                     → OrgOut
PUT    /api/v1/orgs/{org_id}                     → OrgOut  {name?, plan?}
DELETE /api/v1/orgs/{org_id}                     → {detail}
GET    /api/v1/orgs/{org_id}/members             → List[OrgMemberOut]
POST   /api/v1/orgs/{org_id}/members             → OrgMemberOut  {email, role?}
PUT    /api/v1/orgs/{org_id}/members/{user_id}   → OrgMemberOut  {role}
DELETE /api/v1/orgs/{org_id}/members/{user_id}   → {detail}
POST   /api/v1/auth/switch-org                   → TokenOut  {org_id}
```

## OrgOut Schema
```json
{ "id": 1, "name": "My Org", "slug": "my-org", "plan": "free", "max_devices": 10, "max_users": 3, "created_at": "...", "updated_at": "..." }
```

## OrgMemberOut Schema
```json
{ "user_id": 1, "email": "user@example.com", "role": "owner", "invited_at": "...", "joined_at": "..." }
```

## Testing
After implementation:
1. Run `cd frontend && npx tsc --noEmit` to ensure no type errors
2. Verify `/organizations` page renders
3. Test: create org form works (with validation)
4. Test: org list shows in table
5. Test: clicking org shows details + members
6. Test: member invite works
7. Test: role change works
8. Test: switch org stores new token
9. Verify `/settings` page renders with 3 tabs
10. Test: auth tab login/token works same as before

## Reference
- Dashboard page for design patterns: `frontend/src/pages/DashboardPage.vue`
- Design system components: `frontend/src/components/ui/`
- API helper: `frontend/src/lib/api.ts`
- Capabilities: `frontend/src/lib/capabilities.ts`
- Toast store: `frontend/src/stores/toast.ts`
- Backend orgs API: `app/api/v1/orgs.py`
- Backend auth API: `app/api/v1/auth.py` (switch-org)
- Org models: `app/db/models/orgs.py`

## After Completion
Update `ROADMAP.md`: mark Step 7 as done `[x]`
