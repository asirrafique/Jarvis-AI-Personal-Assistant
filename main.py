import speech_recognition as sr
import pyttsx3
from gtts import gTTS
import pygame
import os

from dotenv import load_dotenv

from jarvis.agent import run_agent


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()


# ==========================================
# INITIALIZE
# ==========================================

recognizer = sr.Recognizer()
engine = pyttsx3.init()


# ==========================================
# TEXT-TO-SPEECH
# ==========================================

def speak_old(text):
    """
    Fallback offline TTS using pyttsx3.
    """
    try:
        engine.say(text)
        engine.runAndWait()

    except Exception as e:
        print("pyttsx3 Error:", e)


def speak(text):
    """
    Main Jarvis voice output using gTTS.
    """

    if not text:
        print("TTS Error: No text to speak")
        return

    # Make sure the value is a string
    text = str(text).strip()

    if not text:
        print("TTS Error: Empty text")
        return

    print("Jarvis:", text)

    temp_file = "temp.mp3"

    try:

        # ----------------------------------
        # Generate speech
        # ----------------------------------

        tts = gTTS(
            text=text,
            lang="en"
        )

        tts.save(temp_file)


        # ----------------------------------
        # Initialize pygame
        # ----------------------------------

        if not pygame.mixer.get_init():

            pygame.mixer.init()


        # ----------------------------------
        # Play speech
        # ----------------------------------

        pygame.mixer.music.load(
            temp_file
        )

        pygame.mixer.music.play()


        # ----------------------------------
        # Wait until speech finishes
        # ----------------------------------

        while pygame.mixer.music.get_busy():

            pygame.time.Clock().tick(10)


        # ----------------------------------
        # Cleanup
        # ----------------------------------

        pygame.mixer.music.unload()


        if os.path.exists(temp_file):

            os.remove(temp_file)


    except Exception as e:

        print(
            "TTS Error:",
            e
        )


        # ----------------------------------
        # Fallback to pyttsx3
        # ----------------------------------

        try:

            if pygame.mixer.get_init():

                pygame.mixer.music.stop()

                pygame.mixer.music.unload()


        except Exception:
            pass


        try:

            if os.path.exists(temp_file):

                os.remove(temp_file)

        except Exception:
            pass


        print(
            "Using pyttsx3 fallback..."
        )

        speak_old(text)


# ==========================================
# PROCESS COMMAND
# ==========================================

def process_command(command):

    if not command:

        return


    command = command.strip()


    if not command:

        return


    print(
        "Command:",
        command
    )


    try:

        # ==================================
        # SEND COMMAND TO AGENT
        # ==================================

        print(
            "Sending command to Jarvis Agent..."
        )


        response = run_agent(
            command
        )


        # ==================================
        # AGENT RESPONSE
        # ==================================

        if response:

            speak(
                response
            )

            return


        # ==================================
        # NO RESPONSE
        # ==================================

        speak(
            "Sorry, I could not complete "
            "that request."
        )


    except Exception as e:

        print(
            "Agent Error:",
            e
        )


        speak(
            "Sorry, something went wrong "
            "while processing your request."
        )


# ==========================================
# LISTEN FOR WAKE WORD
# ==========================================

def listen_for_wake_word():

    try:

        with sr.Microphone() as source:

            print(
                "Listening..."
            )


            # ----------------------------------
            # Adjust microphone
            # ----------------------------------

            recognizer.adjust_for_ambient_noise(
                source,
                duration=0.5
            )


            # ----------------------------------
            # Listen
            # ----------------------------------

            audio = recognizer.listen(
                source,
                timeout=5,
                phrase_time_limit=3
            )


        # --------------------------------------
        # Speech → Text
        # --------------------------------------

        word = recognizer.recognize_google(
            audio
        )


        print(
            "You:",
            word
        )


        return word.strip()


    except sr.WaitTimeoutError:

        print(
            "Listening timed out."
        )

        return None


    except sr.UnknownValueError:

        print(
            "Could not understand audio."
        )

        return None


    except sr.RequestError as e:

        print(
            "Speech recognition error:",
            e
        )

        return None


    except Exception as e:

        print(
            "Wake word error:",
            e
        )

        return None


# ==========================================
# LISTEN FOR COMMAND
# ==========================================

def listen_for_command():

    try:

        with sr.Microphone() as source:

            print(
                "Jarvis Active..."
            )


            # ----------------------------------
            # Listen for command
            # ----------------------------------

            audio = recognizer.listen(
                source,
                timeout=5,
                phrase_time_limit=15
            )


        # --------------------------------------
        # Speech → Text
        # --------------------------------------

        command = recognizer.recognize_google(
            audio
        )


        print(
            "Command:",
            command
        )


        return command.strip()


    except sr.WaitTimeoutError:

        print(
            "Command listening timed out."
        )

        return None


    except sr.UnknownValueError:

        print(
            "Could not understand command."
        )

        return None


    except sr.RequestError as e:

        print(
            "Speech recognition error:",
            e
        )

        return None


    except Exception as e:

        print(
            "Command recognition error:",
            e
        )

        return None


# ==========================================
# MAIN PROGRAM
# ==========================================

if __name__ == "__main__":

    speak(
        "Initializing Jarvis."
    )


    while True:

        print(
            "\nRecognizing..."
        )


        # ==================================
        # WAIT FOR WAKE WORD
        # ==================================

        word = listen_for_wake_word()


        if not word:

            continue


        # ==================================
        # CHECK WAKE WORD
        # ==================================

        if word.lower().strip() != "jarvis":

            continue


        # ==================================
        # JARVIS ACTIVATED
        # ==================================

        speak(
            "Ya"
        )


        # ==================================
        # LISTEN FOR USER COMMAND
        # ==================================

        command = listen_for_command()


        if not command:

            continue


        # ==================================
        # PROCESS COMMAND WITH AGENT
        # ==================================

        process_command(
            command
        )