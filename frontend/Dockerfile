# -------------------------------
# Stage 1: Build React app
# -------------------------------
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies (cache layer)
COPY package*.json ./
RUN npm ci --silent

# Copy rest of the source and build
COPY . .
RUN npm run build

# -------------------------------
# Stage 2: Serve with Nginx
# -------------------------------
FROM nginx:alpine

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy React build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Run Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
