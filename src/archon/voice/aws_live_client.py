"""
AWS Live Client - Gemini-compatible interface for AWS voice services.
Uses Amazon Transcribe for STT, Bedrock for Brain, and Polly for TTS.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, List, Dict

from archon.voice.voice_engine import AmazonVoiceEngine
from archon.voice.gemini_live_client import ResponsePart
from archon.manager.orchestrator import ManagerOrchestrator
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class AWSLiveSession:
    """
    Simulates a Gemini Live session using decoupled AWS services.
    """

    def __init__(
        self,
        engine: AmazonVoiceEngine,
        orchestrator: ManagerOrchestrator,
        language_code: str = "en-US",
    ):
        self.engine = engine
        self.orchestrator = orchestrator
        self.language_code = language_code
        self._interrupted = asyncio.Event()
        self._input_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._output_queue: asyncio.Queue[ResponsePart] = asyncio.Queue()
        self._running = True

    async def send_audio(self, pcm_bytes: bytes) -> None:
        """Queue mic audio for transcription."""
        if self._interrupted.is_set():
            return
        await self._input_queue.put(pcm_bytes)

    async def end_turn(self) -> None:
        """Signal end of turn to trigger processing."""
        # For AWS, we might just wait for Transcribe to yield a final result
        pass

    def interrupt(self) -> None:
        self._interrupted.set()
        # Clear queues if needed

    def clear_interrupt(self) -> None:
        self._interrupted.clear()

    async def _audio_generator(self) -> AsyncIterator[bytes]:
        while self._running:
            chunk = await self._input_queue.get()
            if chunk is None:
                break
            yield chunk

    async def _run_pipeline(self):
        """
        Background task:
        Transcribe -> Text -> Bedrock -> Text -> Translate -> Polly -> Output Queue
        """
        async for transcript in self.engine.transcribe_stream(
            self._audio_generator(), self.language_code
        ):
            if not self._running:
                break

            logger.info(f"STT ({self.language_code}): {transcript}")
            yield ResponsePart(text=f"Transcript: {transcript}")

            # Regional Pipeline: Translate Input (e.g. Hindi -> English)
            source_lang = self.language_code.split("-")[0]
            english_input = transcript
            if source_lang != "en":
                english_input = await self.engine.translate_text(
                    transcript, target_lang="en", source_lang=source_lang
                )
                logger.info(f"Translate (Input): {english_input}")

            # Process with Bedrock via Orchestrator (Orchestrator handles English)
            response = await self.orchestrator.process_conversational_input(english_input, [])
            text_response = response.get("message", "I didn't quite catch that.")
            action = response.get("action")
            spec = response.get("spec")
            if action == "execute_task" and spec:

                async def _bg_run():
                    try:
                        async for _ in self.orchestrator.execute_plan(spec):
                            pass
                    except Exception as e:
                        logger.error(f"Execution failed in voice mode: {e}")

                asyncio.create_task(_bg_run())

            # Translate Output (English -> Regional)
            target_lang = source_lang
            if target_lang != "en":
                text_response = await self.engine.translate_text(text_response, target_lang)

            yield ResponsePart(text=text_response)

            # Synthesize with Polly
            voice_config = self.engine.get_regional_voice(target_lang)
            audio_response = await self.engine.synthesize(
                text_response, voice_id=voice_config["voice"], language_code=voice_config["code"]
            )

            if audio_response:
                # Break audio into chunks for the visualizer/player
                chunk_size = 3200  # 100ms at 16kHz
                for i in range(0, len(audio_response), chunk_size):
                    await self._output_queue.put(
                        ResponsePart(audio=audio_response[i : i + chunk_size])
                    )

            await self._output_queue.put(ResponsePart(is_final=True))

    async def receive(self) -> AsyncIterator[ResponsePart]:
        """Yield response parts from the output queue."""
        # In this simplistic version, we'll start the pipeline and yield from queue
        pipeline_task = asyncio.create_task(self._process_stream())
        try:
            while self._running:
                part = await self._output_queue.get()
                yield part
                if part.is_final:
                    # Don't break here, stay in the session
                    pass
        finally:
            pipeline_task.cancel()

    async def _process_stream(self):
        """Forward pipeline results to output queue."""
        async for part in self._run_pipeline():
            await self._output_queue.put(part)


class AWSLiveClient:
    """
    AWS-based alternative to GenaiLiveClient.
    """

    def __init__(self, orchestrator: ManagerOrchestrator, language_code: str = "hi-IN"):
        self.engine = AmazonVoiceEngine()
        self.orchestrator = orchestrator
        self.language_code = language_code

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AWSLiveSession]:
        session = AWSLiveSession(self.engine, self.orchestrator, self.language_code)
        try:
            yield session
        finally:
            session._running = False
