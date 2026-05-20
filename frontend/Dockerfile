# Frontend Dockerfile for React + Vite application
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source code
COPY . .

# Expose frontend port
EXPOSE 5173

# Start development server
CMD ["npm", "run", "dev"]