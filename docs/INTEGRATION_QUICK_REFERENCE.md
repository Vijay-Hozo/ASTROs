# Integration Audit - Developer Quick Reference
**Status:** 15% Ready | Effort: 25-35 hours | Timeline: 3-5 days

---

## 🚀 GET STARTED - 5 MINUTE SETUP

### 1. Backend Status ✅
```bash
cd backend
uvicorn main:app --reload --port 8000

# Should see: Uvicorn running on http://127.0.0.1:8000
# Test: curl http://localhost:8000/health
```

### 2. Frontend Status ⚠️
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev

# Should see: ▲ Next.js running on http://localhost:3000
# But: Pages use mock data, buttons don't work
```

### 3. What Needs to Happen
Frontend must make actual API calls instead of using mock data.

---

## 📋 THE WORK BREAKDOWN

### Phase 1: HTTP Client Foundation (TODAY) - 3-4 hours
**Create:** `frontend/lib/api-client.ts`
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = {
  async get(endpoint: string) {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  },
  
  async post(endpoint: string, body: any) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  },
  
  async delete(endpoint: string) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return null;
  },
  
  async uploadFile(endpoint: string, file: File) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      body: fd,
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  }
};
```

---

### Phase 2: Rules CRUD (DAY 2) - 3-4 hours

**File:** `frontend/components/rules-library/rules-library-client.tsx`

```typescript
import { api } from '@/lib/api-client';
import { useState, useEffect } from 'react';

export default function RulesLibraryClient() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Fetch rules on mount
  useEffect(() => {
    loadRules();
  }, []);

  async function loadRules() {
    try {
      setLoading(true);
      const data = await api.get('/rules');
      setRules(data);
    } catch (err) {
      setError('Failed to load rules');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateRule() {
    const text = prompt('Enter rule text:');
    if (!text) return;
    try {
      const newRule = await api.post('/rules', {
        rule_text: text,
        severity: 'high'
      });
      setRules([newRule, ...rules]);
    } catch (err) {
      setError('Failed to create rule');
    }
  }

  async function handleDeleteRule(id) {
    try {
      await api.delete(`/rules/${id}`);
      setRules(rules.filter(r => r.id !== id));
    } catch (err) {
      setError('Failed to delete rule');
    }
  }

  return (
    // Render with real rules, show loading/error states
  );
}
```

---

### Phase 3: File Upload (DAY 3) - 3-4 hours

**File:** `frontend/components/validate-invoices/upload-card.tsx`

```typescript
import { api } from '@/lib/api-client';
import { useState } from 'react';

export default function UploadCard() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [uploadedId, setUploadedId] = useState(null);

  async function handleUpload() {
    if (!file) return;
    
    // Validate size (backend: 1MB max)
    if (file.size > 1_000_000) {
      setError('File too large (max 1MB)');
      return;
    }

    try {
      setUploading(true);
      const result = await api.uploadFile('/invoices/upload', file);
      setUploadedId(result.id);
      
      // Now validate
      const validationResult = await api.post(`/invoices/${result.id}/validate`, {});
      // Display validation results...
    } catch (err) {
      setError('Upload failed');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <input
        type="file"
        accept=".xml"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button
        onClick={handleUpload}
        disabled={uploading || !file}
      >
        {uploading ? 'Uploading...' : 'Upload'}
      </button>
      {error && <div className="text-red-600">{error}</div>}
    </div>
  );
}
```

---

### Phase 4: Dashboard & Results (DAY 4) - 2-3 hours

**File:** `frontend/components/dashboard/dashboard-shell.tsx`

```typescript
import { api } from '@/lib/api-client';
import { useState, useEffect } from 'react';

export default function DashboardShell() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const data = await api.get('/dashboard/stats');
        setStats(data);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!stats) return <div>Error loading stats</div>;

  return (
    <div>
      <StatsCard title="Total Rules" value={stats.total_rules} />
      <StatsCard title="Pass Rate" value={`${stats.pass_rate.toFixed(1)}%`} />
      {/* Use real stats instead of hardcoded */}
    </div>
  );
}
```

---

## 🧪 TESTING EACH ENDPOINT

### Rules Endpoints
```bash
# GET /rules
curl http://localhost:8000/rules

# POST /rules
curl -X POST http://localhost:8000/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_text": "Tax amount must be > 0",
    "severity": "high"
  }'

# DELETE /rules/{id}
curl -X DELETE http://localhost:8000/rules/1
```

### Validation Endpoints
```bash
# POST /validate (single)
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "rule_text": "Seller name is required",
    "xml_content": "<Invoice><seller_name>ABC</seller_name></Invoice>"
  }'

# POST /validate/all-rules (batch)
curl -X POST http://localhost:8000/validate/all-rules \
  -H "Content-Type: application/json" \
  -d '{
    "xml_content": "<Invoice>...</Invoice>"
  }'
```

### Invoice Endpoints
```bash
# POST /invoices/upload
curl -X POST http://localhost:8000/invoices/upload \
  -F "file=@invoice.xml"

# GET /invoices
curl http://localhost:8000/invoices

# GET /results
curl http://localhost:8000/results

# GET /results/{invoice_id}
curl http://localhost:8000/results/1
```

---

## 🔴 CRITICAL ERRORS TO HANDLE

```typescript
// CORS Error
// Fix: Ensure backend has CORS headers
// In main.py: app.add_middleware(CORSMiddleware, ...)

// 504 Timeout Error  
// Meaning: Rule parsing took >30 seconds
// Fix: Show message "Still parsing, may take up to 30 seconds..."

// 413 Payload Too Large
// Meaning: XML file > 1MB
// Fix: Validate file size in frontend before upload

// 422 Validation Error
// Meaning: Invalid request body
// Fix: Check request schema matches endpoint docs

// 500 Server Error
// Meaning: Unexpected error in backend
// Fix: Check backend logs, may be LLM API issue
```

---

## ✅ DEFINITION OF DONE

For each feature, test:

**Rules CRUD:**
- [ ] Load rules on page mount → GET /rules returns data
- [ ] Create rule → POST /rules works, returns id
- [ ] Delete rule → DELETE /rules/{id} removes from UI
- [ ] Error shown if API fails

**File Upload:**
- [ ] File input captures file → File object created
- [ ] Upload button enabled only when file selected
- [ ] Upload works → POST /invoices/upload succeeds
- [ ] File size validated before upload
- [ ] Error shown if file >1MB

**Validation:**
- [ ] Rule parse works → POST /validate returns PASS/FAIL
- [ ] Show loading "Parsing rule..." during API call
- [ ] Display validation result
- [ ] Handle 504 timeout gracefully

**Dashboard:**
- [ ] Stats load on mount → GET /dashboard/stats
- [ ] Shows real numbers, not hardcoded
- [ ] Refresh stats after rule create/delete

**Results:**
- [ ] Load results on mount → GET /results
- [ ] Filter/search works on real data
- [ ] Click row → GET /results/{invoice_id}
- [ ] Show detail modal

---

## 📊 PROGRESS CHECKLIST

### Phase 1 (3-4h)
- [ ] Create api-client.ts
- [ ] Create .env.local with API_URL
- [ ] Test first endpoint (GET /health)
- [ ] Commit to repo

### Phase 2 (3-4h)  
- [ ] Rules list loads from backend
- [ ] Create rule works
- [ ] Delete rule works
- [ ] All 3 rules endpoints integrated
- [ ] Commit

### Phase 3 (3-4h)
- [ ] File upload works
- [ ] Validation triggered after upload
- [ ] Results displayed
- [ ] All invoice endpoints integrated
- [ ] Commit

### Phase 4 (2-3h)
- [ ] Dashboard loads stats
- [ ] Rule engine parse works
- [ ] All dashboard endpoints integrated
- [ ] Commit

### Phase 5 (2-3h)
- [ ] Test all error codes
- [ ] CORS verified working
- [ ] All loading states complete
- [ ] Final testing & polish
- [ ] Commit

---

## 💡 PRO TIPS

1. **Development Mode**
   - Keep backend and frontend both running in dev mode
   - Use browser DevTools Network tab to inspect API calls
   - Check terminal logs for backend errors

2. **Common Mistakes**
   - Forget to set NEXT_PUBLIC_API_URL → API_BASE falls back to localhost:8000
   - Don't handle 504 timeouts (rule parsing can take 30 seconds)
   - Forget to import api-client in components
   - Don't disable buttons during loading (users click multiple times)

3. **Fast Iteration**
   - Use curl to test endpoints directly from terminal
   - Test backend separately from frontend
   - Make sure backend returns expected response format
   - Then wire up frontend to consume it

4. **Debugging**
   - Always check network tab in DevTools
   - Look at both frontend console and backend terminal
   - Check CORS headers if cross-origin errors
   - Use `console.log(response)` to verify data shape

---

## 📞 SUPPORT

If stuck:
1. Check FRONTEND_BACKEND_INTEGRATION_AUDIT.md (full details)
2. Run test curl commands to verify endpoint works
3. Check DevTools Network tab to see API response
4. Check backend terminal for error messages
5. Review test_fixes.py in backend for integration examples

---

**Ready to start? Begin Phase 1 now!**

Questions? See FRONTEND_BACKEND_INTEGRATION_AUDIT.md for details.
