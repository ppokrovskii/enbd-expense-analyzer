# Frontend Design

**Framework**: Next.js 14 (App Router)  
**UI**: TailwindCSS + shadcn/ui  
**State**: SWR

---

## Structure

```
app/
  (auth)/login, callback/         # Auth0
  (dashboard)/
    dashboard/                    # Overview
    transactions/                 # List, import
    categories/                   # Rules
    chat/                         # AI chat
    reports/                      # Generate, download
    settings/                     # LLM model
components/
  person-switcher.tsx             # Header dropdown
  transaction-table.tsx
  chat-interface.tsx
hooks/
  use-auth.ts                     # Auth0
  use-person.ts                   # Active person + switch
  use-transactions.ts             # SWR
  use-notifications.ts            # WebSocket
```

---

## Key Features

**Auth0**
```typescript
import { Auth0Client } from '@auth0/auth0-spa-js';
await auth0.loginWithRedirect();
const token = await auth0.getTokenSilently();
```

**Person Switcher**
```typescript
<Select value={activePerson.id} onChange={switchPerson}>
  {persons.map(p => <option>{p.name}</option>)}
</Select>
<Button onClick={createPerson}>+ Add Person</Button>
```

**WebSocket Notifications**
```typescript
wsManager.on('recategorization.completed', () => {
  toast.success('Done!');
  mutate('/api/transactions');
});
```

**LLM Model Settings**
```typescript
<Select value={settings.preferred_model}>
  <option value="gpt-5.2">GPT-5.2 (Latest)</option>
  <option value="gpt-4o">GPT-4o</option>
</Select>
```

---

## API Client

```typescript
import axios from 'axios';
const api = axios.create({ baseURL: 'http://localhost:8000' });

// Add auth token
api.interceptors.request.use(async (config) => {
  const token = await auth0.getTokenSilently();
  config.headers.Authorization = `Bearer ${token}`;
  return config;
});
```

---

## Environment

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_AUTH0_DOMAIN=...
NEXT_PUBLIC_AUTH0_CLIENT_ID=...
```

---

**Dependencies**: Backend API, Auth0  
**Status**: Ready
