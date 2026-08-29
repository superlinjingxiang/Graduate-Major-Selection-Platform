# GradMatch

GradMatch starts as a Web-first monorepo foundation for a future Django API and Next.js product. Task 1 establishes the workspace, shared packages, Python service skeleton, and validation commands only.

## Workspace

- `apps/web`: minimal Next.js App Router foundation page
- `packages/api-client`: shared TypeScript API boundary placeholders for future generated clients
- `packages/domain`: shared TypeScript domain contracts
- `packages/design-tokens`: typed semantic design tokens with no browser dependencies
- `services/api`: uv-managed Python service package; Django is intentionally deferred to Task 2

## Commands

- `pnpm dev`: start the monorepo development processes
- `pnpm build`: build all TypeScript workspace packages and the web app
- `pnpm lint`: run Biome across JavaScript, TypeScript, JSON, and Markdown files
- `pnpm typecheck`: run strict TypeScript checks across the workspace
- `pnpm test`: run workspace smoke tests
- `pnpm format:check`: verify formatting with Biome
- `pnpm generate:api`: placeholder command until Task 3 generates OpenAPI clients

## Python Service

Use the local `uv` installation to manage `services/api`:

```powershell
& 'C:\Users\76358\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts\uv.exe' lock
& 'C:\Users\76358\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts\uv.exe' run ruff check .
& 'C:\Users\76358\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts\uv.exe' run pyright
& 'C:\Users\76358\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts\uv.exe' run pytest
```

## Scope Notes

The mobile app is intentionally absent in this repository stage. Expo support is deferred until a later task.
