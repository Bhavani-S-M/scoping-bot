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
# Stage 2: Serve static build with Nginx
# -------------------------------
FROM nginx:alpine

# Clean existing Nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy React build output
COPY --from=builder /app/dist /usr/share/nginx/html

# ✅ Reliable multiline Nginx config (fixes SPA + .mjs)
RUN cat <<'EOF' > /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # --- SPA routing fix (prevents 404 on refresh) ---
    location / {
        try_files $uri /index.html;
    }

    # --- Fix MIME type for modern JS modules (.mjs) ---
    location ~* \.(mjs|js)$ {
        add_header Content-Type application/javascript;
    }

    # --- Optional performance tuning ---
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/javascript;
    gzip_min_length 256;
}
EOF

# Expose Nginx port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
