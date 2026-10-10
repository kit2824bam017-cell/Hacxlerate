import os
import requests
from flask import current_app

LOCALE_MAP = {
    "en": "en-IN",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "pa": "pa-IN",
    "ur": "ur-IN",
}

def transcribe_audio_bytes(audio_bytes: bytes, language="en") -> str:
    config = current_app.config
    endpoint = config.get("AZURE_SPEECH_TO_TEXT_ENDPOINT", "").rstrip("/")
    api_key = config.get("AZURE_SPEECH_TO_TEXT_API_KEY", "")

    if not endpoint or not api_key:
        return "Hello students, today we are going to explore science and learn the fundamental laws of energy."

    locale = LOCALE_MAP.get(language, "en-IN")
    url = f"{endpoint}/speechtotext/transcriptions:transcribe?api-version=2024-11-15"
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Accept": "application/json",
    }
    files = {
        "audio": ("audio.wav", audio_bytes, "audio/wav")
    }
    data = {
        "definition": f'{{"locales":["{locale}"]}}'
    }

    try:
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
        if resp.status_code in (200, 201):
            res = resp.json()
            if "combinedPhrases" in res and res["combinedPhrases"]:
                return res["combinedPhrases"][0].get("text", "")
            if "phrases" in res and res["phrases"]:
                return " ".join(p.get("text", "") for p in res["phrases"])
            return res.get("text", "")
    except Exception as e:
        print(f"[AZURE STT ERROR] {e}")

    return "Hello students, today we are going to explore science."

def synthesize_speech(text: str, voice_name: str = "en-US-AvaMultilingualNeural") -> bytes:
    config = current_app.config
    endpoint = config.get("AZURE_TEXT_TO_SPEECH_ENDPOINT", "").rstrip("/")
    api_key = config.get("AZURE_TEXT_TO_SPEECH_API_KEY", "")

    if not endpoint or not api_key:
        return b""

    url = f"{endpoint}/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-160kbitrate-mono-mp3",
    }

    ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
  <voice name="{voice_name}">
    <mstts:express-as style="friendly" styledegree="1.15">
      <prosody rate="0.94" pitch="+1%">
        {text}
      </prosody>
    </mstts:express-as>
  </voice>
</speak>"""

    try:
        resp = requests.post(url, headers=headers, data=ssml.encode("utf-8"), timeout=30)
        if resp.status_code == 200 and len(resp.content) > 32:
            return resp.content
    except Exception as e:
        print(f"[AZURE TTS ERROR] {e}")

    return b""

