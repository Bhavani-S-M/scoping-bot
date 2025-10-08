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

# Clean existing Nginx web directory
RUN rm -rf /usr/share/nginx/html/*

# Copy React build output
COPY --from=builder /app/dist /usr/share/nginx/html

#  Fix MIME type for .mjs (avoid browser module errors)
RUN sed -i '1i include /etc/nginx/mime.types;' /etc/nginx/conf.d/default.conf && \
    echo "    types { application/javascript js mjs; }" >> /etc/nginx/conf.d/default.conf

# Expose Nginx port
EXPOSE 80

# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
