from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sarvamai import RealtimeAudioInput, RealtimeEnd
from fastapi.middleware.cors import CORSMiddleware
from websockets.exceptions import ConnectionClosed
from seller_dashboard.bot import graph
from seller_dashboard.sarvam_credentials import (
    advance_client_sarvam_api_key,
    get_client_sarvam_api_key,
    get_client_sarvam_key_status,
    is_sarvam_credential_error,
    set_client_sarvam_api_key,
)
from pydantic import BaseModel
import anyio
import asyncio
import base64   
import logging
import json
import time
from types import SimpleNamespace
from langchain_core.messages import HumanMessage, AIMessage
from asyncio import wait as wait_for_voice_task_completion

from seller_dashboard.tools import (
    get_seller_metrics,
    get_out_of_stock_products,
    record_findings,
    create_action,
    get_actions,
    update_action_status,
    get_call_summary,
    get_playbook,
    register_session_seller,
    is_known_seller,
    normalize_seller_id,
    _resolve_seller_id,
)
from seller_dashboard.conversation_store import (
    save_message,
    get_conversation_history,
    get_seller_conversations,
)
from seller_dashboard.summary_store import (
    generate_call_summary,
    get_call_summary_record,
    get_seller_call_summaries,
)
from seller_dashboard.call_closure import (
    finalize_call_session,
    complete_call_finalization,
    fail_call_finalization,
    build_pending_question_offer,
    has_unanswered_assistant_question,
    is_call_termination_intent,
    is_session_active,
)

from seller_dashboard.voice import VoiceAssistant
from seller_dashboard.voice_diagnostics import (
    EmptyAssistantResponseError,
    clean_transcript,
    extract_request_id,
    has_nonempty_text,
    log_audio_boundary,
    log_text_boundary,
)

app = FastAPI()
voiceAssistant = VoiceAssistant()
logger = logging.getLogger("seller_dashboard.voice")


async def send_realtime_audio_if_open(
    sarvam_ws,
    encoded_audio: str,
    stt_closed: asyncio.Event,
    session_id: str,
) -> bool:
    if stt_closed.is_set():
        return False
    try:
        await sarvam_ws.send_realtime_audio_input(
            RealtimeAudioInput(audio=encoded_audio)
        )
        return True
    except ConnectionClosed as error:
        stt_closed.set()
        logger.warning(
            "Sarvam STT socket closed during audio send session_id=%s error_type=%s",
            session_id,
            type(error).__name__,
        )
        return False


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
    client_id: str = ""


class SarvamKeyRequest(BaseModel):
    client_id: str
    api_key: str = ""


@app.get('/')
def home():
    return {"message":"SnapDeal Seller API is running."}


@app.get('/settings/sarvam-key')
def read_sarvam_key_status(client_id: str):
    """Return only the masked key status for the requesting browser profile."""
    return get_client_sarvam_key_status(client_id)


@app.get('/settings/sarvam-key/diagnostics')
def read_sarvam_key_diagnostics(client_id: str):
    """Report browser-profile key selection without exposing credentials."""
    status = get_client_sarvam_key_status(client_id)
    return {
        "client_key_source": status["source"],
        "client_key_configured": status["configured"],
        "scope": "browser_profile",
        "clients": "created for each request",
    }


@app.post('/settings/sarvam-key')
def update_sarvam_key(request: SarvamKeyRequest):
    """Save, replace, or clear the custom Sarvam key.

    An empty value clears only this browser profile's override and falls back to the
    deployment-configured key.
    """
    try:
        status = set_client_sarvam_api_key(request.client_id, request.api_key)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OSError as error:
        logger.exception(
            "Could not save the Sarvam API key on the backend error_type=%s errno=%s",
            type(error).__name__,
            error.errno,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "The backend cannot write its private API-key storage (neither "
                "the app-data location nor the project private/ "
                "directory is writable). Set SARVAM_CREDENTIALS_PATH to a "
                "writable persistent file path for this backend, then try again."
            ),
        ) from error

    logger.info(
        "Saved browser-profile Sarvam key source=%s",
        status["source"],
    )
    return status

@app.post('/chat')
def chat(request:VoiceRequest):
    log_text_boundary("FastAPI /chat input -> LangGraph", request.session_id, request.message)
    if not has_nonempty_text(request.message):
        raise HTTPException(status_code=422, detail="Message cannot be empty.")

    register_session_seller(request.session_id, request.seller_id)
    config = {
        "configurable": {
            "thread_id": request.session_id,
            "seller_id": request.seller_id,
            "client_id": request.client_id or request.session_id,
        }
    }

    if not is_session_active(request.session_id):
        raise HTTPException(status_code=400, detail="This conversation session has already ended.")

    # Persist incoming seller text message
    seller_save = save_message(
        seller_id=request.seller_id,
        session_id=request.session_id,
        speaker="seller",
        message_text=request.message,
        channel="text",
    )
    if not seller_save.get("saved") and not seller_save.get("duplicate"):
        raise HTTPException(status_code=500, detail="Seller message could not be saved.")

    if is_call_termination_intent(request.message):
        finalization = finalize_call_session(
            seller_id=request.seller_id,
            session_id=request.session_id,
            channel="text",
        )
        return {
            "seller_id": request.seller_id,
            "message": finalization.get("final_message", "Thank you for speaking with Snapdeal. Goodbye!"),
            "call_ended": finalization.get("success", False),
            "status": finalization.get("status", "failed"),
            "error": finalization.get("error"),
            "summary_id": (finalization.get("summary") or {}).get("summary_id"),
        }

    user_message = f"""
        The current seller ID is {request.seller_id}.
        The seller's message is: {request.message}
    """

    config["configurable"]["voice_mode"] = False
    events = graph.stream({"messages":[HumanMessage(user_message)]}, config, stream_mode='values')
    final_mesg = None

    for event in events:
        messages = event.get('messages', [])
        if messages:
            last_msg = messages[-1]

            if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
                final_mesg = last_msg.content

    log_text_boundary("FastAPI /chat response", request.session_id, final_mesg)

    # Persist final assistant text response
    if has_nonempty_text(final_mesg):
        assistant_save = save_message(
            seller_id=request.seller_id,
            session_id=request.session_id,
            speaker="assistant",
            message_text=final_mesg,
            channel="text",
        )
        if not assistant_save.get("saved") and not assistant_save.get("duplicate"):
            raise HTTPException(status_code=500, detail="Assistant response could not be saved.")

    return {
        "seller_id": request.seller_id,
        "message": final_mesg
    }

def _seller_tool_response(result: dict):
    """Translate structured seller-tool errors into proper HTTP responses."""
    if isinstance(result, dict) and result.get("error"):
        status_code = 404 if result.get("code") in {
            "seller_not_found",
            "seller_id_required",
        } else 500
        return JSONResponse(status_code=status_code, content=result)
    return result


@app.get('/dashboard/{seller_id}')
def dashboard(seller_id:str):

    try:
        metrics = get_seller_metrics.invoke({"seller_id":seller_id})
    except Exception:
        logger.exception("Could not load seller dashboard metrics")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "code": "dashboard_unavailable",
                "message": "Seller metrics are temporarily unavailable.",
            },
        )
    return _seller_tool_response(metrics)


@app.get('/inventory/{seller_id}')
def inventory(seller_id:str):

    try:
        stocks = get_out_of_stock_products.invoke({"seller_id":seller_id, "onlyNew":False})
    except Exception:
        logger.exception("Could not load seller inventory")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "code": "inventory_unavailable",
                "message": "Seller inventory is temporarily unavailable.",
            },
        )
    return _seller_tool_response(stocks)


class ActionUpdateRequest(BaseModel):
    action_id: str
    status: str
    seller_id: str | None = None
    notes: str = ""


@app.get('/actions/{seller_id}')
def list_actions(seller_id: str, status: str | None = None, session_id: str | None = None):
    return get_actions.invoke(
        {"seller_id": seller_id, "status": status or "", "session_id": session_id or ""},
        config={"configurable": {"thread_id": session_id or "api", "seller_id": seller_id}},
    )


@app.post('/actions/update')
def update_action(req: ActionUpdateRequest):
    res = update_action_status.invoke(
        {
            "action_id": req.action_id,
            "status": req.status,
            "seller_id": req.seller_id or "",
            "notes": req.notes,
        },
        config={"configurable": {"thread_id": "api", "seller_id": req.seller_id or ""}},
    )
    if not res.get("updated"):
        raise HTTPException(status_code=400, detail=res.get("message", "Update failed"))
    return res


@app.get('/conversations/{seller_id}')
def list_conversations(seller_id: str, session_id: str | None = None):
    if session_id:
        history = get_conversation_history(session_id=session_id, seller_id=seller_id)
        return {
            "seller_id": seller_id,
            "session_id": session_id,
            "messages": history,
            "count": len(history),
        }
    sessions = get_seller_conversations(seller_id=seller_id)
    return {
        "seller_id": seller_id,
        "sessions": sessions,
        "count": len(sessions),
    }


@app.get('/call-summaries/{seller_id}')
def list_call_summaries(seller_id: str, session_id: str | None = None):
    if session_id:
        summary = get_call_summary_record(session_id=session_id, seller_id=seller_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Call summary not found.")
        return summary
    summaries = get_seller_call_summaries(seller_id=seller_id)
    return {
        "seller_id": seller_id,
        "summaries": summaries,
        "count": len(summaries),
    }



_STT_QUOTA_MARKERS = (
    "quota",
    "billing",
    "payment_required",
    "insufficient credit",
    "credits exhausted",
    "credit limit",
)
_STT_AUTH_MARKERS = (
    "unauthorized",
    "invalid_api_key",
    "invalid api key",
    "invalid subscription key",
    "1003",
    "authentication",
    "forbidden",
    "401",
    "403",
)

# If Sarvam emits partials but never a final transcript (VAD stuck on room
# noise or an empty final), finalize the last stable partial after this grace
# period. A hard cap prevents an utterance from listening forever.
VOICE_PARTIAL_FINAL_GRACE_SECONDS = 4.0
VOICE_PARTIAL_MAX_UTTERANCE_SECONDS = 12.0
VOICE_FINAL_WATCH_INTERVAL_SECONDS = 0.5


def _stt_failure_payload(
    code: str,
    detail: str = "",
    client_id: str = "",
) -> tuple[str, str]:
    """Classify a fatal STT failure without exposing credentials."""
    text = f"{code or ''} {detail or ''}".lower()

    if any(marker in text for marker in _STT_QUOTA_MARKERS):
        if get_client_sarvam_key_status(client_id).get("source") == "custom":
            message = (
                "सहेजी गई custom API key की speech recognition सीमा पूरी हो गई है। "
                "उसका API plan या credits जाँचें, या Settings में custom key हटाकर "
                ".env वाली key इस्तेमाल करें।"
            )
        else:
            message = (
                "Sarvam speech recognition की सीमा पूरी हो गई है। अपना API plan "
                "जाँचें या Settings में दूसरी API key दर्ज करें।"
            )
        return "stt_quota_exceeded", message

    if any(marker in text for marker in _STT_AUTH_MARKERS):
        return "stt_auth_failed", (
            "Sarvam ने speech recognition API key स्वीकार नहीं की। Settings में "
            "key अपडेट करके फिर कोशिश करें।"
        )

    return "stt_connection_closed", (
        "Speech recognition का connection टूट गया। आपकी बातचीत सुरक्षित है; "
        "जारी रखने के लिए voice फिर शुरू करें।"
    )


@app.websocket("/voice/{session_id}")
async def voice_input(
    websocket: WebSocket,
    session_id: str,
    seller_id: str = "",
    client_id: str = "",
):

    await websocket.accept()
    logger.info("Voice WebSocket session started session_id=%s", session_id)

    # Bind the portal's loaded seller to this voice session so the very first
    # spoken turn is answered from that seller's data instead of falling back
    # to the default seller. Unknown IDs stay unbound; the agent will ask.
    requested_seller = normalize_seller_id(seller_id)
    if requested_seller and is_known_seller(requested_seller):
        register_session_seller(session_id, requested_seller)
        logger.info(
            "Voice session seller bound session_id=%s seller_id=%s",
            session_id,
            requested_seller,
        )
    elif requested_seller:
        logger.info(
            "Voice session seller id unknown, left unbound session_id=%s requested=%s",
            session_id,
            requested_seller,
        )

    playback_complete = asyncio.Event()
    playback_failed = asyncio.Event()
    turn_playback_ack = asyncio.Event()
    finalization_lock = asyncio.Lock()
    finalization_started = asyncio.Event()
    stt_closed = asyncio.Event()
    assistant_busy = asyncio.Event()
    turn_tasks: set[asyncio.Task] = set()
    processed_request_ids: set[str] = set()
    partial_request_ids: set[str] = set()
    processed_utterances: set[int] = set()
    pending_partial = {
        "utterance_idx": None,
        "request_id": None,
        "text": "",
        "changed_at": 0.0,
        "started_at": 0.0,
        "speech_ended_at": 0.0,
    }
    fallback_transcripts: dict[str, float] = {}
    fallback_request_ids: dict[str, float] = {}
    fallback_utterance_ids: dict[int, float] = {}
    fallback_unkeyed_final_pending = False
    stt_event_queue: asyncio.Queue = asyncio.Queue()
    stt_stream_end = object()
    last_unkeyed_partial_at = 0.0
    silence_frame = base64.b64encode(b"\x00" * 3200).decode("ascii")
    stt_failure = {"code": "", "detail": ""}
    stt_started = False

    async def send_stt_audio(encoded_audio: str) -> bool:
        return await send_realtime_audio_if_open(
            sarvam_ws,
            encoded_audio,
            stt_closed,
            session_id,
        )

    async def send_recoverable_stt_error() -> None:
        failed_key = get_client_sarvam_api_key(client_id or session_id)
        failure = RuntimeError(
            f"{stt_failure['code']} {stt_failure['detail']}"
        )
        fallback_key = (
            advance_client_sarvam_api_key(client_id or session_id, failed_key)
            if failed_key and is_sarvam_credential_error(failure)
            else None
        )
        code, message = _stt_failure_payload(
            stt_failure["code"],
            stt_failure["detail"],
            client_id or session_id,
        )
        logger.warning(
            "Sarvam STT unavailable session_id=%s code=%s",
            session_id,
            code,
        )
        if fallback_key:
            message += " दूसरी configured API key इस्तेमाल करने के लिए voice फिर शुरू करें।"
        try:
            await websocket.send_json({
                "type": "error",
                "code": code,
                "recoverable": True,
                "message": message,
            })
            await websocket.close(code=1012, reason="Speech recognition unavailable")
        except (RuntimeError, WebSocketDisconnect):
            pass

    async def finalize_voice_call():
        """Persist, synthesize, deliver, and only then complete a voice call."""
        if finalization_lock.locked():
            try:
                await websocket.send_json({
                    "type": "finalization_in_progress",
                    "message": "आपकी call पूरी की जा रही है। कृपया थोड़ी देर प्रतीक्षा करें।",
                })
            except (RuntimeError, WebSocketDisconnect):
                pass
            return
        async with finalization_lock:
            finalization_started.set()
            current_seller = _resolve_seller_id(thread_id=session_id)
            playback_complete.clear()
            playback_failed.clear()
            await websocket.send_json({"type": "call_finalizing"})
            result = await asyncio.to_thread(
                finalize_call_session,
                seller_id=current_seller,
                session_id=session_id,
                channel="voice",
                defer_completion=True,
            )
            if not result.get("success") or result.get("status") != "finalizing":
                finalization_started.clear()
                await websocket.send_json({
                    "type": "error",
                    "code": result.get("error", "finalization_failed"),
                    "message": result.get("message", "Call पूरी नहीं हो सकी, लेकिन सहेजे गए रिकॉर्ड सुरक्षित हैं।"),
                })
                return

            final_reply = result.get("final_message")
            try:
                audio_bytes = await asyncio.to_thread(
                    voiceAssistant.generate_audio,
                    final_reply,
                    session_id,
                    client_id or session_id,
                )
            except Exception as err:
                fail_call_finalization(current_seller, session_id, f"TTS failed: {type(err).__name__}")
                finalization_started.clear()
                logger.exception("Final call TTS failed session_id=%s", session_id)
                await websocket.send_json({
                    "type": "error",
                    "code": "final_tts_failed",
                    "message": "बातचीत और summary सुरक्षित हैं, लेकिन closing audio तैयार नहीं हो सकी। आप call समाप्त करने की फिर कोशिश कर सकते हैं।",
                })
                return

            try:
                await websocket.send_json({"type": "assistant_reply", "text": final_reply})
                await websocket.send_bytes(audio_bytes)
                await websocket.send_json({"type": "assistant_end"})
                complete_wait = asyncio.create_task(playback_complete.wait())
                failed_wait = asyncio.create_task(playback_failed.wait())
                done, pending = await asyncio.wait(
                    {complete_wait, failed_wait},
                    timeout=90,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                if not done:
                    raise asyncio.TimeoutError("Browser playback acknowledgement timed out.")
                if playback_failed.is_set():
                    raise RuntimeError("Browser could not play the final audio.")
            except asyncio.TimeoutError:
                fail_call_finalization(current_seller, session_id, "Final playback acknowledgement timed out.")
                finalization_started.clear()
                logger.warning("Final playback acknowledgement timed out session_id=%s", session_id)
                try:
                    await websocket.send_json({
                        "type": "error",
                        "code": "final_playback_timeout",
                        "message": "Closing audio समय पर पूरी नहीं चली। आपके रिकॉर्ड सुरक्षित हैं। कृपया call समाप्त करने की फिर कोशिश करें।",
                    })
                except (RuntimeError, WebSocketDisconnect):
                    pass
                return
            except RuntimeError:
                fail_call_finalization(current_seller, session_id, "Final audio playback failed in browser.")
                finalization_started.clear()
                logger.warning("Final audio playback failed session_id=%s", session_id)
                try:
                    await websocket.send_json({
                        "type": "error",
                        "code": "final_playback_failed",
                        "message": "Closing audio नहीं चल सकी। आपके रिकॉर्ड सुरक्षित हैं। कृपया call समाप्त करने की फिर कोशिश करें।",
                    })
                except (RuntimeError, WebSocketDisconnect):
                    pass
                return
            except WebSocketDisconnect:
                fail_call_finalization(current_seller, session_id, "WebSocket disconnected before final playback acknowledgement.")
                logger.warning("WebSocket disconnected before final playback acknowledgement session_id=%s", session_id)
                return

            completed = await asyncio.to_thread(complete_call_finalization, current_seller, session_id)
            if not completed.get("success"):
                finalization_started.clear()
                await websocket.send_json({
                    "type": "error",
                    "code": completed.get("error", "finalization_verification_failed"),
                    "message": "Closing audio चल गई, लेकिन रिकॉर्ड सुरक्षित होने की पुष्टि नहीं हो सकी। Call को अभी पूरा नहीं माना गया है।",
                })
                return
            summary_data = completed.get("summary") or {}
            await websocket.send_json({
                "type": "call_ended",
                "status": "completed",
                "summary_id": summary_data.get("summary_id", ""),
                "message": "Call summary और बातचीत के रिकॉर्ड सुरक्षित दर्ज हो गए हैं।",
            })
            await websocket.close(code=1000, reason="Call completed")

    try:
        async with voiceAssistant.connect_stt(
            session_id,
            client_id or session_id,
        ) as sarvam_ws:
            stt_started = True
            # Tell the browser that speech recognition is actually available.
            # A connected microphone alone is not proof that STT works.
            await websocket.send_json({"type": "stt_ready"})

            async def process_assistant_turn(transcript: str, request_id: str | None):
                try:
                    reply = await asyncio.to_thread(
                        voiceAssistant.generate_response,
                        transcript,
                        session_id,
                        client_id or session_id,
                    )
                    if not has_nonempty_text(reply):
                        raise EmptyAssistantResponseError(
                            "The assistant returned no text."
                        )

                    active_seller = _resolve_seller_id(thread_id=session_id)
                    assistant_save = save_message(
                        seller_id=active_seller,
                        session_id=session_id,
                        speaker="assistant",
                        message_text=reply,
                        channel="voice",
                    )
                    if not assistant_save.get("saved") and not assistant_save.get("duplicate"):
                        raise IOError("Assistant voice response could not be persisted.")

                    log_text_boundary("LangGraph result -> Sarvam TTS", session_id, reply)
                    audio_bytes = await asyncio.to_thread(
                        voiceAssistant.generate_audio,
                        reply,
                        session_id,
                        client_id or session_id,
                    )
                    await websocket.send_json({
                        "type": "assistant_reply",
                        "text": reply,
                    })
                    log_text_boundary("Assistant text -> Browser WebSocket", session_id, reply)
                    log_audio_boundary(
                        "Sarvam TTS audio -> Browser WebSocket",
                        session_id,
                        len(audio_bytes),
                    )
                    turn_playback_ack.clear()
                    await websocket.send_bytes(audio_bytes)
                    try:
                        await asyncio.wait_for(turn_playback_ack.wait(), timeout=90)
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Assistant audio playback acknowledgement timed out session_id=%s",
                            session_id,
                        )

                except EmptyAssistantResponseError:
                    logger.warning(
                        "Empty assistant response; TTS skipped session_id=%s",
                        session_id,
                    )
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "code": "empty_assistant_response",
                            "recoverable": True,
                            "message": voiceAssistant.retry_prompt(session_id, transcript),
                        })
                    except (RuntimeError, WebSocketDisconnect):
                        pass
                except (WebSocketDisconnect, ConnectionClosed):
                    logger.info(
                        "Voice client disconnected during response session_id=%s",
                        session_id,
                    )
                except Exception as error:
                    logger.exception(
                        "Voice turn failed session_id=%s request_id=%s error_type=%s",
                        session_id,
                        request_id or "unavailable",
                        type(error).__name__,
                    )
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "code": "voice_turn_failed",
                            "recoverable": True,
                            "message": "माफ़ कीजिए, मैं अभी जवाब नहीं दे पा रही हूँ। कृपया फिर से बोलें।",
                        })
                    except (RuntimeError, WebSocketDisconnect):
                        pass
                finally:
                    assistant_busy.clear()
                    try:
                        await websocket.send_json({"type": "assistant_end"})
                    except (RuntimeError, WebSocketDisconnect):
                        pass

            async def send_audio():
                """Forward browser audio chunks to Sarvam."""

                while True:
                    try:
                        incoming = await asyncio.wait_for(
                            websocket.receive(),
                            timeout=1.0,
                        )
                    except asyncio.TimeoutError:
                        if (
                            not stt_closed.is_set()
                            and (assistant_busy.is_set() or finalization_started.is_set())
                        ):
                            if not await send_stt_audio(silence_frame):
                                continue
                        continue
                    if incoming.get("type") == "websocket.disconnect":
                        raise WebSocketDisconnect(incoming.get("code", 1000))
                    if incoming.get("text") is not None:
                        try:
                            control = json.loads(incoming["text"])
                        except (TypeError, json.JSONDecodeError):
                            continue
                        if control.get("type") == "playback_complete":
                            playback_complete.set()
                            turn_playback_ack.set()
                        elif control.get("type") == "playback_failed":
                            playback_failed.set()
                            turn_playback_ack.set()
                        elif control.get("type") in {
                            "turn_playback_complete",
                            "turn_playback_failed",
                        }:
                            turn_playback_ack.set()
                        elif control.get("type") in {"end_call", "retry_finalization"}:
                            if finalization_lock.locked():
                                await websocket.send_json({
                                    "type": "finalization_in_progress",
                                    "message": "आपकी call पूरी की जा रही है। कृपया थोड़ी देर प्रतीक्षा करें।",
                                })
                            else:
                                asyncio.create_task(finalize_voice_call())
                        continue
                    audio_chunk = incoming.get("bytes") or b""
                    if finalization_started.is_set():
                        # Ignore any in-flight microphone frames once finalization begins.
                        continue
                    if stt_closed.is_set():
                        continue
                    if assistant_busy.is_set():
                        # The UI pauses capture while the assistant responds.
                        # Drop any frames already in flight rather than
                        # queueing speech that cannot be answered yet.
                        continue
                    log_audio_boundary(
                        "Browser PCM -> FastAPI WebSocket -> Sarvam Realtime STT",
                        session_id,
                        len(audio_chunk),
                    )
                    if not audio_chunk:
                        logger.warning("Empty audio frame skipped session_id=%s", session_id)
                        continue

                    encoded_audio = base64.b64encode(
                        audio_chunk
                    ).decode("utf-8")

                    if not await send_stt_audio(encoded_audio):
                        return

            async def receive_transcript():
                """Receive transcripts and generate AI voice responses."""

                # Track partial transcripts so an empty final transcript can
                # tell attempted speech apart from VAD noise. ``nonlocal`` is
                # required because the handler owns this timestamp.
                nonlocal last_unkeyed_partial_at, fallback_unkeyed_final_pending

                while True:
                    message = await stt_event_queue.get()
                    if message is stt_stream_end:
                        break
                    if isinstance(message, BaseException):
                        raise message
                    request_id = extract_request_id(message)

                    if message.event == "transcript.partial":
                        raw_partial = getattr(message, "text", None)
                        log_text_boundary(
                            "Sarvam Realtime STT partial transcript",
                            session_id,
                            raw_partial,
                            request_id,
                            level=logging.DEBUG,
                        )
                        partial_text = clean_transcript(raw_partial)
                        if partial_text is None:
                            continue
                        utterance_idx = getattr(message, "utterance_idx", None)
                        if (
                            utterance_idx is not None
                            and utterance_idx in processed_utterances
                        ):
                            continue
                        if assistant_busy.is_set() or finalization_started.is_set():
                            logger.debug(
                                "Partial transcript ignored while response/finalization is active session_id=%s",
                                session_id,
                            )
                            continue
                        fallback_unkeyed_final_pending = False

                        now = time.monotonic()
                        request_id = request_id or None
                        if utterance_idx is not None:
                            if pending_partial["utterance_idx"] != utterance_idx:
                                pending_partial.update({
                                    "utterance_idx": utterance_idx,
                                    "request_id": request_id,
                                    "text": partial_text,
                                    "changed_at": now,
                                    "started_at": now,
                                    "speech_ended_at": 0.0,
                                })
                            elif (
                                partial_text != pending_partial["text"]
                                or pending_partial["speech_ended_at"]
                            ):
                                pending_partial["text"] = partial_text
                                pending_partial["changed_at"] = now
                                pending_partial["speech_ended_at"] = 0.0
                                pending_partial["request_id"] = (
                                    request_id or pending_partial["request_id"]
                                )
                        elif (
                            pending_partial["utterance_idx"] is not None
                            or pending_partial["speech_ended_at"]
                        ):
                            pending_partial.update({
                                "utterance_idx": None,
                                "request_id": request_id,
                                "text": partial_text,
                                "changed_at": now,
                                "started_at": now,
                                "speech_ended_at": 0.0,
                            })
                        else:
                            if not pending_partial["text"]:
                                pending_partial["started_at"] = now
                            if (
                                partial_text != pending_partial["text"]
                                or pending_partial["speech_ended_at"]
                            ):
                                pending_partial["text"] = partial_text
                                pending_partial["changed_at"] = now
                                pending_partial["speech_ended_at"] = 0.0
                            pending_partial["request_id"] = (
                                request_id or pending_partial["request_id"]
                            )

                        if request_id:
                            partial_request_ids.add(request_id)
                            if len(partial_request_ids) > 256:
                                partial_request_ids.pop()
                        else:
                            last_unkeyed_partial_at = time.monotonic()
                        await websocket.send_json({
                            "type": "partial_transcript",
                            "text": partial_text,
                            "request_id": request_id,
                        })

                    elif message.event == "transcript.final":
                        utterance_idx = getattr(message, "utterance_idx", None)
                        pending_matches = (
                            pending_partial["utterance_idx"] == utterance_idx
                            if utterance_idx is not None
                            else bool(
                                request_id
                                and request_id == pending_partial["request_id"]
                            )
                            or (
                                pending_partial["utterance_idx"] is None
                                and not request_id
                            )
                        )
                        stable_partial = pending_partial["text"] if pending_matches else ""
                        if utterance_idx is not None:
                            if utterance_idx in processed_utterances:
                                logger.info(
                                    "Duplicate final transcript ignored session_id=%s utterance_idx=%s",
                                    session_id,
                                    utterance_idx,
                                )
                                continue
                            processed_utterances.add(utterance_idx)
                            if len(processed_utterances) > 256:
                                processed_utterances.pop()
                        raw_transcript = getattr(message, "text", None)
                        log_text_boundary(
                            "Sarvam Realtime STT final transcript",
                            session_id,
                            raw_transcript,
                            request_id,
                        )
                        transcript = clean_transcript(raw_transcript)

                        used_partial_fallback = transcript is None and bool(stable_partial)
                        if used_partial_fallback:
                            logger.warning(
                                "Empty final transcript; using last stable partial session_id=%s utterance_idx=%s",
                                session_id,
                                utterance_idx if utterance_idx is not None else "unavailable",
                            )
                            transcript = stable_partial

                        if transcript is None:
                            # A final transcript with no usable text is only a
                            # real problem when the seller was actually
                            # speaking (partial transcripts were seen). VAD
                            # endpointing on room noise should not surface an
                            # error to the seller. Correlate by request ID when
                            # available so an earlier utterance cannot trigger
                            # a stale retry hint for a later noise frame.
                            if request_id:
                                speech_attempted = request_id in partial_request_ids
                                partial_request_ids.discard(request_id)
                            else:
                                speech_attempted = (
                                    time.monotonic() - last_unkeyed_partial_at < 15.0
                                )
                                last_unkeyed_partial_at = 0.0
                            if speech_attempted:
                                logger.info(
                                    "Speech detected but transcript was empty session_id=%s request_id=%s",
                                    session_id,
                                    request_id or "unavailable",
                                )
                                await websocket.send_json({
                                    "type": "error",
                                    "code": "empty_transcript",
                                    "recoverable": True,
                                    "message": voiceAssistant.retry_prompt(session_id),
                                })
                            else:
                                logger.info(
                                    "Empty STT transcript without speech ignored session_id=%s request_id=%s",
                                    session_id,
                                    request_id or "unavailable",
                                )
                            continue

                        synthetic_fallback = bool(
                            getattr(message, "synthetic_fallback", False)
                        )
                        if not synthetic_fallback:
                            now = time.monotonic()
                            for fallback_id, expiry in tuple(fallback_request_ids.items()):
                                if expiry <= now:
                                    fallback_request_ids.pop(fallback_id, None)
                            for fallback_idx, expiry in tuple(fallback_utterance_ids.items()):
                                if expiry <= now:
                                    fallback_utterance_ids.pop(fallback_idx, None)
                            correlated_fallback = (
                                bool(request_id and request_id in fallback_request_ids)
                                or (
                                    utterance_idx is not None
                                    and utterance_idx in fallback_utterance_ids
                                )
                            )
                            if correlated_fallback:
                                logger.info(
                                    "Late transcript correlated with finalized partial ignored session_id=%s request_id=%s utterance_idx=%s",
                                    session_id,
                                    request_id or "unavailable",
                                    utterance_idx if utterance_idx is not None else "unavailable",
                                )
                                continue
                            if (
                                request_id is None
                                and utterance_idx is None
                                and fallback_unkeyed_final_pending
                            ):
                                fallback_unkeyed_final_pending = False
                                logger.info(
                                    "Uncorrelated late final after partial fallback ignored session_id=%s",
                                    session_id,
                                )
                                continue
                            fallback_expiry = fallback_transcripts.get(transcript, 0.0)
                            if fallback_expiry > time.monotonic():
                                logger.info(
                                    "Late transcript matching a finalized partial ignored session_id=%s request_id=%s",
                                    session_id,
                                    request_id or "unavailable",
                                )
                                continue
                            fallback_transcripts.pop(transcript, None)

                        if request_id and request_id in processed_request_ids:
                            logger.info(
                                "Duplicate STT transcript skipped session_id=%s request_id=%s",
                                session_id,
                                request_id,
                            )
                            continue
                        if request_id:
                            partial_request_ids.discard(request_id)
                        else:
                            last_unkeyed_partial_at = 0.0
                        if request_id:
                            processed_request_ids.add(request_id)
                            if len(processed_request_ids) > 256:
                                processed_request_ids.pop()
                        if (
                            (synthetic_fallback or used_partial_fallback)
                        ):
                            now = time.monotonic()
                            expiry = now + 30.0
                            if request_id:
                                fallback_request_ids[request_id] = expiry
                            if utterance_idx is not None:
                                fallback_utterance_ids[utterance_idx] = expiry
                            if request_id is None and utterance_idx is None:
                                fallback_unkeyed_final_pending = True
                                fallback_transcripts[transcript] = expiry
                            for fallback_text, expiry in tuple(fallback_transcripts.items()):
                                if expiry <= now:
                                    fallback_transcripts.pop(fallback_text, None)

                        if pending_matches:
                            pending_partial.update({
                                "utterance_idx": None,
                                "request_id": None,
                                "text": "",
                                "changed_at": 0.0,
                                "started_at": 0.0,
                                "speech_ended_at": 0.0,
                            })

                        if not is_session_active(session_id):
                            logger.info("Session %s is already finalizing/completed. Ignoring new transcript.", session_id)
                            continue

                        if assistant_busy.is_set():
                            logger.info(
                                "STT transcript ignored while response is active session_id=%s",
                                session_id,
                            )
                            continue

                        log_text_boundary(
                            "Validated transcript -> LangGraph",
                            session_id,
                            transcript,
                            request_id,
                        )

                        # Persist original seller voice transcript
                        current_seller = _resolve_seller_id(thread_id=session_id)
                        seller_save = save_message(
                            seller_id=current_seller,
                            session_id=session_id,
                            speaker="seller",
                            message_text=transcript,
                            channel="voice",
                        )
                        if not seller_save.get("saved") and not seller_save.get("duplicate"):
                            await websocket.send_json({
                                "type": "error",
                                "code": "transcript_storage_failed",
                                "message": "आपकी बात समझ आई, लेकिन दर्ज नहीं हो सकी। कृपया call समाप्त करने की फिर कोशिश करें।",
                            })
                            continue

                        # Check for explicit call termination intent.
                        if is_call_termination_intent(transcript):
                            logger.info("Call termination intent detected for session %s", session_id)
                            await websocket.send_json({
                                "type": "assistant_start",
                                "transcript": transcript,
                                "request_id": request_id,
                            })
                            history = get_conversation_history(session_id, current_seller)
                            if has_unanswered_assistant_question(history):
                                language = "hindi"
                                offer = build_pending_question_offer(language)
                                saved_offer = save_message(
                                    seller_id=current_seller,
                                    session_id=session_id,
                                    speaker="assistant",
                                    message_text=offer,
                                    channel="voice",
                                    language=language,
                                )
                                if saved_offer.get("saved") or saved_offer.get("duplicate"):
                                    try:
                                        offer_audio = await asyncio.to_thread(
                                            voiceAssistant.generate_audio,
                                            offer,
                                            session_id,
                                            client_id or session_id,
                                        )
                                        await websocket.send_json({"type": "assistant_reply", "text": offer})
                                        await websocket.send_bytes(offer_audio)
                                    except Exception as error:
                                        await websocket.send_json({
                                            "type": "error",
                                            "code": "pending_question_audio_failed",
                                            "message": "मैं follow-up सवाल नहीं चला पाई। कृपया फिर कोशिश करें या End call दबाएँ।",
                                        })
                                    finally:
                                        await websocket.send_json({"type": "assistant_end"})
                                    continue
                                await websocket.send_json({
                                    "type": "error",
                                    "code": "transcript_storage_failed",
                                    "message": "मैं follow-up सवाल दर्ज नहीं कर पाई, इसलिए call जारी है। कृपया फिर कोशिश करें।",
                                })
                                await websocket.send_json({"type": "assistant_end"})
                                continue
                            await finalize_voice_call()
                            return

                        assistant_busy.set()
                        await websocket.send_json({
                            "type": "assistant_start",
                            "transcript": transcript,
                            "request_id": request_id,
                        })

                        turn_task = asyncio.create_task(
                            process_assistant_turn(transcript, request_id)
                        )
                        turn_tasks.add(turn_task)
                        turn_task.add_done_callback(turn_tasks.discard)
                        continue

                    elif message.event in {
                        "session.begin",
                        "vad.speech_start",
                        "vad.speech_end",
                        "session.end",
                    }:
                        if message.event == "vad.speech_end" and pending_partial["text"]:
                            utterance_idx = getattr(message, "utterance_idx", None)
                            request_matches = (
                                not request_id
                                or not pending_partial["request_id"]
                                or request_id == pending_partial["request_id"]
                            )
                            if (
                                request_matches
                                and (
                                    utterance_idx is None
                                    or utterance_idx == pending_partial["utterance_idx"]
                                )
                            ):
                                speech_ended_at = time.monotonic()
                                pending_partial["speech_ended_at"] = speech_ended_at
                                pending_partial["changed_at"] = max(
                                    pending_partial["changed_at"],
                                    speech_ended_at,
                                )
                        logger.info(
                            "Sarvam STT event session_id=%s event=%s utterance_idx=%s",
                            session_id,
                            message.event,
                            getattr(message, "utterance_idx", "unavailable"),
                        )

                    elif message.event == "error":
                        error_code = str(getattr(message, "code", "") or "")
                        error_detail = str(
                            getattr(message, "message", None)
                            or getattr(message, "reason", None)
                            or ""
                        )
                        is_fatal = bool(getattr(message, "is_fatal", False))
                        logger.error(
                            "Sarvam Realtime STT error session_id=%s request_id=%s code=%s fatal=%s",
                            session_id,
                            request_id or "unavailable",
                            error_code or "unknown",
                            is_fatal,
                        )

                        failure_text = f"{error_code} {error_detail}".lower()
                        fatal_or_billing = is_fatal or any(
                            marker in failure_text
                            for marker in _STT_QUOTA_MARKERS + _STT_AUTH_MARKERS
                        )

                        if fatal_or_billing:
                            stt_failure["code"] = error_code
                            stt_failure["detail"] = error_detail
                            stt_closed.set()
                            return

                if not finalization_started.is_set():
                    stt_closed.set()

            async def pump_stt_events():
                """Decouple SDK events from the turn-completion watchdog."""
                try:
                    async for event in sarvam_ws:
                        await stt_event_queue.put(event)
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    await stt_event_queue.put(error)
                finally:
                    await stt_event_queue.put(stt_stream_end)

            async def finalize_stale_partial():
                """Complete a turn when Sarvam sends partials but no final.

                This is a bounded recovery path for VAD that stays active on
                room noise (or a final transcript that never arrives). It only
                runs after the partial text has been stable for the grace
                period, so live speech is not cut off prematurely.
                """
                while not stt_closed.is_set():
                    await asyncio.sleep(VOICE_FINAL_WATCH_INTERVAL_SECONDS)
                    if (
                        stt_closed.is_set()
                        or finalization_started.is_set()
                        or assistant_busy.is_set()
                    ):
                        continue

                    text = pending_partial["text"]
                    if (
                        not text
                        or (
                            pending_partial["utterance_idx"] is not None
                            and pending_partial["utterance_idx"] in processed_utterances
                        )
                    ):
                        continue

                    now = time.monotonic()
                    stable_for = now - pending_partial["changed_at"]
                    utterance_age = now - pending_partial["started_at"]
                    if (
                        stable_for < VOICE_PARTIAL_FINAL_GRACE_SECONDS
                        or (
                            not pending_partial["speech_ended_at"]
                            and utterance_age < VOICE_PARTIAL_MAX_UTTERANCE_SECONDS
                        )
                    ):
                        continue

                    pending_partial["text"] = ""
                    pending_partial["changed_at"] = now
                    utterance_idx = pending_partial["utterance_idx"]
                    logger.warning(
                        "No transcript.final after stable partial; finalizing last partial session_id=%s utterance_idx=%s text_length=%s",
                        session_id,
                        utterance_idx,
                        len(text),
                    )
                    await stt_event_queue.put(
                        SimpleNamespace(
                            event="transcript.final",
                            text=text,
                            utterance_idx=utterance_idx,
                            request_id=pending_partial["request_id"],
                            synthetic_fallback=True,
                        )
                    )

            sender = asyncio.create_task(send_audio())
            receiver = asyncio.create_task(receive_transcript())
            stt_pump = asyncio.create_task(pump_stt_events())
            stale_final_watch = asyncio.create_task(finalize_stale_partial())

            try:
                done, _ = await wait_for_voice_task_completion(
                    {sender, receiver},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if receiver in done:
                    receiver_error = receiver.exception()
                    if isinstance(receiver_error, ConnectionClosed):
                        stt_closed.set()
                if stt_closed.is_set():
                    if finalization_started.is_set():
                        await sender
                    else:
                        for turn_task in tuple(turn_tasks):
                            turn_task.cancel()
                        await asyncio.gather(*turn_tasks, return_exceptions=True)
                        await send_recoverable_stt_error()
                else:
                    for task in done:
                        task.result()

            finally:
                # Teardown must finish even when the ASGI server (or Starlette's
                # TestClient) is cancelling this endpoint. AnyIO re-delivers
                # cancellation on every event-loop iteration, which would abort
                # the awaits below and leave the STT sender/receiver tasks
                # un-awaited. Shield the teardown, then let cancellation resume.
                with anyio.CancelScope(shield=True):
                    sender.cancel()
                    receiver.cancel()
                    stt_pump.cancel()
                    stale_final_watch.cancel()
                    for turn_task in tuple(turn_tasks):
                        turn_task.cancel()

                    await asyncio.gather(
                        sender,
                        receiver,
                        stt_pump,
                        stale_final_watch,
                        *turn_tasks,
                        return_exceptions=True
                    )

                    if not stt_closed.is_set():
                        try:
                            await sarvam_ws.send_realtime_end(RealtimeEnd())
                        except ConnectionClosed:
                            logger.debug(
                                "Sarvam STT already closed at session cleanup session_id=%s",
                                session_id,
                            )

    except WebSocketDisconnect:
        logger.info("Voice WebSocket session disconnected session_id=%s", session_id)

    except Exception as error:
        # Log only the exception type: SDK errors can echo request metadata.
        logger.error(
            "Voice WebSocket failed session_id=%s error_type=%s",
            session_id,
            type(error).__name__,
        )
        if not stt_started:
            failed_key = get_client_sarvam_api_key(client_id or session_id)
            fallback_key = (
                advance_client_sarvam_api_key(client_id or session_id, failed_key)
                if failed_key and is_sarvam_credential_error(error)
                else None
            )
            code, message = _stt_failure_payload(
                "",
                str(error),
                client_id or session_id,
            )
            try:
                await websocket.send_json({
                    "type": "error",
                    "code": code,
                    "recoverable": True,
                    "message": (
                        message + " दूसरी configured API key इस्तेमाल करने के लिए voice फिर शुरू करें।"
                        if fallback_key
                        else message
                    ),
                })
                await websocket.close(code=1012, reason="Speech recognition unavailable")
            except (RuntimeError, WebSocketDisconnect):
                pass
        elif not finalization_started.is_set():
            # Never leave the browser stuck in Listening if the receiver or a
            # turn handler fails unexpectedly after STT started.
            try:
                await websocket.send_json({
                    "type": "error",
                    "code": "voice_pipeline_failed",
                    "recoverable": True,
                    "message": (
                        "I couldn't complete the voice response. Please try "
                        "speaking again."
                    ),
                })
                await websocket.close(code=1011, reason="Voice pipeline failed")
            except (RuntimeError, WebSocketDisconnect):
                pass
    finally:
        # A dropped transport is not explicit seller consent to complete a call.
        logger.info("Voice WebSocket cleanup finished session_id=%s", session_id)
