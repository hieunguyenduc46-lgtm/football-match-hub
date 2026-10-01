# Stage 1: build the static site with Node (dev dependencies are only needed here).
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# Stage 2: serve the built files with nginx (small image, no Node or source code at runtime).
# nginx-unprivileged runs as a non-root user and listens on port 8080 instead of 80.
FROM nginxinc/nginx-unprivileged:stable-alpine

# Apply the latest Alpine security patches, then drop back to the non-root nginx user.
USER root
RUN apk upgrade --no-cache
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
USER 101

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/ > /dev/null || exit 1
