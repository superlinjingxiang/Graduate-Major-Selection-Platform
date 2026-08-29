# syntax=docker/dockerfile:1
FROM node:22-alpine AS builder

ENV PNPM_HOME=/pnpm \
    PATH="${PNPM_HOME}:${PATH}" \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /workspace

RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json tsconfig.base.json tsconfig.package.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/design-tokens/package.json packages/design-tokens/package.json
COPY packages/domain/package.json packages/domain/package.json

RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY packages/api-client packages/api-client
COPY packages/design-tokens packages/design-tokens
COPY packages/domain packages/domain

RUN pnpm --filter @gradmatch/web build

FROM node:22-alpine AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app

RUN addgroup --system --gid 10001 gradmatch \
    && adduser --system --uid 10001 --ingroup gradmatch gradmatch

COPY --from=builder --chown=gradmatch:gradmatch /workspace/apps/web/.next/standalone ./
COPY --from=builder --chown=gradmatch:gradmatch /workspace/apps/web/.next/static ./apps/web/.next/static

USER gradmatch

WORKDIR /app/apps/web

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=6 \
  CMD node -e "fetch('http://127.0.0.1:3000/').then((response) => process.exit(response.ok ? 0 : 1)).catch(() => process.exit(1))"

CMD ["node", "server.js"]
