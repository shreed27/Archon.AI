"""
Amazon Voice Engine - AI for Bharat Capabilities.
Integrates Amazon Transcribe (STT), Amazon Polly (TTS), and Amazon Translate.
"""

import asyncio
import os
import boto3
from typing import Optional, AsyncIterator, List, Dict
from archon.utils.logger import get_logger

try:
    from amazon_transcribe.client import TranscribeStreamingClient
    from amazon_transcribe.handlers import TranscriptResultStreamHandler
    from amazon_transcribe.model import TranscriptEvent

    TRANSCRIBE_AVAILABLE = True
except ImportError:
    TRANSCRIBE_AVAILABLE = False

logger = get_logger(__name__)


class AmazonVoiceEngine:
    """
    Orchestrates AWS-based voice services for regional language support.
    """

    def __init__(
        self,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")

        session_kwargs = {"region_name": self.region_name}
        if aws_access_key_id:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.polly = boto3.client("polly", **session_kwargs)
        self.translate = boto3.client("translate", **session_kwargs)

        if TRANSCRIBE_AVAILABLE:
            self.transcribe_client = TranscribeStreamingClient(region=self.region_name)
        else:
            self.transcribe_client = None
            logger.warning("amazon-transcribe not installed. STT disabled.")

    async def transcribe_stream(
        self, audio_generator: AsyncIterator[bytes], language_code: str = "en-US"
    ) -> AsyncIterator[str]:
        """
        Stream audio to Amazon Transcribe and yield transcriptions.

        Args:
            audio_generator: Async iterator yielding PCM chunks (16kHz, mono, int16)
            language_code: Language code (e.g., 'hi-IN' for Hindi)
        """
        if not self.transcribe_client:
            logger.error("Transcribe client not available")
            return

        stream = await self.transcribe_client.start_stream_transcription(
            language_code=language_code,
            media_sample_rate_hz=16000,
            media_encoding="pcm",
        )

        async def write_chunks():
            async for chunk in audio_generator:
                await stream.input_stream.send_audio_event(audio_chunk=chunk)
            await stream.input_stream.end_stream()

        asyncio.create_task(write_chunks())

        async for event in stream.output_stream:
            if isinstance(event, TranscriptEvent):
                results = event.transcript.results
                for result in results:
                    if not result.is_partial:
                        for alt in result.alternatives:
                            yield alt.transcript

    async def synthesize(
        self, text: str, voice_id: str = "Aditi", language_code: str = "hi-IN"
    ) -> bytes:
        """
        Synthesize text to speech using Amazon Polly.

        Args:
            text: Text to synthesize
            voice_id: Polly Voice ID (e.g., 'Aditi' for Hindi, 'Kajal' for Hindi)
            language_code: Language code

        Returns:
            Raw PCM audio bytes (16kHz, mono, int16)
        """
        try:
            # Note: boto3 is synchronous, wrapping in executor if needed
            response = self.polly.synthesize_speech(
                Text=text,
                OutputFormat="pcm",
                VoiceId=voice_id,
                LanguageCode=language_code,
                SampleRate="16000",
            )

            if "AudioStream" in response:
                return response["AudioStream"].read()
            return b""
        except Exception as e:
            logger.error(f"Polly synthesis failed: {e}")
            return b""

    async def translate_text(
        self, text: str, target_lang: str = "hi", source_lang: str = "en"
    ) -> str:
        """Translate text using Amazon Translate."""
        try:
            response = self.translate.translate_text(
                Text=text, SourceLanguageCode=source_lang, TargetLanguageCode=target_lang
            )
            return response.get("TranslatedText", text)
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text

    def get_regional_voice(self, language: str) -> Dict[str, str]:
        """Get best Polly voice/language code for a region."""
        mapping = {
            "hindi": {"voice": "Aditi", "code": "hi-IN", "lang": "hi"},
            "marathi": {
                "voice": "Aditi",
                "code": "hi-IN",
                "lang": "mr",
            },  # Polly uses Aditi for multiple Indian langs sometimes or has specific ones
            "tamil": {"voice": "initial", "code": "ta-IN", "lang": "ta"},
            "telugu": {"voice": "initial", "code": "te-IN", "lang": "te"},
            # Add more as needed
        }
        return mapping.get(language.lower(), mapping["hindi"])
