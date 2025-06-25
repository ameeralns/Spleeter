#!/usr/bin/env python3
"""
Vocal Extractor using Demucs
Extracts vocals from audio files using the Demucs library.
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import torch
    import torchaudio
    import librosa
    import soundfile as sf
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    from demucs.audio import save_audio
except ImportError:
    print("Error: Required libraries not installed. Please run: pip install -r requirements.txt")
    sys.exit(1)

def extract_vocals(input_file, output_dir="output"):
    """
    Extract vocals from an audio file using Demucs
    
    Args:
        input_file (str): Path to the input audio file
        output_dir (str): Directory to save the output files
    """
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        return False
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        print(f"Processing: {input_file}")
        
        # Load the pre-trained model (htdemucs is good for vocals)
        print("Loading Demucs model...")
        model = get_model('htdemucs')
        
        # Load the audio file using librosa (more reliable for various formats)
        print("Loading audio file...")
        audio_data, sample_rate = librosa.load(input_file, sr=None, mono=False)
        
        # Convert to torch tensor and ensure stereo format
        if audio_data.ndim == 1:
            # Mono to stereo
            waveform = torch.from_numpy(audio_data).unsqueeze(0).repeat(2, 1)
        else:
            # Already stereo or multi-channel
            waveform = torch.from_numpy(audio_data)
            if waveform.shape[0] == 1:
                waveform = waveform.repeat(2, 1)
            elif waveform.shape[0] > 2:
                waveform = waveform[:2]
        
        # Apply the model
        print("Separating audio tracks...")
        with torch.no_grad():
            sources = apply_model(model, waveform[None], device='cpu')[0]
        
        # The sources are: [drums, bass, other, vocals]
        drums, bass, other, vocals = sources
        
        # Extract the base filename without extension
        base_name = Path(input_file).stem
        
        # Save the vocals track
        vocals_output = os.path.join(output_dir, f"{base_name}_vocals.wav")
        save_audio(vocals, vocals_output, sample_rate)
        
        # Create accompaniment by summing non-vocal sources
        accompaniment = drums + bass + other
        accompaniment_output = os.path.join(output_dir, f"{base_name}_accompaniment.wav")
        save_audio(accompaniment, accompaniment_output, sample_rate)
        
        print(f"✅ Vocals extracted successfully!")
        print(f"   Vocals saved to: {vocals_output}")
        print(f"   Accompaniment saved to: {accompaniment_output}")
        
        return True
        
    except Exception as e:
        print(f"Error processing audio: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Extract vocals from audio files using Demucs")
    parser.add_argument("input_file", help="Input audio file path")
    parser.add_argument("-o", "--output", default="output", help="Output directory (default: output)")
    parser.add_argument("--vocals-only", action="store_true", help="Save only vocals track")
    
    args = parser.parse_args()
    
    print("🎵 Vocal Extractor using Demucs")
    print("=" * 40)
    
    success = extract_vocals(args.input_file, args.output)
    
    if success:
        print("\n🎉 Processing completed successfully!")
    else:
        print("\n❌ Processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 