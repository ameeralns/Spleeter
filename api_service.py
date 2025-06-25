#!/usr/bin/env python3
"""
Vocal Extractor API Microservice
A minimal API that extracts vocals from MP3 files using Demucs
and stores results in Vercel Blob Storage
"""

import os
import secrets
import tempfile
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime
import hashlib

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl
import uvicorn
import httpx
import torch
from demucs.pretrained import get_model
from demucs.apply import apply_model
import librosa
import soundfile as sf
from pydub import AudioSegment
import aiofiles

# Configuration
API_TOKEN = os.getenv("API_TOKEN", None)
VERCEL_BLOB_READ_WRITE_TOKEN = os.getenv("VERCEL_BLOB_READ_WRITE_TOKEN")
VERCEL_BLOB_STORE_ID = os.getenv("VERCEL_BLOB_STORE_ID", "")

# Validate environment variables
if not API_TOKEN:
    # Generate a token if not provided
    API_TOKEN = secrets.token_urlsafe(32)
    print(f"⚠️  No API_TOKEN found in environment. Generated token: {API_TOKEN}")
    print("   Set this token as API_TOKEN environment variable in production!")

if not VERCEL_BLOB_READ_WRITE_TOKEN:
    raise ValueError("VERCEL_BLOB_READ_WRITE_TOKEN environment variable is required!")

# Initialize FastAPI app
app = FastAPI(
    title="Vocal Extractor API",
    description="Extract vocals from MP3 files using Demucs",
    version="1.0.0"
)

# Security
security = HTTPBearer()

# Load model once at startup
print("Loading Demucs model...")
MODEL = get_model('htdemucs')
print("Model loaded successfully!")

# Request/Response models
class ExtractVocalsRequest(BaseModel):
    mp3_url: HttpUrl

class ExtractVocalsResponse(BaseModel):
    vocals_url: str
    processing_time_seconds: float

# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return credentials.credentials

# Helper functions
async def download_file(url: str, destination: Path):
    """Download file from URL to destination"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    async with httpx.AsyncClient() as client:
        try:
            print(f"Downloading file from: {url}")
            response = await client.get(url, headers=headers, follow_redirects=True, timeout=30.0)
            response.raise_for_status()
            
            async with aiofiles.open(destination, 'wb') as f:
                await f.write(response.content)
            print("File download complete.")
        except httpx.RequestError as e:
            print(f"HTTP Request error for {e.request.url}: {e}")
            raise HTTPException(status_code=400, detail=f"Error downloading file: Network error accessing URL.")
        except httpx.HTTPStatusError as e:
            print(f"HTTP Status error for {e.request.url}: {e.response.status_code}")
            raise HTTPException(status_code=400, detail=f"Error downloading file: Server returned status {e.response.status_code}.")

async def upload_to_vercel_blob(file_path: Path, filename: str) -> str:
    """Upload file to Vercel Blob Storage"""
    async with aiofiles.open(file_path, 'rb') as f:
        file_content = await f.read()

    # The final public path we want for our file
    blob_path = f"vocals/{filename}"

    # Vercel's API endpoint for uploads
    upload_url = "https://blob.vercel-storage.com"

    headers = {
        "Authorization": f"Bearer {VERCEL_BLOB_READ_WRITE_TOKEN}",
        "x-api-version": "6",
        # We specify the desired public path in this header
        "x-vercel-blob-pathname": blob_path,
    }

    if VERCEL_BLOB_STORE_ID:
        headers["x-vercel-blob-store-id"] = VERCEL_BLOB_STORE_ID

    async with httpx.AsyncClient() as client:
        response = await client.put(
            upload_url,
            content=file_content,
            headers=headers,
            timeout=60.0
        )
        response.raise_for_status()

        # The Vercel API response is unreliable for getting the final URL.
        # So, we will construct it manually from the response.
        data = response.json()
        print(f"Vercel Blob response: {data}")

        # The response `url` field gives us the base URL of our blob store.
        # e.g., "https://a0vjuoiakesdfbzi.public.blob.vercel-storage.com"
        # We combine it with our desired `blob_path` to create the final, correct URL.
        
        base_url = data.get("url")
        if not base_url:
            raise ValueError(f"Could not determine base URL from Vercel response: {data}")

        # Construct the correct public URL
        # Example: "https://<store_url>/vocals/yourfile.mp3"
        final_url = f"{base_url.split('/api/put')[0]}/{blob_path}"
        
        return final_url

def extract_vocals_sync(input_path: Path, output_path: Path):
    """Synchronous vocal extraction using Demucs"""
    # Load audio
    audio_data, sample_rate = librosa.load(str(input_path), sr=None, mono=False)
    
    # Convert to torch tensor and ensure stereo format
    if audio_data.ndim == 1:
        waveform = torch.from_numpy(audio_data).unsqueeze(0).repeat(2, 1)
    else:
        waveform = torch.from_numpy(audio_data)
        if waveform.shape[0] == 1:
            waveform = waveform.repeat(2, 1)
        elif waveform.shape[0] > 2:
            waveform = waveform[:2]
    
    # Apply the model
    with torch.no_grad():
        sources = apply_model(MODEL, waveform[None], device='cpu')[0]
    
    # Extract vocals (4th source)
    vocals = sources[3]
    
    # Save as WAV first
    temp_wav = output_path.with_suffix('.wav')
    sf.write(str(temp_wav), vocals.T.numpy(), sample_rate)
    
    # Convert to MP3
    audio = AudioSegment.from_wav(str(temp_wav))
    audio.export(str(output_path), format="mp3", bitrate="192k")
    
    # Clean up temp WAV
    temp_wav.unlink()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model_loaded": MODEL is not None}

@app.post("/extract-vocals", response_model=ExtractVocalsResponse)
async def extract_vocals(
    request: ExtractVocalsRequest,
    token: str = Depends(verify_token)
):
    """
    Extract vocals from an MP3 file.
    
    - **mp3_url**: URL of the MP3 file to process
    - **Authorization**: Bearer token required
    
    Returns the URL of the extracted vocals MP3 file stored in Vercel Blob.
    """
    start_time = datetime.now()
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # Generate unique filename based on URL hash
            url_hash = hashlib.md5(str(request.mp3_url).encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Download input file
            input_file = temp_path / f"input_{url_hash}.mp3"
            await download_file(str(request.mp3_url), input_file)
            
            # Process vocals
            output_file = temp_path / f"vocals_{url_hash}_{timestamp}.mp3"
            
            # Run sync operation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                extract_vocals_sync,
                input_file,
                output_file
            )
            
            # Upload to Vercel Blob
            vocals_url = await upload_to_vercel_blob(
                output_file,
                output_file.name
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ExtractVocalsResponse(
                vocals_url=vocals_url,
                processing_time_seconds=processing_time
            )
            
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error downloading file: {e.response.status_code}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Processing error: {str(e)}"
            )

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    print(f"🚀 Vocal Extractor API starting on port 8000")
    print(f"📋 API Token: {API_TOKEN[:8]}...{API_TOKEN[-8:]}")
    print(f"☁️  Vercel Blob configured: {'✅' if VERCEL_BLOB_READ_WRITE_TOKEN else '❌'}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 