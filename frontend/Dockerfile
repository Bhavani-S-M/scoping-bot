# Stage 1: Build React app
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies efficiently
COPY package*.json ./
RUN npm ci --silent

# Copy the rest of the source and build
COPY . .
RUN npm run build

# Stage 2: Serve static build with Nginx
FROM nginx:alpine

# Remove default Nginx web files
RUN rm -rf /usr/share/nginx/html/*

# Copy React build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom Nginx config (SPA + correct MIME for .mjs/.js)
RUN cat <<'EOF' > /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Load default MIME types
    include /etc/nginx/mime.types;

    # Explicitly fix MIME type for .js and .mjs
    types {
        application/javascript js mjs;
    }

    #  SPA routing fix (prevents 404 on refresh)
    location / {
        try_files $uri /index.html;
    }

    #  Optional gzip for performance
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/javascript;
    gzip_min_length 256;
}
EOF

# Expose Nginx port
EXPOSE 80

# Run Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
