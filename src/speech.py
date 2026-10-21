import io
import wave
import threading

import pyaudio
import speech_recognition as sr


class SpeechError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class Recorder:
    RATE = 16000
    CHANNELS = 1
    CHUNK = 1024
    FORMAT = pyaudio.paInt16

    def __init__(self, language: str = "ru-RU"):
        self.language = language
        self._pa = None
        self._stream = None
        self._frames = []
        self._thread = None
        self._stop_flag = False
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self):
        if self._recording:
            return
        self._pa = pyaudio.PyAudio()
        try:
            self._stream = self._pa.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )
        except Exception as e:
            self._cleanup()
            raise SpeechError(f"Микрофон недоступен: {e}")

        self._frames = []
        self._stop_flag = False
        self._recording = True

        def loop():
            while not self._stop_flag:
                try:
                    data = self._stream.read(self.CHUNK, exception_on_overflow=False)
                    self._frames.append(data)
                except Exception:
                    break

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self) -> str:
        if not self._recording:
            raise SpeechError("Запись не идёт")
        self._stop_flag = True
        if self._thread:
            self._thread.join(timeout=2)
        self._recording = False

        frames = self._frames
        self._cleanup()

        if not frames:
            raise SpeechError("Ничего не записалось")

        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self._pa_width())
            wf.setframerate(self.RATE)
            wf.writeframes(b"".join(frames))
        wav_io.seek(0)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            audio = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            raise SpeechError("Не удалось распознать речь")
        except sr.RequestError as e:
            raise SpeechError(f"Сервис распознавания недоступен: {e}")

        return text.strip()

    @staticmethod
    def _pa_width() -> int:
        return 2  # paInt16

    def _cleanup(self):
        try:
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
        except Exception:
            pass
        self._stream = None
        try:
            if self._pa is not None:
                self._pa.terminate()
        except Exception:
            pass
        self._pa = None
