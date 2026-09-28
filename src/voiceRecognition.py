import io
import speech_recognition as sr
from faster_whisper import WhisperModel

class VoiceProcessor:
    def __init__(self, model_size="turbo"):
        print("Caricamento del modello AI vocale...")
        # Usa "base" (75 MB) in int8: per 6 comandi direzionali ha la stessa precisione di "small" ma è 3x più veloce
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.recognizer = sr.Recognizer()
        
        # Taglia l'attesa post-parlato da 0.8s a 0.4s
        self.recognizer.pause_threshold = 0.4
        self.recognizer.non_speaking_duration = 0.3
        self.recognizer.dynamic_energy_threshold = False # Evita che la soglia si abbassi troppo col fruscio

        # Calibra il microfono UNA SOLA VOLTA all'avvio
        with sr.Microphone() as source:
            print("Calibrazione rumore di fondo (1s)...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def listen_and_transcribe(self):
        with sr.Microphone() as source:
            print("In ascolto! Parla entro 3 secondi...")
            # phrase_time_limit=3 impedisce al microfono di restare aperto per più di 3 secondi
            audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=3)

        # Passa l'audio direttamente in RAM (BytesIO) senza scrivere/cancellare "temp_cmd.wav" su disco!
        wav_stream = io.BytesIO(audio.get_wav_data(convert_rate=16000))

        segments, _ = self.model.transcribe(
            wav_stream,
            language="it",
            beam_size=1,                # Decodifica greedy: istantanea su M1
            vad_filter=True,            # Scarta i silenzi residui tramite Silero VAD
            condition_on_previous_text=False
        )
        return " ".join([s.text for s in segments]).strip()