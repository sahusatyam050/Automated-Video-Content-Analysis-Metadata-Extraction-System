import io
import subprocess
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException

app = FastAPI(title="Pro STT Service (16kHz Mono)")

# IMPORTANT: Ensure this matches your actual Whisper/STT backend IP and port
STT_BACKEND_URL = "http://10.94.157.37:5000/whisper"

def process_audio(input_bytes: bytes) -> bytes:
    """
    Uses the system FFmpeg (via subprocess) to convert input audio bytes 
    to 16kHz, mono, wav format (PCM 16-bit).
    """
    command = [
        'ffmpeg',
        '-i', 'pipe:0',             # Read from stdin
        '-f', 'wav',                # Output format wav
        '-acodec', 'pcm_s16le',     # Audio codec
        '-ac', '1',                 # Mono (1 channel)
        '-ar', '16000',             # Sample rate 16kHz
        'pipe:1'                    # Write to stdout
    ]

    try:
        # We call the ffmpeg command directly
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Feed the raw bytes and get the converted output
        out, err = process.communicate(input=input_bytes)
        
        if process.returncode != 0:
            error_msg = err.decode() if err else "Unknown FFmpeg error"
            print(f"FFmpeg Error: {error_msg}")
            raise Exception(error_msg)
            
        return out

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"FFmpeg conversion failed: {str(e)}")

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    try:
        # 1. Read raw uploaded file bytes
        raw_content = await file.read()
        
        # 2. Convert to 16kHz Mono via system FFmpeg
        processed_content = process_audio(raw_content)
        
        # 3. Prepare the converted audio for the STT backend
        files = {
            'file': (file.filename, io.BytesIO(processed_content), 'audio/wav')
        }
        data = {"response_format": "json"}

        # 4. Forward to your transcription backend
        response = requests.post(STT_BACKEND_URL, files=files, data=data, timeout=1200)
        response.raise_for_status()
        print(response.json().get("text"))
        return {
            "filename": file.filename,
            "transcription": response.json().get("text", ""),
            "parameters": "16kHz, Mono, PCM16",
            "status": "success"
        }
        

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"STT Backend Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        await file.close()

if __name__ == "__main__":
    import uvicorn
    # This allows you to run the file directly with 'python whisper_services.py'
    uvicorn.run(app, host="0.0.0.0", port=8001)