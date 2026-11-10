
from sarvamai import SarvamAI
from langchain_core.messages import HumanMessage
import sounddevice as sd
import soundfile as sf
from seller_dashboard.bot import graph
from dotenv import load_dotenv
import uuid
import os
import base64
import time


load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

THREAD_ID = str(uuid.uuid4())

# 1. Speech to Text
print("\n[1/4] Processing your audio...")

with open("input.wav", "rb") as audio_file:
    response = client.speech_to_text.transcribe(
        file=audio_file,
        model="saaras:v4",
        mode="transcribe"
    )

transcript = response.transcript

print("\nYou:", transcript)
print("\n[2/4] STT completed. Sending to AI...")

# 2. LangGraph + Ollama

start_time = time.time()
result = graph.invoke(
    {"messages": [HumanMessage(content=transcript)]},
    config={
        "configurable": {
            "thread_id": THREAD_ID
        }
    }
)

print(f"[DEBUG] Graph completed in {time.time() - start_time:.2f} seconds")

assistant_reply = result["messages"][-1].content

print("\n[3/4] AI response generated.")
print("\nAssistant:", assistant_reply)

# 3. Text to Speech
print("\nGenerating voice response...")

audio = client.text_to_speech.convert(
    text=assistant_reply,
    model="bulbul:v4-flash",
    language_code="hi-IN",
    speaker="ritu_hi_sales"
)

print("[4/4] TTS completed.")

# 4. Save generated audio
audio_bytes = base64.b64decode("".join(audio.audios))

with open("response.wav", "wb") as output_file:
    output_file.write(audio_bytes)

print("\nVoice response saved as response.wav")

print("\nPlaying AI response...")

data, samplerate = sf.read("response.wav")

sd.play(data, samplerate)
sd.wait()

print("Playback completed.")