#!/bin/bash
# Docker deployment script for Vocal Extractor API

echo "🐳 Vocal Extractor API Docker Deployment"
echo "========================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Installing Docker..."
    
    # Install Docker on Amazon Linux 2
    sudo amazon-linux-extras install docker -y
    sudo service docker start
    sudo usermod -a -G docker ec2-user
    
    echo "⚠️  Docker installed! Please logout and login again, then run this script again."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing docker-compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Generate API token if not exists
if [ -z "$API_TOKEN" ] && [ ! -f .env ]; then
    echo "🔐 Generating API token..."
    python3 generate_token.py
    echo ""
    read -p "Copy the API token above and press Enter to continue..."
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
API_TOKEN=${API_TOKEN}
VERCEL_BLOB_READ_WRITE_TOKEN=${VERCEL_BLOB_READ_WRITE_TOKEN}
VERCEL_BLOB_STORE_ID=${VERCEL_BLOB_STORE_ID}
EOF
    echo "⚠️  Please edit .env file and add your tokens!"
    nano .env
fi

# Build and start the container
echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Starting the service..."
docker-compose up -d

# Wait for service to be ready
echo "⏳ Waiting for service to start..."
sleep 10

# Check if service is running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Service is running!"
    
    # Get public IP
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo "localhost")
    
    echo ""
    echo "📊 Service Status:"
    docker-compose ps
    
    echo ""
    echo "📝 Useful commands:"
    echo "  View logs:    docker-compose logs -f"
    echo "  Stop service: docker-compose down"
    echo "  Restart:      docker-compose restart"
    echo ""
    echo "🔒 Your API endpoint: http://$PUBLIC_IP:8000"
    echo ""
    echo "🧪 Test with: curl http://localhost:8000/health"
else
    echo "❌ Service failed to start. Check logs with: docker-compose logs"
    exit 1
fi 