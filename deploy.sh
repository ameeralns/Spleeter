#!/bin/bash
# Deployment script for Vocal Extractor API on AWS EC2 (Amazon Linux)

echo "🚀 Vocal Extractor API Deployment Script (Amazon Linux)"
echo "======================================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "Please don't run this script as root (use ec2-user instead)"
   exit 1
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo yum update -y
sudo yum install -y python3 python3-pip python3-devel gcc

# Install ffmpeg from EPEL repository
echo "🎵 Installing ffmpeg..."
sudo amazon-linux-extras install epel -y
sudo yum install -y ffmpeg ffmpeg-devel

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Generate API token if not exists
if [ -z "$API_TOKEN" ]; then
    echo "🔐 Generating API token..."
    python generate_token.py
    echo ""
    read -p "Copy the API token above and press Enter to continue..."
fi

# Check for Vercel token
if [ -z "$VERCEL_BLOB_READ_WRITE_TOKEN" ]; then
    echo "⚠️  VERCEL_BLOB_READ_WRITE_TOKEN not found!"
    echo "Please set it before continuing:"
    echo "export VERCEL_BLOB_READ_WRITE_TOKEN='your_token_here'"
    exit 1
fi

# Copy and configure systemd service
echo "⚙️  Setting up systemd service..."
sudo cp vocal-extractor.service /etc/systemd/system/

# Update the service file with environment variables
sudo sed -i "s/YOUR_API_TOKEN_HERE/$API_TOKEN/g" /etc/systemd/system/vocal-extractor.service
sudo sed -i "s/YOUR_VERCEL_TOKEN_HERE/$VERCEL_BLOB_READ_WRITE_TOKEN/g" /etc/systemd/system/vocal-extractor.service

# Update the user and paths in service file
CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)
sudo sed -i "s/User=ubuntu/User=$CURRENT_USER/g" /etc/systemd/system/vocal-extractor.service
sudo sed -i "s|/home/ubuntu/vocalExtractor|$CURRENT_DIR|g" /etc/systemd/system/vocal-extractor.service

# Reload and start service
echo "🏃 Starting the service..."
sudo systemctl daemon-reload
sudo systemctl enable vocal-extractor
sudo systemctl start vocal-extractor

# Check status
sleep 2
sudo systemctl status vocal-extractor --no-pager

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Ensure port 8000 is open in your AWS Security Group"
echo "2. Test the API with: curl http://localhost:8000/health"
echo "3. View logs with: sudo journalctl -u vocal-extractor -f"
echo ""

# Get public IP using IMDSv2
TOKEN=`curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null`
PUBLIC_IP=`curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null`
echo "🔒 Your API endpoint: http://$PUBLIC_IP:8000" 