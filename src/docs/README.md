# Documentation System

This directory contains user-facing documentation for the Ontos platform. Documentation is served via API endpoints and rendered in the frontend.

## Quick Start: Adding New Documentation

### 1. Create the markdown file
```bash
cd src/docs
touch my-new-guide.md
```

### 2. Register it in `docs.yaml`
```yaml
documents:
  my-new-guide:
    file: my-new-guide.md
    title: My New Guide
    description: Brief description
    category: tutorial  # optional: user-guide, reference, tutorial
```

### 3. Test it
```bash
curl http://localhost:8000/api/user-docs/my-new-guide | jq
```

That's it! No code changes needed.

## Linking Between Documents

Use the frontend path in markdown links:

```markdown
See the [My Guide](/user-docs/my-new-guide) for details.
```

## API Endpoints

### List All Documentation
```
GET /api/user-docs
```

Returns metadata for all available documents.

### Get Specific Document
```
GET /api/user-docs/{doc_name}
```

Returns the document content and metadata.

### Legacy Endpoint
```
GET /api/user-guide
```

Backward compatibility endpoint for the user guide.

## Current Documentation

| Key | File | Category | Description |
|-----|------|----------|-------------|
| `user-guide` | USER-GUIDE.md | user-guide | Complete user guide |
| `compliance-dsl-guide` | compliance-dsl-guide.md | reference | DSL quick guide |
| `compliance-dsl-reference` | compliance-dsl-reference.md | reference | DSL complete reference |

## File Structure

```
src/docs/
├── docs.yaml                      # Document registry (edit this to add docs)
├── README.md                      # This file
├── USER-GUIDE.md                  # Main user guide
├── compliance-dsl-guide.md        # DSL quick guide
└── compliance-dsl-reference.md    # DSL complete reference
```

## How It Works

1. **docs.yaml** - Central registry defining all available documentation
2. **Backend** - Loads YAML, validates files exist, serves via `/api/user-docs`
3. **Frontend** - Route `/user-docs/:docName` fetches and renders markdown

### Backend Implementation

- File: `src/backend/src/routes/settings_routes.py`
- Function: `_load_docs_registry()` reads `docs.yaml`
- Function: `_get_available_docs()` validates files and returns metadata
- Endpoints: `/api/user-docs` and `/api/user-docs/{doc_name}`

### Frontend Implementation

- Component: `src/frontend/src/views/documentation-viewer.tsx`
- Route: `/user-docs/:docName` in `app.tsx`
- Fetches from API and renders markdown with table of contents

## Endpoint Migration Note

The system uses `/api/user-docs` (not `/api/docs`) to avoid conflicts with FastAPI's Swagger documentation at `/docs`. The vite proxy routes `/docs` to the backend for API documentation.

## Document Categories

Suggested categories for organizing documentation:
- `user-guide` - User-facing guides
- `reference` - Technical references
- `tutorial` - Step-by-step tutorials
- `api` - API documentation
- `developer` - Developer guides

## Markdown Guidelines

1. Start with an H1 heading (`# Title`)
2. Use H2-H3 for sections (generates table of contents)
3. Include code examples with language tags
4. Use `/user-docs/` paths for cross-references
5. Keep descriptions concise (one sentence)

## Troubleshooting

**Document not appearing?**
- Check YAML syntax is valid
- Verify file path in `docs.yaml` matches actual file
- Restart backend server
- Check logs for errors

**Links not working?**
- Use full frontend path: `/user-docs/doc-name`
- Don't use relative paths or filenames
- Frontend route handles loading from API

## Example: Adding Deployment Guide

1. Create `deployment-guide.md`:
```markdown
# Deployment Guide

Instructions for deploying data products...
```

2. Add to `docs.yaml`:
```yaml
documents:
  deployment-guide:
    file: deployment-guide.md
    title: Deployment Guide
    description: Guide for deploying data products to Unity Catalog
    category: tutorial
```

3. Link from other docs:
```markdown
See the [Deployment Guide](/user-docs/deployment-guide) for instructions.
```

4. Access it:
- Frontend: `http://localhost:3000/user-docs/deployment-guide`
- API: `http://localhost:8000/api/user-docs/deployment-guide`

## Benefits of This System

- **Configuration-driven**: Add docs by editing YAML only
- **No code changes**: Non-developers can add documentation
- **Category support**: Organize docs by type
- **Validation**: System checks files exist before serving
- **Backward compatible**: Legacy endpoints still work
- **Conflict-free**: Doesn't interfere with Swagger docs

## Maintenance

When updating documentation:
1. Edit the markdown file
2. Update "Last Updated" date in footer (if present)
3. Check cross-references still work
4. Test the API endpoint returns updated content
