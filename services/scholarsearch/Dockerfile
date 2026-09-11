# ScholarSearch backend test image — apps/server workspace only.
# Frontend (apps/client) is built nowhere and shipped nowhere: the E2E
# contract targets :3001, so compiling UI would be pure CI-minute burn.
FROM node:20-slim AS builder

WORKDIR /repo

COPY . .

RUN npm ci

# Generate Prisma client bindings — db.ts imports @prisma/client directly.
RUN npx prisma generate

# Build the server workspace and its workspace dependencies only.
# turbo filter "..." suffix = "@scholarsearch/server plus everything it depends on".
RUN npx turbo run build --filter=@scholarsearch/server...

FROM node:20-slim AS runtime

ENV NODE_ENV=production PORT=3001 HOST=0.0.0.0

WORKDIR /repo

COPY --from=builder /repo/package.json /repo/package-lock.json ./
COPY --from=builder /repo/apps/server ./apps/server
COPY --from=builder /repo/packages ./packages
COPY --from=builder /repo/node_modules ./node_modules

RUN groupadd -r scholar && useradd -r -g scholar -d /repo scholar \
  && chown -R scholar:scholar /repo

USER scholar

EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "fetch('http://localhost:3001/health').then(function(r){if(!r.ok)process.exit(1)}).catch(function(){process.exit(1)})"

CMD ["node", "apps/server/dist/server.js"]
