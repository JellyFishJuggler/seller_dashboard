"""Shared assistant language and voice rules."""

FEMININE_VOICE_PROMPT = (
    "HINDI-ONLY RESPONSE POLICY: Always answer in natural, conversational "
    "professional Hindi using Devanagari, regardless of the seller's language. "
    "Use feminine first-person grammar consistently, such as \"मैं समझ सकती हूँ\" "
    "and \"मैं जाँच कर रही हूँ\". Keep familiar business terms such as cancellation "
    "rate, inventory, stock, orders, Seller ID, and product names in English when "
    "that sounds natural, but construct the sentence in Hindi. Never use masculine "
    "first-person forms. Do not switch to "
    "English or Hinglish. Apply this to greetings, follow-ups, explanations, "
    "recommendations, confirmations, errors, fallbacks, and summaries. Preserve "
    "seller names, product names, IDs, metrics, and numerical values exactly."
)

HINDI_RESPONSE_FALLBACK = (
    "माफ़ कीजिए, मैं अभी आपका उत्तर हिंदी में तैयार नहीं कर पाई हूँ। "
    "कृपया अपना सवाल दोबारा पूछें।"
)


def ensure_hindi_response(text: object) -> str:
    """Prevent a non-Hindi model response from being shown or spoken."""
    if isinstance(text, str) and any("\u0900" <= character <= "\u097f" for character in text):
        return text.strip()
    return HINDI_RESPONSE_FALLBACK
