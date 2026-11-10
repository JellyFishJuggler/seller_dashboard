from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sarvamai import RealtimeAudioInput, RealtimeEnd
from fastapi.middleware.cors import CORSMiddleware
from seller_dashboard.bot import graph
from pydantic import BaseModel
import asyncio
import base64   
from langchain_core.messages import HumanMessage, AIMessage
import os

from seller_dashboard.tools import (
    get_seller_metrics,
    get_out_of_stock_products,
    record_findings,
    create_action,
    get_call_summary,
    get_playbook,
)

from seller_dashboard.voice import VoiceAssistant

app = FastAPI()
voiceAssistant = VoiceAssistant()

API_KEY = os.getenv("SARVAM_API_KEY")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class VoiceRequest(BaseModel):
    session_id:str
    seller_id:str
    message:str


@app.get('/')
def home():
    return {"message":"SnapDeal Seller API is running."}

@app.post('/chat')
def chat(request:VoiceRequest):

    config = {"configurable":{"thread_id": request.session_id}}

    user_message = f"""
        The current seller ID is {request.seller_id}.
        The seller's message is: {request.message}
    """

    events = graph.stream({"messages":[HumanMessage(user_message)]}, config, stream_mode='values')
    final_mesg = None

    for event in events:
        messages = event.get('messages', [])
        if messages:
            last_msg = messages[-1]

            if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
                final_mesg = last_msg.content

    return {
        "seller_id": request.seller_id,
        "message": final_mesg
    }

@app.get('/dashboard/{seller_id}')
def dashboard(seller_id:str):

    metrics = get_seller_metrics.invoke({"seller_id":seller_id})
    return metrics

@app.get('/inventory/{seller_id}')
def inventory(seller_id:str):

    stocks = get_out_of_stock_products.invoke({"seller_id":seller_id, "onlyNew":False})
    return stocks



@app.websocket("/voice/{session_id}")
async def voice_input(websocket: WebSocket, session_id: str):

    await websocket.accept()
    print(f"Voice session started: {session_id}")

    try:
        async with voiceAssistant.connect_stt() as sarvam_ws:

            async def send_audio():
                """Forward browser audio chunks to Sarvam."""

                while True:
                    audio_chunk = await websocket.receive_bytes()

                    encoded_audio = base64.b64encode(
                        audio_chunk
                    ).decode("utf-8")

                    await sarvam_ws.send_realtime_audio_input(
                        RealtimeAudioInput(audio=encoded_audio)
                    )

            async def receive_transcript():
                """Receive transcripts and generate AI voice responses."""

                async for message in sarvam_ws:

                    if message.event == "transcript.partial":
                        await websocket.send_json({
                            "type": "partial_transcript",
                            "text": message.text
                        })

                    elif message.event == "transcript.final":

                        transcript = message.text.strip()

                        if not transcript:
                            continue

                        print("Seller:", transcript)

                        await websocket.send_json({
                            "type": "assistant_start",
                            "transcript": transcript
                        })

                        try:
                            # Generate LLM response
                            reply = await asyncio.to_thread(
                                voiceAssistant.generate_response,
                                transcript,
                                session_id
                            )

                            print("Assistant:", reply)

                            # Convert response into speech
                            audio_bytes = await asyncio.to_thread(
                                voiceAssistant.generate_audio,
                                reply
                            )

                            # Send text response
                            await websocket.send_json({
                                "type": "assistant_reply",
                                "text": reply
                            })

                            # Send generated audio
                            await websocket.send_bytes(audio_bytes)

                        except Exception as error:
                            print("AI/TTS error:", error)

                            await websocket.send_json({
                                "type": "error",
                                "message": str(error)
                            })

                        finally:
                            await websocket.send_json({
                                "type": "assistant_end"
                            })

                    elif message.event == "error":
                        print(
                            "Sarvam error:",
                            message.code,
                            message.message
                        )

                        if message.is_fatal:
                            return

            sender = asyncio.create_task(send_audio())
            receiver = asyncio.create_task(receive_transcript())

            try:
                await asyncio.gather(sender, receiver)

            finally:
                sender.cancel()
                receiver.cancel()

                await asyncio.gather(
                    sender,
                    receiver,
                    return_exceptions=True
                )

                try:
                    await sarvam_ws.send_realtime_end(RealtimeEnd())
                except Exception:
                    pass

    except WebSocketDisconnect:
        print(f"Voice session disconnected: {session_id}")

    except Exception as error:
        print("Voice connection error:", error)
