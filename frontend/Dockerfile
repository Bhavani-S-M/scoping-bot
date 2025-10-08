# -------------------------------
# Stage 1: Build React app
# -------------------------------
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies efficiently
COPY package*.json ./
RUN npm ci --silent

# Copy source and build
COPY . .
RUN npm run build


# -------------------------------
# Stage 2: Serve with Nginx
# -------------------------------
FROM nginx:alpine

# Remove default Nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy React build output
COPY --from=builder /app/dist /usr/share/nginx/html

# (Optional) Enable gzip for performance
RUN echo 'gzip on;' >> /etc/nginx/nginx.conf && \
    echo 'gzip_types text/plain text/css application/json application/javascript text/javascript;' >> /etc/nginx/nginx.conf

# Expose Nginx port
EXPOSE 80

# Run Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
