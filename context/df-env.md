# Dark Factory Environment Context

Reference file. Not invocable. Loaded by dark-factory ASK skills.

---

## Repository

- **Repo:** `srmbsrg/dark-factory` (public)
- **Purpose:** Self-building code generator — generates, evaluates, and commits code autonomously
- **Primary branch:** `main`
- **Push method:** See `context/gfs-env.md` GitHub section — same PAT, same urllib pattern

---

## Generation Pattern

Dark Factory operates on a loop:
1. **Prompt** — receive a generation target (what to build / what to improve)
2. **Generate** — produce candidate code via LLM (OpenRouter, same model as Tes)
3. **Evaluate** — score candidate against acceptance criteria
4. **Select** — keep best candidate or iterate
5. **Commit** — push to branch via GitHub API
6. **Notify** — telegram Scott with result

---

## ASK Integration Principle

When DF generates code that requires a known capability (GitHub push, Vercel deploy, Telegram notify, etc.), it emits an ASK invocation rather than generating that code from scratch. The generated output references the appropriate skill by path:

```
# In DF-generated code:
# ASK: foundation/github-push — push generated file to repo
# ASK: foundation/vercel-deploy — trigger redeployment
```

This keeps generated code minimal and stable — capability logic lives in the ASK library, not in generated output.

---

## Accepted Generation Targets

- New API routes for GFS (`app/api/...`)
- New UI components (`components/...`)
- New lib utilities (`lib/...`)
- New ASK skills (meta: DF can generate new skills for the library)
- Schema extensions (new Prisma models appended to `prisma/schema.prisma`)

---

## Quality Gates

Generated code must pass before commit:
1. TypeScript compilation (no type errors)
2. No hardcoded secrets (all env vars via `process.env`)
3. No blocking async in render path
4. Single responsibility — one file, one concern
5. If touching existing file: diff must be additive, not destructive
