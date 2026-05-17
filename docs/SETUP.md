# E2E Integration Setup Guide

## Quick Start

### Prerequisites
- Python 3.10+ (backend)
- Node.js 18+ (frontend)
- Virtual environment (`venv` or similar)

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment (if not already done)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional)
# export GROQ_API_KEY=your_key_here
# export OPEN_ROUTER_API_KEY=your_key_here

# Run backend (default port 8000)
uvicorn main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000` with:
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# The .env.local should already have:
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Run frontend (default port 3000)
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

### Rule Management
- `POST /parse-rule` - Parse a rule without saving
  - Request: `{ "rule_text": "..." }`
  - Response: `{ "rule_text", "parsed_rule", "xslt", "xpath", "python_logic" }`

- `POST /rules` - Create and save a rule
  - Request: `{ "rule_text": "...", "severity": "high|medium|low" }`
  - Response: `{ "id", "rule_text", "parsed_json", "severity", "created_at" }`

- `GET /rules` - List all saved rules
  - Response: `[ { "id", "rule_text", "parsed_json", "severity", "created_at" } ]`

- `DELETE /rules/{rule_id}` - Delete a rule
  - Response: `{ "message", "id" }`

### Invoice Management
- `POST /invoices/upload` - Upload an XML invoice
  - Request: Form data with file upload
  - Response: `{ "id", "filename", "uploaded_at" }`

- `GET /invoices` - List uploaded invoices
  - Response: `[ { "id", "filename", "uploaded_at" } ]`

### Validation
- `POST /validate` - Validate one rule against one XML (not saved)
  - Request: `{ "rule_text": "...", "xml_content": "..." }`
  - Response: `{ "status": "PASS|FAIL|ERROR", "message", ... }`

- `POST /validate/all-rules` - Validate all saved rules against one XML
  - Request: `{ "xml_content": "..." }`
  - Response: `{ "results": [...], "summary": { "total", "passed", "failed", "errors" } }`

- `POST /invoices/{invoice_id}/validate` - Validate an uploaded invoice
  - Response: `{ "results": [...], "summary": {...} }`

### Dashboard
- `GET /dashboard/stats` - Get dashboard statistics
  - Response: `{ "total_rules", "total_invoices", "total_validations", "passed_validations", "failed_validations", "pass_rate" }`

## Frontend Features

### Rule Engine Page (`/rule-engine`)
1. **Write Rule** - Type a rule in plain English
2. **Parse Rule** - Click "Parse Rule" to see:
   - Structured JSON representation
   - Generated validation logic (XPath, XSLT, Python)
   - Editable code sections
3. **Add Rule** - Save to rules library with severity level
4. **XML Preview** - Test rule against sample XML

### Rules Library (`/rules-library`)
- View all saved rules
- Table and grid views
- Search and filter
- Edit/delete rules
- Create new rules

### Validate Invoices (`/validate-invoices`)
- Upload XML invoice files
- Validate against all saved rules
- View results summary
- Status indicators (Pass/Fail/Error)

### Validation Results (`/validation-results`)
- View all validation results
- Searchable and filterable table
- Detailed result information
- Performance metrics

### Dashboard (`/dashboard`)
- Real-time statistics
- Total rules, invoices, validations
- Pass rate metrics
- Recent validation activity

## Data Flow

### Create and Validate Rule
```
User Input (English) 
    ↓
[Parse Rule Button]
    ↓ POST /parse-rule
Backend (LLM Parser)
    ↓
Parse Result (JSON + XSLT + XPath)
    ↓
[Add Rule Button]
    ↓ POST /rules
Database (SQLite)
    ↓
Rule Saved
    ↓
Appears in Rules Library
```

### Upload and Validate Invoice
```
[Upload XML File]
    ↓ POST /invoices/upload
Database + File Storage
    ↓
Invoice ID Returned
    ↓
[Validate Button]
    ↓ POST /invoices/{id}/validate
Run All Saved Rules
    ↓
Validation Results
    ↓
Display in Results Page
    ↓
Dashboard Stats Updated
```

## Database

Currently uses **SQLite** (local file: `database.db` in backend folder)

Tables:
- `rules` - Stored validation rules
- `invoices` - Uploaded XML files
- `validation_results` - Results of rule evaluations

### Schema

```sql
-- Rules
CREATE TABLE rules (
  id INTEGER PRIMARY KEY,
  rule_text TEXT NOT NULL,
  parsed_json TEXT NOT NULL,
  rule_type TEXT,
  severity TEXT DEFAULT 'medium',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Invoices
CREATE TABLE invoices (
  id INTEGER PRIMARY KEY,
  filename TEXT,
  xml_content TEXT NOT NULL,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Validation Results
CREATE TABLE validation_results (
  id INTEGER PRIMARY KEY,
  invoice_id INTEGER FOREIGN KEY,
  rule_id INTEGER FOREIGN KEY,
  rule_text TEXT,
  status TEXT NOT NULL, -- PASS, FAIL, ERROR
  message TEXT,
  rule_type TEXT,
  validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Environment Variables

### Frontend (`.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (optional `.env` file)
```
GROQ_API_KEY=your_groq_api_key
OPEN_ROUTER_API_KEY=your_openrouter_api_key
OPEN_ROUTER_MODEL=anthropic/claude-3.5-sonnet
DB_PATH=database.db
```

## Testing

### 1. Test Parse Rule Endpoint
```bash
curl -X POST http://localhost:8000/parse-rule \
  -H "Content-Type: application/json" \
  -d '{"rule_text": "Tax amount must be greater than 0"}'
```

### 2. Test Create Rule
```bash
curl -X POST http://localhost:8000/rules \
  -H "Content-Type: application/json" \
  -d '{"rule_text": "Tax amount must be greater than 0", "severity": "high"}'
```

### 3. Test Health Check
```bash
curl http://localhost:8000/health
```

### 4. Through Frontend
- Visit `http://localhost:3000`
- Navigate to Rule Engine
- Type a rule and click "Parse Rule"
- Fill in severity and click "Add Rule"
- Go to Rules Library to see saved rule

## Troubleshooting

### Backend fails to start
- Check Python version: `python --version`
- Ensure venv is activated
- Install requirements: `pip install -r requirements.txt`
- Check if port 8000 is available: `lsof -i :8000` (Unix) or `netstat -ano | findstr :8000` (Windows)

### Frontend can't reach backend
- Verify backend is running on port 8000
- Check `.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Check browser console for CORS errors
- Backend has CORS enabled for all origins (development only)

### LLM Parser timeouts
- Ensure `GROQ_API_KEY` is set in backend environment
- Check internet connection (needed for LLM API calls)
- Timeout limit: 30 seconds

### Database errors
- Check write permissions in backend folder
- Delete `database.db` to reset database
- Tables auto-create on first run

## Future Enhancements

### Phase 4: Supabase Migration
To migrate from SQLite to Supabase:

1. Create Supabase project
2. Update database URL in backend:
   ```
   DATABASE_URL=postgresql://user:password@host/dbname
   ```
3. Update `orm_models.py` to use Postgres dialect
4. Run migrations

### Advanced Features
- Batch rule uploads
- Scheduled validations
- Webhook notifications
- Custom rule templates
- Multi-tenant support
- Advanced analytics

## Architecture Notes

The application follows a clear separation of concerns:

**Backend (FastAPI + SQLAlchemy)**
- RESTful API endpoints
- LLM-based rule parsing (Groq/OpenRouter)
- XSLT code generation
- XML validation execution
- SQLite persistence

**Frontend (Next.js + React)**
- Modern UI with Tailwind CSS
- Client-side state management
- Centralized API client
- Responsive design
- Real-time updates

**No Redesign Policy**
- Existing components and pages preserved
- Minimal architectural changes
- Backward compatible API extensions
- Focus on feature completion

## Support

For issues or questions:
1. Check the API documentation at `http://localhost:8000/docs`
2. Review browser console for frontend errors
3. Check backend logs for API errors
4. Ensure environment variables are set correctly
