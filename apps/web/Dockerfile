# Stage 1: Dependencies
# Build context must be the repo root so the monorepo lockfile is accessible:
#   docker build -f apps/web/Dockerfile .
FROM node:22-alpine AS deps

WORKDIR /app

# Copy root workspace manifests + lockfile first for layer caching
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
# Copy the web app manifest so pnpm resolves the workspace package
COPY apps/web/package.json ./apps/web/package.json
RUN corepack enable && pnpm install --frozen-lockfile

# Stage 2: Build
FROM node:22-alpine AS build

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
# Copy only the web app source (not the entire monorepo)
COPY apps/web/ ./apps/web/

RUN corepack enable && cd apps/web && pnpm run build

# Stage 3: Production
FROM node:22-alpine AS production

WORKDIR /app

RUN addgroup -g 1001 -S appuser && adduser -S appuser -u 1001

COPY --from=build /app/apps/web/.next/standalone ./
COPY --from=build /app/apps/web/.next/static ./.next/static

USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
