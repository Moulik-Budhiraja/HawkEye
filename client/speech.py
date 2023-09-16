import speech_recognition as sr

recognizer = sr.Recognizer()

while True:
    try:
        print("Listening for voice command...")
        with sr.Microphone() as source:
            audio = recognizer.listen(source, timeout=5)

        command = recognizer.recognize_google(audio)
        print(command)
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand the audio")
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")