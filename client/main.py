import speech_recognition as sr
import openai
import eye_tracker
import cv2
import numpy as np

from multiprocessing import Process, Manager
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


def imageProcess(transcription):
    cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    last_capture = time.time()

    tracker = eye_tracker.FrontendData()

    position_for_later = ()

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
            

            # # Capture a frame to BytesIO 
            # if time.time() - last_capture > 2:
            #     bytesio_obj = capture_frame_to_bytesio(cap)
            #     if bytesio_obj:
            #         print("Captured frame to BytesIO object.")

            #     last_capture = time.time()



            # Break the loop if the user presses the 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # os.system('cls' if os.name=='nt' else 'clear')
            
            
            # print(transcription.value)
            # print('', end='', flush=True)

    finally:
        cap.release()
        cv2.destroyAllWindows()

def audioProcess(shared_transcription):
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

def main():
    manager = Manager()
    shared_transcription = manager.Value(ctypes.c_char_p, "")

    cv2_process = Process(target=imageProcess, args=(shared_transcription,))
    audio_process = Process(target=audioProcess, args=(shared_transcription,))

    cv2_process.start()
    audio_process.start()

    cv2_process.join()


if __name__ == "__main__":
    main()