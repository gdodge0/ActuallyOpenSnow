# Frontend Dockerfile - Vue.js with multi-stage build
# Stage 1: Build the Vue application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first for better layer caching
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci --prefer-offline --no-audit

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check using curl
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:80/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
