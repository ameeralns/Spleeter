# Vocal Extractor API

A scalable API microservice that uses Demucs to extract vocals from audio files, with Vercel Blob storage integration.

## Features

- 🎵 High-quality vocal extraction using Demucs
- 🔐 Token-based authentication
- ☁️ Vercel Blob storage integration
- 🚀 FastAPI-based microservice
- 📊 Processing time tracking
- 🏃 Async processing for scalability

## API Documentation

### Base URL
```
http://your-aws-instance:8000
```

### Authentication
All API requests require a Bearer token in the Authorization header:
```
Authorization: Bearer YOUR_API_TOKEN
```

### Endpoints

#### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

#### Extract Vocals
```http
POST /extract-vocals
Content-Type: application/json
Authorization: Bearer YOUR_API_TOKEN

{
  "mp3_url": "https://example.com/audio.mp3"
}
```

Response:
```json
{
  "vocals_url": "https://your-blob-store.vercel-storage.com/vocals/vocals_abc123_20240101_120000.mp3",
  "processing_time_seconds": 15.4
}
```

Error Response:
```json
{
  "detail": "Error message"
}
```

### Status Codes
- `200` - Success
- `400` - Bad Request (invalid URL, download failed)
- `401` - Unauthorized (invalid token)
- `422` - Validation Error (invalid request format)
- `500` - Internal Server Error

## Installation

### Prerequisites
- Python 3.8+
- ffmpeg (for pydub MP3 support)

### Setup

1. Clone the repository:
```bash
git clone <your-repo>
cd vocalExtractor
```

2. Install system dependencies:
```bash
# Amazon Linux 2/2023
sudo yum update -y
sudo yum install -y python3 python3-pip python3-devel gcc
sudo amazon-linux-extras install epel -y
sudo yum install -y ffmpeg ffmpeg-devel

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg
```

3. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
```

4. Install Python dependencies:
```bash
pip install -r requirements.txt
```

5. Generate API token:
```bash
python generate_token.py
```

6. Set environment variables:
```bash
export API_TOKEN="your_generated_token"
export VERCEL_BLOB_READ_WRITE_TOKEN="vercel_blob_rw_xxxxx"
export VERCEL_BLOB_STORE_ID="your_store_id"  # Optional
```

## Running the API

### Development
```bash
python api_service.py
```

### Production (AWS EC2)

#### Quick Deploy (Amazon Linux)
```bash
# Set your Vercel token first
export VERCEL_BLOB_READ_WRITE_TOKEN="your_vercel_token_here"

# Run the deployment script
chmod +x deploy.sh
./deploy.sh
```

#### Manual Setup

1. Copy the systemd service file:
```bash
sudo cp vocal-extractor.service /etc/systemd/system/
```

2. Edit the service file with your tokens:
```bash
sudo nano /etc/systemd/system/vocal-extractor.service
# Update API_TOKEN and VERCEL_BLOB_READ_WRITE_TOKEN
# Update paths if not using default /home/ec2-user/vocalExtractor
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vocal-extractor
sudo systemctl start vocal-extractor
```

4. Check status:
```bash
sudo systemctl status vocal-extractor
sudo journalctl -u vocal-extractor -f  # View logs
```

5. Configure AWS Security Group to allow port 8000:
   - Go to EC2 Dashboard > Security Groups
   - Select your instance's security group
   - Add inbound rule: Type=Custom TCP, Port=8000, Source=0.0.0.0/0

## Client Usage Example

### JavaScript/TypeScript
```javascript
const API_URL = 'http://your-aws-instance:8000';
const API_TOKEN = 'your_api_token';

async function extractVocals(mp3Url) {
  const response = await fetch(`${API_URL}/extract-vocals`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_TOKEN}`
    },
    body: JSON.stringify({ mp3_url: mp3Url })
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return await response.json();
}

// Usage
try {
  const result = await extractVocals('https://example.com/song.mp3');
  console.log('Vocals URL:', result.vocals_url);
  console.log('Processing time:', result.processing_time_seconds, 'seconds');
} catch (error) {
  console.error('Error:', error);
}
```

### Python
```python
import requests

API_URL = 'http://your-aws-instance:8000'
API_TOKEN = 'your_api_token'

def extract_vocals(mp3_url):
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        f'{API_URL}/extract-vocals',
        json={'mp3_url': mp3_url},
        headers=headers
    )
    
    response.raise_for_status()
    return response.json()

# Usage
result = extract_vocals('https://example.com/song.mp3')
print(f"Vocals URL: {result['vocals_url']}")
print(f"Processing time: {result['processing_time_seconds']} seconds")
```

### cURL
```bash
curl -X POST http://your-aws-instance:8000/extract-vocals \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mp3_url": "https://example.com/song.mp3"}'
```

## Performance Notes

- First request will be slower as the model loads into memory
- Subsequent requests will be faster (model cached)
- Processing time depends on audio length and server resources
- Recommended: Use at least t3.large EC2 instance for better performance

## Vercel Blob Storage Setup

1. Create a Vercel account and project
2. Enable Blob storage in your project
3. Generate a Read/Write token from the Vercel dashboard
4. All vocals will be stored in the `/vocals/` directory in your blob store

## Security Considerations

- Always use HTTPS in production (set up with nginx/Apache reverse proxy)
- Keep your API token secure
- Rotate tokens regularly
- Consider rate limiting for production use
- Monitor usage and costs

## Troubleshooting

### Model Download Issues
The first run will download the Demucs model (~300MB). Ensure you have:
- Stable internet connection
- Sufficient disk space
- Write permissions in the cache directory

### Memory Issues
If you encounter memory errors:
- Increase instance size
- Adjust `MemoryMax` in systemd service file
- Consider using GPU instance for faster processing

### Audio Format Issues
- Ensure input URLs point to valid MP3 files
- The service handles most common MP3 encodings
- Large files (>100MB) may timeout - consider increasing timeouts

### Amazon Linux Specific Issues
- If ffmpeg installation fails, ensure EPEL repository is enabled
- For Python issues, ensure python3-devel is installed
- Check SELinux status if service fails to start: `sudo getenforce`

## Original CLI Tool

The original command-line vocal extractor is still available:
```bash
python vocal_extractor.py "input.mp3"
```

See the previous documentation section for CLI usage. 