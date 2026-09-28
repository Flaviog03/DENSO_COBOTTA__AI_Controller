from voiceRecognition import VoiceProcessor

orecchio = VoiceProcessor()
comando = orecchio.listen_and_transcribe()
print(comando)