# ---- build: compile the SPA ----
FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . ./
# Baked at build time. Same-origin (nginx proxy) → empty. Direct API → full URL.
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ---- runtime: static serve via nginx ----
FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
