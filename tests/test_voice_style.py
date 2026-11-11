import unittest
from unittest.mock import patch

from seller_dashboard.assistant_style import FEMININE_VOICE_PROMPT
from seller_dashboard.bot import SYSTEM_PROMPT, SarvamLLMUnavailable, language_policy
from seller_dashboard.voice import VoiceAssistant


MASCULINE_FIRST_PERSON = (
    "kar raha hoon",
    "raha hoon",
    "sakta",
    "karunga",
    "samajh gaya",
    "रहा हूँ",
    "सकता",
    "करूंगा",
    "समझा",
)


class FeminineVoiceTests(unittest.TestCase):
    def _fallback(self, transcript):
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        with patch(
            "seller_dashboard.voice.graph.invoke",
            side_effect=SarvamLLMUnavailable("unavailable"),
        ):
            return assistant.generate_response(transcript, "style-test")

    def test_system_prompt_requires_feminine_hindi_grammar(self):
        self.assertNotIn(FEMININE_VOICE_PROMPT, SYSTEM_PROMPT)
        self.assertIn(FEMININE_VOICE_PROMPT, language_policy(voice_mode=True))
        for form in ("मैं समझ सकती हूँ", "मैं जाँच कर रही हूँ"):
            self.assertIn(form, FEMININE_VOICE_PROMPT)
        self.assertIn("Never use masculine", FEMININE_VOICE_PROMPT)

    def test_hindi_fallback_is_feminine(self):
        fallback = self._fallback("मेरी बिक्री कम हो रही है।")
        self.assertIn("पा रही हूँ", fallback)
        for masculine in MASCULINE_FIRST_PERSON:
            self.assertNotIn(masculine, fallback)

    def test_hinglish_input_gets_hindi_fallback(self):
        fallback = self._fallback("Mera ASP gir raha hai, main kya karun?")
        self.assertIn("पा रही हूँ", fallback)
        for masculine in MASCULINE_FIRST_PERSON:
            self.assertNotIn(masculine, fallback)

    def test_english_input_gets_hindi_fallback(self):
        fallback = self._fallback("My sales are falling, what should I do?")
        self.assertIn("माफ़ कीजिए", fallback)
        self.assertIn("पा रही हूँ", fallback)

    def test_all_retry_prompts_are_hindi_and_feminine(self):
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        responses = [
            assistant.retry_prompt("style-test", "मेरी बिक्री कम हो रही है।"),
            assistant.retry_prompt("style-test", "Mera ASP gir raha hai"),
            assistant.retry_prompt("style-test", "Please repeat that"),
        ]
        for response in responses:
            self.assertIn("पाई", response)
        for masculine in MASCULINE_FIRST_PERSON:
            for response in responses:
                self.assertNotIn(masculine, response)


if __name__ == "__main__":
    unittest.main()
