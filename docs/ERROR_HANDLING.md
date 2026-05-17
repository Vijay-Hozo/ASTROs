# Error Handling & Network Resilience Guide

## What's Been Improved ✅

### 1. **Automatic Retry Logic**
- Network errors automatically retry up to 2 times with exponential backoff
- Timeouts trigger a retry after 1 second, then 2 seconds
- HTTP errors don't retry (avoids wasting requests)
- Only actual network issues trigger retries

### 2. **Better Error Messages**
The API client now provides helpful, actionable error messages:

**Network Error:**
```
Network error: Unable to reach http://localhost:8000. Check that:
• The backend server is running
• The API URL is correct: http://localhost:8000
• Your internet connection is working
```

**Timeout Error:**
```
Request timed out after 30000ms. The server may be slow or unreachable.
```

**Validation Error:**
```
Please enter a rule before parsing
```

### 3. **Health Check Monitor**
- Automatically checks backend connectivity every 30 seconds
- Shows helpful toast notification if backend is unreachable
- Includes quick-start command for backend

**Health Check Toast:**
```
❌ Backend Connection Issue
Cannot connect to backend. Make sure it's running at http://localhost:8000

💡 Tip: Run the backend with:
cd backend && uvicorn main:app --reload
```

### 4. **Enhanced UI Error Display**
Rule Input Card now shows:
- ✅ Error type (Connection Error vs Validation Error)
- ✅ Detailed multi-line error message
- ✅ Retry button for connection errors (grayed out for validation errors)
- ✅ Better styling with red border and background

### 5. **Error Boundary Component**
- Catches uncaught errors across the app
- Shows friendly error message
- Provides reload button for recovery

---

## How It Works

### Request Flow with Retries

```
User Action
    ↓
API Request (POST /parse-rule)
    ↓
fetchWithRetry() invoked
    ↓
Try 1: Network error occurs
    ↓
Wait 1 second (exponential backoff)
    ↓
Try 2: Network error occurs again
    ↓
Wait 2 seconds
    ↓
Try 3: Network error occurs again
    ↓
Max retries reached (2)
    ↓
Error normalized with helpful message
    ↓
Component displays error
    ↓
User sees "Retry" button
    ↓
Click Retry → Starts fresh attempt
```

### Error Detection

| Error Type | Detection | Action |
|------------|-----------|--------|
| Network Error | `TypeError` from fetch | Retry up to 2 times |
| Timeout | `AbortError` from fetch | Retry up to 2 times |
| HTTP 4xx | Non-OK response | Don't retry, show error |
| HTTP 5xx | Non-OK response | Don't retry, show error |
| JSON Parse | Invalid JSON response | Show parse error |

---

## Testing the Error Handling

### Scenario 1: Backend Not Running
**Setup:** Start frontend only, don't start backend
**Expected Behavior:**
1. Page loads normally
2. Health check runs (every 30 seconds)
3. Toast appears: "Backend Connection Issue"
4. Click on Rule Engine page
5. Try to parse a rule
6. See error message with "Retry" button
7. Start backend
8. Click "Retry"
9. Request succeeds!

### Scenario 2: Slow Network
**Setup:** Simulate slow network in DevTools
**Expected Behavior:**
1. Request times out
2. Error message shows timeout
3. Automatic retries happen
4. If still failing, shows error to user
5. Retry button available

### Scenario 3: Invalid API URL
**Setup:** Change `NEXT_PUBLIC_API_URL` to wrong port
**Expected Behavior:**
1. Network error on every request
2. Error message shows wrong URL
3. Guide user to fix `.env.local`
4. Retries fail (won't connect to wrong port)

### Scenario 4: Validation Error
**Setup:** Click "Parse Rule" with empty text
**Expected Behavior:**
1. Shows "Validation Error"
2. Message: "Please enter a rule before parsing"
3. No retry button (validation error, not connection)

---

## Configuration

### Environment Variables (.env.local)

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# If backend runs on different port:
NEXT_PUBLIC_API_URL=http://localhost:8001

# For production:
NEXT_PUBLIC_API_URL=https://api.example.com
```

### API Client Constants (lib/api-client.ts)

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const REQUEST_TIMEOUT = 30000; // 30 seconds
const MAX_RETRIES = 2; // Retry up to 2 times
const RETRY_DELAY = 1000; // Start with 1s delay, exponential backoff
```

To adjust:
1. Change `MAX_RETRIES` to increase retry attempts
2. Change `RETRY_DELAY` to adjust backoff timing
3. Change `REQUEST_TIMEOUT` to adjust timeout threshold

---

## Files Modified

### Backend
- No changes to backend API (already works)

### Frontend

**API Client:**
- `lib/api-client.ts` - Added retry logic, improved error messages

**Components:**
- `components/rule-engine/rule-input-card.tsx` - Better error display + retry button
- `components/health-check.tsx` - NEW: Health monitoring
- `components/error-boundary.tsx` - NEW: Error boundary
- `app/layout.tsx` - Added HealthCheck to all pages

---

## Testing Checklist

- [ ] Start backend: `cd backend && uvicorn main:app --reload`
- [ ] Start frontend: `cd frontend && npm run dev`
- [ ] Navigate to http://localhost:3000
- [ ] Check health notification (should disappear if backend running)
- [ ] Go to /rule-engine page
- [ ] Type "Tax amount must be positive"
- [ ] Click "Parse Rule"
- [ ] See result appear (parsed JSON + logic)
- [ ] Click "Add Rule" with severity
- [ ] See success message
- [ ] Go to /rules-library
- [ ] See your rule in the list

**Troubleshooting Test:**
- [ ] Stop backend
- [ ] Refresh page
- [ ] See health notification
- [ ] Try to parse rule
- [ ] See connection error with retry button
- [ ] Click retry
- [ ] See error (backend not running)
- [ ] Start backend
- [ ] Click retry again
- [ ] See success!

---

## User Experience Improvements

### Before
❌ Generic "Network error occurred" message  
❌ No guidance on what to do  
❌ Retry requires page reload  
❌ No visibility into backend status  

### After
✅ Detailed error messages with actionable steps  
✅ Helpful tooltips with commands to run  
✅ One-click retry button  
✅ Real-time health check notifications  
✅ Automatic retries for transient failures  
✅ Better loading states  
✅ Error boundary for app stability  

---

## Next Steps

### Short-term
- Monitor error logs to identify common issues
- Adjust retry timing if needed based on network conditions
- Add more detailed errors for specific API failures

### Medium-term
- Add request/response logging to DevTools
- Implement circuit breaker pattern for repeated failures
- Add analytics tracking for error types

### Long-term
- Migrate to Supabase (reduces network latency)
- Implement websockets for real-time updates
- Add offline-first functionality with service workers

---

## Questions & Answers

**Q: Will retry slow down the app?**
A: No. Retries only happen on actual network failures. Normal requests are unaffected. Retry delay starts at 1 second with exponential backoff.

**Q: Can I disable retries?**
A: Yes. Set `MAX_RETRIES = 0` in `lib/api-client.ts`. But not recommended - retries help with transient network issues.

**Q: What if the backend is really slow?**
A: Increase `REQUEST_TIMEOUT` in `lib/api-client.ts`. Default is 30 seconds, which should be plenty.

**Q: Does retry affect the database?**
A: No. Retries only happen on the client side before reaching the backend. Each successful request is exactly one database operation.

**Q: Can users see retry attempts?**
A: No. Retries are silent. User only sees "Parsing..." loading state. If all retries fail, then error is shown.
