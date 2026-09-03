import os
import threading
import tempfile
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.utils import platform

from gtts import gTTS

# Android-specific imports
if platform == "android":
    from android.permissions import request_permissions, check_permission, Permission
    from android.runnable import run_on_ui_thread
    from jnius import autoclass, PythonJavaClass, java_method
else:
    # Dummy decorator for non-Android desktop testing
    def run_on_ui_thread(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper


if platform == "android":

    class RecognitionListener(PythonJavaClass):
        """Java proxy for android.speech.RecognitionListener."""
        __javainterfaces__ = ["android/speech/RecognitionListener"]

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method("(Landroid/os/Bundle;)V")
        def onReadyForSpeech(self, params):
            print("[JARVIS] Ready for speech")

        @java_method("()V")
        def onBeginningOfSpeech(self):
            print("[JARVIS] Beginning of speech")

        @java_method("(F)V")
        def onRmsChanged(self, rmsdB):
            pass

        @java_method("([B)V")
        def onBufferReceived(self, buffer):
            pass

        @java_method("()V")
        def onEndOfSpeech(self):
            print("[JARVIS] End of speech detected")

        @java_method("(I)V")
        def onError(self, error):
            print(f"[JARVIS] Speech error code: {error}")
            try:
                self.callback("", error)
            except Exception as e:
                print(f"[JARVIS] Callback error: {e}")

        @java_method("(Landroid/os/Bundle;)V")
        def onResults(self, results):
            try:
                matches = results.getStringArrayList("results_recognition")
                if matches and matches.size() > 0:
                    text = str(matches.get(0))
                else:
                    text = ""
                print(f"[JARVIS] Recognized text: {text}")
                self.callback(text, 0)
            except Exception as e:
                print(f"[JARVIS] Recognition result error: {e}")
                self.callback("", -1)

        @java_method("(Landroid/os/Bundle;)V")
        def onPartialResults(self, partial_results):
            pass

        @java_method("(ILandroid/os/Bundle;)V")
        def onEvent(self, event_type, params):
            pass


class JarvisApp(App):

    def build(self):
        self.layout = BoxLayout(
            orientation="vertical",
            padding=25,
            spacing=15
        )

        self.label = Label(
            text="Jarvis v1 — Ready\nTap MIC to talk",
            font_size="20sp",
            halign="center"
        )
        self.layout.add_widget(self.label)

        self.mic_button = Button(
            text="🎤 MIC",
            font_size="24sp",
            size_hint=(1, 0.25)
        )
        self.mic_button.bind(on_press=self.start_listening)
        self.layout.add_widget(self.mic_button)

        self.stop_button = Button(
            text="STOP",
            font_size="20sp",
            size_hint=(1, 0.20)
        )
        self.stop_button.bind(on_press=self.stop_listening)
        self.layout.add_widget(self.stop_button)

        self.speech_recognizer = None
        self.recognition_listener = None
        self.is_listening = False
        self.is_speaking = False

        # Request required permissions at launch
        if platform == "android":
            self.request_android_permissions()

        return self.layout

    def request_android_permissions(self):
        try:
            permissions = [Permission.RECORD_AUDIO]
            request_permissions(permissions)
        except Exception as e:
            print(f"[JARVIS] Permission request error: {e}")

    def has_audio_permission(self):
        if platform != "android":
            return True
        try:
            return check_permission(Permission.RECORD_AUDIO)
        except Exception:
            return False

    def start_listening(self, instance):
        if self.is_listening:
            return

        if self.is_speaking:
            self.label.text = "Jarvis is speaking. Please wait..."
            return

        if platform == "android" and not self.has_audio_permission():
            self.label.text = "❌ Microphone permission not granted."
            self.request_android_permissions()
            return

        self.is_listening = True
        self.mic_button.disabled = True
        self.label.text = "🎤 Listening..."

        if platform == "android":
            # SpeechRecognizer MUST be called on the Android UI Thread
            self.android_speech_on_ui()
        else:
            self.label.text = "Speech recognition is only supported on Android devices."
            self.mic_button.disabled = False
            self.is_listening = False

    @run_on_ui_thread
    def android_speech_on_ui(self):
        """Initializes and activates SpeechRecognizer on the main Android thread."""
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
            RecognizerIntent = autoclass("android.content.Intent")

            # Clean any previously dangling recognizer instance first
            self.cleanup_recognizer()

            activity = PythonActivity.mActivity

            if not SpeechRecognizer.isRecognitionAvailable(activity):
                Clock.schedule_once(
                    lambda dt: self.speech_error("Speech recognition is not available on this device."),
                    0
                )
                return

            self.speech_recognizer = SpeechRecognizer.createSpeechRecognizer(activity)
            self.recognition_listener = RecognitionListener(self.on_speech_result)
            self.speech_recognizer.setRecognitionListener(self.recognition_listener)

            intent = RecognizerIntent("android.speech.action.RECOGNIZE_SPEECH")
            intent.putExtra("android.speech.extra.LANGUAGE_MODEL", "free_form")
            intent.putExtra("android.speech.extra.MAX_RESULTS", 1)
            intent.putExtra("android.speech.extra.LANGUAGE", "en-US")
            intent.putExtra("android.speech.extra.PARTIAL_RESULTS", False)

            self.speech_recognizer.startListening(intent)

        except Exception as e:
            print(f"[JARVIS] Error starting recognizer: {e}")
            Clock.schedule_once(lambda dt: self.speech_error(str(e)), 0)

    def on_speech_result(self, text, error_code):
        Clock.schedule_once(lambda dt: self.process_speech(text, error_code), 0)

    def process_speech(self, text, error_code):
        self.is_listening = False
        self.mic_button.disabled = False

        if error_code != 0:
            self.show_speech_error(error_code)
            self.destroy_speech_recognizer()
            return

        if not text or not text.strip():
            self.label.text = "❌ I didn't catch that. Tap Mic to retry."
            self.destroy_speech_recognizer()
            return

        self.label.text = f"You: {text}"
        self.destroy_speech_recognizer()

        response = self.jarvis_response(text)
        self.show_response(response)

        # Run TTS generation and playback in a background thread to prevent UI freezing
        threading.Thread(
            target=self.speak,
            args=(response,),
            daemon=True
        ).start()

    def jarvis_response(self, text):
        command = text.lower().strip()

        if "hello" in command:
            return "Hello. I am Jarvis. How can I help you?"
        if command == "hi" or command.startswith("hi "):
            return "Hello. How can I help you?"
        if "how are you" in command:
            return "I am functioning normally and ready to assist."
        if "your name" in command:
            return "My name is Jarvis."
        if "who are you" in command:
            return "I am your personal voice assistant."
        if "thank you" in command or "thanks" in command:
            return "You are very welcome."
        if "goodbye" in command or command == "bye" or command.startswith("bye "):
            return "Goodbye."

        return f"You said: {text}"

    def show_response(self, response):
        self.label.text = f"Jarvis: {response}"

    def speak(self, text):
        temp_file = None
        player = None
        self.is_speaking = True

        try:
            fd, temp_file = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)

            # Generate MP3 via gTTS
            tts = gTTS(text=text, lang="en")
            tts.save(temp_file)

            if platform == "android":
                MediaPlayer = autoclass("android.media.MediaPlayer")
                player = MediaPlayer()
                
                # Pass absolute path to Android MediaPlayer
                player.setDataSource(os.path.abspath(temp_file))
                player.prepare()
                player.start()

                while player.isPlaying():
                    time.sleep(0.08)

            else:
                print(f"[JARVIS Desktop Mock] Audio written to: {temp_file}")
                time.sleep(1.0)

        except Exception as e:
            print(f"[JARVIS] TTS error: {e}")
            Clock.schedule_once(lambda dt: self.tts_error(str(e)), 0)

        finally:
            self.is_speaking = False
            if player:
                try:
                    player.stop()
                except Exception:
                    pass
                try:
                    player.release()
                except Exception:
                    pass

            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f"[JARVIS] Cleanup warning: {e}")

    def stop_listening(self, instance=None):
        self.is_listening = False
        self.mic_button.disabled = False
        self.destroy_speech_recognizer()
        self.label.text = "Stopped. Tap Mic to talk."

    def destroy_speech_recognizer(self):
        if platform == "android":
            self.cleanup_recognizer()

    @run_on_ui_thread
    def cleanup_recognizer(self):
        """Destroys recognizer strictly on the UI thread."""
        try:
            if self.speech_recognizer:
                try:
                    self.speech_recognizer.stopListening()
                except Exception:
                    pass
                try:
                    self.speech_recognizer.cancel()
                except Exception:
                    pass
                try:
                    self.speech_recognizer.destroy()
                except Exception:
                    pass
                self.speech_recognizer = None
            self.recognition_listener = None
        except Exception as e:
            print(f"[JARVIS] Cleanup error: {e}")

    def show_speech_error(self, error_code):
        error_messages = {
            1: "Network timeout.",
            2: "Network error.",
            3: "Audio recording error.",
            4: "Server error.",
            5: "Client error.",
            6: "No speech detected (timeout).",
            7: "Could not understand audio.",
            8: "Recognition service busy.",
            9: "Microphone permission required.",
            10: "Language not supported.",
            11: "Server busy.",
            12: "Server unavailable.",
            13: "Language download unavailable."
        }
        msg = error_messages.get(error_code, f"Speech error code {error_code}")
        self.label.text = f"❌ {msg}"

    def speech_error(self, error):
        self.is_listening = False
        self.mic_button.disabled = False
        self.destroy_speech_recognizer()
        self.label.text = f"❌ Error: {error}"

    def tts_error(self, error):
        self.label.text = f"❌ TTS Error: {error}"

    def on_stop(self):
        self.destroy_speech_recognizer()


if __name__ == "__main__":
    JarvisApp().run()