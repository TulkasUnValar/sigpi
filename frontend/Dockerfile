# Development image for the Next.js frontend.
#
# The compose stack is a development stack (Django runserver, Keycloak
# start-dev), so this image runs `next dev` for hot-reload. A production
# multi-stage build (`next build` + `next start`, `output: 'standalone'`) is a
# separate concern for real deployment.
FROM node:20-alpine

WORKDIR /app

# Install from the lockfile first so the layer caches across source changes.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000

CMD ["npm", "run", "dev"]
