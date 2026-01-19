# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a customized RAG (Retrieval Augmented Generation) chat application built on the Azure OpenAI and Azure AI Search demo template. It creates a ChatGPT-like experience over custom training data for Pheydrus CMO (Chief Marketing Officer) assistant. The application uses Azure OpenAI Service (GPT models) and Azure AI Search for document indexing and retrieval.

**Key Customization**: This instance is specifically configured with CMO-focused marketing prompts for creating viral social media content, Instagram posts, and high-converting marketing materials. See `app/backend/approaches/prompts/cmo_prompt.prompty` for the specialized system prompt.

## Development Commands

### Local Development

**Prerequisites**: Must run `azd up` to deploy to Azure before local development.

**Start full application** (after deployment):
```bash
# Windows
./app/start.ps1

# Linux/Mac
./app/start.sh
```

**Hot reload development** (both frontend and backend):
```bash
# Use VS Code Task: "Development" (default build task: Shift+Cmd+B)
# Or manually:
cd app/frontend && npm run dev  # Frontend on port 5173
# In separate terminal:
cd app/backend && ../../.venv/bin/python -m quart run --reload -p 50505
```

### Frontend

```bash
cd app/frontend
npm install          # Install dependencies
npm run dev          # Development server with hot reload (port 5173)
npm run build        # Production build
```

### Backend

```bash
# Activate virtual environment first
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

cd app/backend
python -m quart --app main:app run --port 50505 --host localhost --reload
```

### Testing

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/test_app.py

# Run with coverage
pytest --cov=app/backend --cov=scripts
```

### Code Quality

```bash
# Python linting and formatting (from project root)
ruff check app/backend scripts          # Linting
ruff format app/backend scripts         # Formatting
black app/backend scripts --line-length 120

# Type checking
cd app/backend && mypy . --config-file=../../pyproject.toml
cd scripts && mypy . --config-file=../pyproject.toml

# Frontend formatting
cd app/frontend
npm run prettier
```

### Data Ingestion

```bash
# Windows
./scripts/prepdocs.ps1

# Linux/Mac
./scripts/prepdocs.sh
```

New data files should be added to the `data/` folder before running prepdocs.

### Azure Deployment

```bash
azd auth login       # Authenticate
azd env new          # Create new environment
azd up              # Provision and deploy
azd deploy          # Deploy code changes only
azd down            # Delete all resources
```

## Architecture

### High-Level Structure

```
Frontend (React/TypeScript) <-> Backend (Python/Quart) <-> Azure Services
     ↓                              ↓                          ↓
  Vite build                  RAG Approaches           OpenAI + AI Search
```

**Frontend**: React + TypeScript + Fluent UI, built with Vite
- Location: `app/frontend/`
- Entry: `app/frontend/src/main.tsx`
- Pages: Chat and Ask interfaces in `app/frontend/src/pages/`

**Backend**: Python + Quart (async Flask)
- Location: `app/backend/`
- Entry: `app/backend/app.py` (main Flask/Quart app)
- Main: `app/backend/main.py` (imports from app.py)

### RAG Approaches

The core RAG logic lives in `app/backend/approaches/`:

**Base Class**: `approach.py`
- Defines `Approach` abstract base class
- Contains `Document`, `ThoughtStep`, `DataPoints` data classes
- Handles search, embedding, and response generation patterns

**Chat Approach**: `chatreadretrieveread.py` (ChatReadRetrieveReadApproach)
Used by the Chat tab for multi-turn conversations:
1. **Query Rewriting**: Rewrites user question into optimized search query using `chat_query_rewrite.prompty`
2. **Search**: Queries Azure AI Search (vector + text hybrid search)
3. **Answering**: Generates response using chat history + sources via `chat_answer_question.prompty`

**Ask Approach**: `retrievethenread.py` (RetrieveThenReadApproach)
Used by the Ask tab for single-turn Q&A:
1. **Search**: Queries Azure AI Search directly with user question
2. **Answering**: Generates response using sources via `ask_answer_question.prompty`

### Prompty Files

Prompt templates use the `.prompty` format and are managed by `promptmanager.py`:
- `ask_answer_question.prompty` - Ask tab responses
- `chat_query_rewrite.prompty` - Query rewriting for search optimization
- `chat_answer_question.prompty` - Chat tab responses
- **`cmo_prompt.prompty`** - CMO-specific marketing system prompt (CUSTOM)

The CMO prompt is heavily customized for social media copywriting, Instagram content, and high-converting marketing materials with specific CTAs for courses (Artist's Way, Hero's Journey, 21 DOMA, Business Growth).

### Configuration System

Settings are managed through:
- **Azure Environment Variables**: Stored via `azd env set` for deployment config
- **Frontend Overrides**: User-adjustable settings in `Chat.tsx` and `Ask.tsx`
- **Backend Config**: `app/backend/config.py` consolidates all configuration constants
- **Developer Settings**: UI panel allows runtime override of retrieval mode, semantic ranker, etc.

### Document Processing Pipeline

`prepdocs.py` and `prepdocslib/` handle document ingestion:
1. **Text Extraction**: Uses Azure Document Intelligence for PDFs
2. **Chunking**: Splits documents into searchable chunks
3. **Embedding Generation**: Creates vector embeddings via Azure OpenAI
4. **Indexing**: Uploads to Azure AI Search with metadata

## Key Files to Modify

### For Prompt/Response Customization
- `app/backend/approaches/prompts/cmo_prompt.prompty` - Main CMO system prompt
- `app/backend/approaches/prompts/chat_answer_question.prompty` - Chat responses
- `app/backend/approaches/prompts/ask_answer_question.prompty` - Ask responses

### For UI Customization
- `app/frontend/src/locales/en/translation.json` - All UI text strings
- `app/frontend/src/components/` - React components
- `app/frontend/src/pages/chat/Chat.tsx` - Chat interface
- `app/frontend/src/pages/ask/Ask.tsx` - Ask interface

### For Backend Logic
- `app/backend/approaches/chatreadretrieveread.py` - Chat approach implementation
- `app/backend/approaches/retrievethenread.py` - Ask approach implementation
- `app/backend/app.py` - API endpoints and app initialization

### For Infrastructure
- `infra/main.bicep` - Azure resource definitions
- `infra/main.parameters.json` - Deployment parameters
- `azure.yaml` - Azure Developer CLI configuration

## Important Patterns

### Adding New Developer Settings

When adding UI-configurable settings:

1. **Frontend**:
   - Add to `ChatAppRequestOverrides` in `app/frontend/src/api/models.ts`
   - Add UI element in `app/frontend/src/components/Settings.tsx`
   - Add translations to all `app/frontend/src/locales/*/translation.json` files
   - Pass setting in `Chat.tsx` and `Ask.tsx`

2. **Backend**:
   - Retrieve from `context.get("overrides", {})` in approach classes
   - Optionally expose in `/config` route in `app.py`

### Adding Azure Environment Variables

Update in order:
1. `infra/main.parameters.json` - Map env var to Bicep parameter
2. `infra/main.bicep` - Add parameter and to `appEnvVariables` object
3. `.github/workflows/azure-dev.yml` - Add to `env` section (if using CI/CD)

### Prompt Template Usage

Use `PromptManager` to load `.prompty` files:
```python
prompt_manager = PromptManager()
prompt = prompt_manager.render_prompt("cmo_prompt.prompty", context={...})
```

### Testing Strategy

- **E2E tests**: Playwright-based UI testing in `tests/e2e.py`
- **Integration tests**: API endpoint testing in `tests/test_app.py`
- **Unit tests**: Individual function tests in `tests/test_*.py`
- Use mocks from `tests/conftest.py` and `tests/mocks.py`

## Training Data Structure

Custom CMO training data is located in `data/Train_CMO/`:
- Artist's Way content and testimonials
- Video testimonial transcripts
- Course module information
- Marketing copy examples

This data is indexed and retrieved during RAG operations to provide context-aware responses aligned with Pheydrus brand voice and methodology.

## Deployment Targets

- **Default**: Azure Container Apps (defined in `azure.yaml`)
- **Alternative**: Azure App Service (requires modifying `azure.yaml` host setting)
- **Local**: Development server on localhost:50505 (backend) + localhost:5173 (frontend dev server)

## Authentication & Security

- Authentication handled via `core/authentication.py` (AuthenticationHelper)
- Uses Azure AD/Entra ID for optional user login and access control
- API route decorators: `@authenticated` and `@authenticated_path`

## Monitoring

- Application Insights integration for telemetry
- OpenTelemetry instrumentation for tracing
- Configuration in `app/backend/app.py` via `configure_azure_monitor()`
