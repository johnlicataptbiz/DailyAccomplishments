FROM node:20-alpine AS runtime

# Set working directory
WORKDIR /app

# Copy static site contents
COPY . /app

# Install a simple static server
RUN npm i -g serve

# Railway typically provides PORT; default to 8080 for local
ENV PORT=8080
EXPOSE 8080

# Serve the current directory statically
CMD ["sh", "-c", "serve -n -s -l ${PORT} ."]

