---
title: eMAG API Documentation (Deprecated)
last_reviewed: 2025-09-25
status: deprecated
owner: integrations-team
---

# eMAG API Documentation (Deprecated)

The comprehensive "Cascade master prompt" that previously lived here has been superseded by focused, easier-to-maintain references.

## Current Sources of Truth

- `docs/integrations/emag/api_reference.md` — canonical limits, authentication rules, payload requirements, and retry/backoff policies.
- `docs/integrations/emag/integration_overview.md` — architecture, supported flows, and configuration summary.
- `docs/integrations/emag/catalog.md` — catalog workflows and examples.
- `docs/EMAG_FULL_SYNC_GUIDE.md` — operational runbook for running and monitoring full syncs.
- `docs/EMAG_CREDENTIALS_TESTING_GUIDE.md` — procedures for validating credentials against the live marketplace.

## Migration Checklist

- Update any bookmarks, runbooks, or onboarding guides to reference the documents above.
- Remove personal copies of the legacy prompt; the original text remains in git history if needed.
- When new API nuances surface, append them to `docs/integrations/emag/api_reference.md` instead of reintroducing large monolithic prompts.
