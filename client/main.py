import speech_recognition as sr
import openai
import eye_tracker
import cv2
import numpy as np
import pyttsx3

from multiprocessing import Process, Manager
from threading import Thread
from function_manager import *
from vision import *
import time
import io
import os
from datetime import datetime, timedelta
from queue import Queue
from tempfile import NamedTemporaryFile
import ctypes
from dotenv import load_dotenv
load_dotenv()


openai.api_key = os.getenv("OPENAI_API_KEY")

transcription_queue = Queue()
transcription_result_queue = Queue()
transcript_queued = False
transcripts_processed = 0

engine = pyttsx3.init()

def capture_frame_to_bytesio(cap):
    """
    Captures a frame from the video capture object and stores it in a BytesIO object.
    Returns the BytesIO object containing the image data.
    """
    ret, frame = cap.read()
    if not ret:
        return None

    is_success, buffer = cv2.imencode(".jpg", frame)
    if not is_success:
        return None

    bytesio_obj = io.BytesIO(buffer)
    return bytesio_obj



def calculate_h_v_fov(diagonal_fov, aspect_ratio):
    d = np.tan(np.radians(diagonal_fov) / 2)
    w = aspect_ratio[0] / np.sqrt(aspect_ratio[0]**2 + aspect_ratio[1]**2)
    h = aspect_ratio[1] / np.sqrt(aspect_ratio[0]**2 + aspect_ratio[1]**2)
    hfov = 2 * np.arctan(w / (2*d))
    vfov = 2 * np.arctan(h / (2*d))
    return np.degrees(hfov), np.degrees(vfov)

def project_3d_to_2d(point, hfov, vfov):
    x, y, z, _ = point
    x_prime = x / (z * np.tan(np.radians(hfov) / 2))
    y_prime = y / (z * np.tan(np.radians(vfov) / 2))
    return x_prime, y_prime

def viewport_transform(point, screen_width, screen_height):
    x_prime, y_prime = point
    x_double_prime = (screen_width * (x_prime + 1)) / 2
    y_double_prime = (screen_height * (1 - y_prime)) / 2
    return int(x_double_prime), int(y_double_prime)


def handle_transcriptions():
    global transcript_queued, transcripts_processed

    while True:
        if not transcription_queue.empty():
            transcription = transcription_queue.get()
            processed_transcript = process_inputs(transcription)

            result = get_function_call(processed_transcript[transcripts_processed + 1:])

            # print(f"{processed_transcript[transcripts_processed + 1:]} {transcripts_processed}")

            transcription_result_queue.put(result)
            transcripts_processed = len(processed_transcript) - 1
        else: 
            transcript_queued = False
            time.sleep(0.1)


def imageProcess(transcription, to_speak, is_mic_on):
    global transcript_queued, transcripts_processed

    cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    tracker = eye_tracker.FrontendData(to_speak, is_mic_on)

    transcription_thread = Thread(target=handle_transcriptions, daemon=True)
    transcription_thread.start()

    last_transcript = ""


    try:
        while True:
            # Display the camera feed in a window
            ret, frame = cap.read()
            if not ret:
                break

            if tracker.current_gaze != [0, 0, 0, 0]:
                hfov, vfov = calculate_h_v_fov(82, (4, 3))
                normalized_2d_point = project_3d_to_2d(tracker.current_gaze, hfov, vfov)
                pixel_point = viewport_transform(normalized_2d_point, frame.shape[1], frame.shape[0])

                centre_point = (550 -pixel_point[0], 175 -pixel_point[1])

                cv2.circle(frame,  centre_point, 5, (0, 0, 255), -1)

                box_size = 30

                cv2.rectangle(frame, (centre_point[0] - box_size * 4, centre_point[1] - box_size * 3), (centre_point[0] + box_size * 4, centre_point[1] + box_size * 3), (0, 255, 0), 2)


            cv2.imshow('Camera Feed', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            if not transcription.value == last_transcript:
                if last_transcript.split("\n")[-1] != transcription.value.split("\n")[-1]:
                    transcripts_processed = min(len(transcription.value.split("\n")) - 2, transcripts_processed) 

                last_transcript = transcription.value

            if not transcript_queued:
                transcript_queued = True
                transcription_queue.put(transcription.value)

            if not transcription_result_queue.empty() and to_speak.value == "":
                command, context = transcription_result_queue.get()

                if command == "ocr":
                    print("OCR")

                    buffer = capture_frame_to_bytesio(cap)

                    try:
                        # Get partial buffer of target area
                        image = cv2.imdecode(np.frombuffer(buffer.getbuffer(), np.uint8), cv2.IMREAD_UNCHANGED)
                        target_image = image[centre_point[1] - box_size * 3:centre_point[1] + box_size * 3, centre_point[0] - box_size * 4:centre_point[0] + box_size * 4]


                        _, target_buffer = cv2.imencode(".jpg", target_image)
                        target_image_buffer = io.BytesIO(target_buffer)                    

                        response = parse_double_ocr(buffer, target_image_buffer, context)

                    except Exception:
                        response = parse_ocr(ocr(buffer), context)


                    print(response)
                    to_speak.value = response

                if command == "ai_answer":
                    print("AI Answer", context)

                    print(context)
                    to_speak.value = context





    finally:
        cap.release()
        cv2.destroyAllWindows()

def audioProcess(shared_transcription, to_speak, is_mic_on):
    phrase_time = None

    last_sample = bytes()

    data_queue = Queue()

    recorder = sr.Recognizer()
    recorder.energy_threshold = 1000
    # Definitely do this, dynamic energy compensation lowers the energy threshold dramtically to a point where the SpeechRecognizer never stops recording.
    recorder.dynamic_energy_threshold = False
    
    source = sr.Microphone(sample_rate=16000)
    

    record_timeout = 2
    phrase_timeout = 3

    temp_file = NamedTemporaryFile().name
    transcription = ['']
    
    with source:
        recorder.adjust_for_ambient_noise(source)

    def record_callback(_, audio:sr.AudioData) -> None:
        """
        Threaded callback function to recieve audio data when recordings finish.
        audio: An AudioData containing the recorded bytes.
        """

        if to_speak.value != "" or not is_mic_on.value:
            return

        # Grab the raw bytes and push it into the thread safe queue.
        data = audio.get_raw_data()
        data_queue.put(data)

    # Create a background thread that will pass us raw audio bytes.
    # We could do this manually but SpeechRecognizer provides a nice helper.
    recorder.listen_in_background(source, record_callback, phrase_time_limit=record_timeout)

    # Cue the user that we're ready to go.
    print("Model loaded.\n")

    while True:
        try:
            now = datetime.utcnow()

            # Pull raw recorded audio from the queue.
            if not data_queue.empty():
                phrase_complete = False
                # If enough time has passed between recordings, consider the phrase complete.
                # Clear the current working audio buffer to start over with the new data.
                if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                    last_sample = bytes()
                    phrase_complete = True
                # This is the last time we received new audio data from the queue.
                phrase_time = now

                # Concatenate our current audio data with the latest audio data.
                while not data_queue.empty():
                    data = data_queue.get()
                    last_sample += data

                # Use AudioData to convert the raw data to wav data.
                audio_data = sr.AudioData(last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH)
                wav_data = io.BytesIO(audio_data.get_wav_data())

                # Write wav data to the temporary file as bytes.
                with open(temp_file + ".wav", 'w+b') as f:
                    f.write(wav_data.read())

                wav_data.name = "audio.wav"

                # Read the transcription.
                # result = audio_model.transcribe(temp_file, fp16=torch.cuda.is_available())
                with open(temp_file + ".wav", 'rb') as f:
                    result = openai.Audio.transcribe("whisper-1", file=f, prompt=f"Always use english. Names: {os.getenv('NAMES')}")
                
                text = result['text'].strip()

                # If we detected a pause between recordings, add a new item to our transcripion.
                # Otherwise edit the existing one.
                if phrase_complete:
                    transcription.append(text)
                else:
                    transcription[-1] = text

                # Clear the console to reprint the updated transcription.
                os.system('cls' if os.name=='nt' else 'clear')
                for line in transcription:
                    print(line)

                shared_transcription.value = "\n".join(transcription)


                time.sleep(0.25)
        except KeyboardInterrupt:
            break

def ttsProcess(to_speak):
    while True:
        if not to_speak.value == "":
            engine.say(to_speak.value)
            engine.runAndWait()
            time.sleep(0.5)
            to_speak.value = ""


def main():
    manager = Manager()
    shared_transcription = manager.Value(ctypes.c_char_p, "")
    to_speak = manager.Value(ctypes.c_char_p, "")
    is_mic_on = manager.Value(ctypes.c_bool, True)

    cv2_process = Process(target=imageProcess, args=(shared_transcription, to_speak, is_mic_on), daemon=True)
    audio_process = Process(target=audioProcess, args=(shared_transcription, to_speak, is_mic_on), daemon=True)
    tts_process = Process(target=ttsProcess, args=(to_speak,), daemon=True)

    cv2_process.start()
    audio_process.start()
    tts_process.start()

    cv2_process.join()


if __name__ == "__main__":
    main()