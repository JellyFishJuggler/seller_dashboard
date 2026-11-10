import asyncio
import base64
import os
import threading
import uuid

import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from sarvamai import (
    AsyncSarvamAI,
    RealtimeAudioInput,
    RealtimeEnd,
    SarvamAI,
)

from seller_dashboard.bot import graph


load_dotenv()

API_KEY = os.getenv("SARVAM_API_KEY")
THREAD_ID = str(uuid.uuid4())

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1600  # 100 ms of audio


def process_seller_message(transcript: str, tts_client: SarvamAI) -> None:
    """Send one transcript to LangGraph, synthesize the reply, and play it."""
    print("\n🤖 Thinking...")

    result = graph.invoke(
        {"messages": [HumanMessage(content=transcript)]},
        config={"configurable": {"thread_id": THREAD_ID}},
    )

    reply = result["messages"][-1].content
    print("\nAssistant:", reply)
    print("\n🔊 Speaking...")

    audio = tts_client.text_to_speech.convert(
        text=reply,
        model="bulbul:v4-flash",
        language_code="hi-IN",
        speaker="ritu_hi_sales",
    )

    audio_bytes = base64.b64decode("".join(audio.audios))

    with open("response.wav", "wb") as output_file:
        output_file.write(audio_bytes)

    data, samplerate = sf.read("response.wav")
    sd.play(data, samplerate)
    sd.wait()


async def main():
    if not API_KEY:
        raise ValueError("SARVAM_API_KEY not found in .env")

    stt_client = AsyncSarvamAI(api_subscription_key=API_KEY)
    tts_client = SarvamAI(api_subscription_key=API_KEY)

    audio_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    # This event is read by the sounddevice callback thread.
    # Clear it while the assistant is speaking to avoid recording its voice.
    mic_enabled = threading.Event()
    mic_enabled.set()

    def audio_callback(indata, frames, time_info, status):
        if status:
            print("Microphone:", status)

        if mic_enabled.is_set():
            audio_bytes = indata.copy().tobytes()
            loop.call_soon_threadsafe(
                audio_queue.put_nowait,
                audio_bytes,
            )

    print("\nConnecting to Sarvam...")

    async with stt_client.speech_to_text_realtime_streaming.connect(
        model="saaras:v4",
        language_code="hi-IN",
        mode="transcribe",
        stream_type="fast",
        endpointing="vad",
        encoding="linear16",
               sample_rate=str(SAMPLE_RATE),
        silence_duration_ms="800",
    ) as ws:
        print("Connected!")
        print("\n🎙️ Listening... Speak naturally. (Ctrl+C to stop)\n")

        async def send_audio():
            while not stop_event.is_set():
                try:
                    chunk = await asyncio.wait_for(
                        audio_queue.get(),
                        timeout=0.2,
                    )
                except asyncio.TimeoutError:
                    continue

                encoded_audio = base64.b64encode(chunk).decode("utf-8")
                await ws.send_realtime_audio_input(
                    RealtimeAudioInput(audio=encoded_audio)
                )

        async def receive_transcript():
            async for message in ws:
                if message.event == "transcript.partial":
                    print(f"\rYou: {message.text}", end="", flush=True)

                elif message.event == "transcript.final":
                    transcript = message.text.strip()
                    if not transcript:
                        continue

                    print(f"\n\nFinal transcript: {transcript}")

                    # Stop collecting mic chunks while the assistant responds.
                    mic_enabled.clear()

                    # Discard chunks captured just before the mic was paused.
                    while not audio_queue.empty():
                        try:
                            audio_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

                    try:
                        await asyncio.to_thread(
                            process_seller_message,
                            transcript,
                            tts_client,
                        )
                    except Exception as error:
                        print(f"\nAI/TTS error: {error}")
                    finally:
                        mic_enabled.set()

                    print("\n🎙️ Listening again...")

                elif message.event == "error":
                    print(
                        f"\nSarvam error: {message.code} - "
                        f"{message.message}"
                    )
                    if message.is_fatal:
                        stop_event.set()
                        return

        sender = asyncio.create_task(send_audio())
        receiver = asyncio.create_task(receive_transcript())

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=BLOCK_SIZE,
                callback=audio_callback,
            ):
                await receiver
        finally:
            stop_event.set()
            sender.cancel()

            try:
                await sender
            except asyncio.CancelledError:
                pass

            await ws.send_realtime_end(RealtimeEnd())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
