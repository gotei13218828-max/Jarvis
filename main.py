import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.utils import platform


if platform == "android":
    from android.permissions import request_permissions, Permission
    from jnius import autoclass, PythonJavaClass, java_method


if platform == "android":

    class RecognitionListener(PythonJavaClass):

        __javainterfaces__ = [
            "android/speech/RecognitionListener"
        ]

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
            print("[JARVIS] End of speech")

        @java_method("(I)V")
        def onError(self, error):
            print("[JARVIS] Speech error code:", error)

            try:
                self.callback("", error)
            except Exception as e:
                print("[JARVIS] Callback error:", e)

        @java_method("(Landroid/os/Bundle;)V")
        def onResults(self, results):
            try:
                matches = results.getStringArrayList(
                    "results_recognition"
                )

                if matches and matches.size() > 0:
                    text = str(matches.get(0))
                else:
                    text = ""

                print("[JARVIS] Recognized:", text)

                self.callback(text, 0)

            except Exception as e:
                print(
                    "[JARVIS] Recognition result error:",
                    e
                )
                self.callback("", -1)

        @java_method("(Landroid/os/Bundle;)V")
        def onPartialResults(self, partial_results):
            pass

        @java_method("(ILandroid/os/Bundle;)V")
        def onEvent(self, event_type, params):
            pass


if platform == "android":

    class TTSListener(PythonJavaClass):

        __javainterfaces__ = [
            "android/speech/tts/TextToSpeech$OnInitListener"
        ]

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method("(I)V")
        def onInit(self, status):
            try:
                self.callback(status)
            except Exception as e:
                print("[JARVIS] TTS callback error:", e)


class JarvisApp(App):

    def build(self):

        self.speech_recognizer = None
        self.recognition_listener = None

        self.tts = None
        self.tts_listener = None
        self.tts_ready = False

        self.is_listening = False

        if platform == "android":

            try:
                request_permissions([
                    Permission.RECORD_AUDIO
                ])
            except Exception as e:
                print(
                    "[JARVIS] Permission error:",
                    e
                )

        self.layout = BoxLayout(
            orientation="vertical",
            padding=20,
            spacing=10
        )

        self.label = Label(
            text="Tap Mic to Talk to Jarvis",
            font_size="18sp"
        )

        self.layout.add_widget(
            self.label
        )

        self.mic_button = Button(
            text="🎤 MIC",
            font_size="24sp",
            size_hint=(1, 0.25)
        )

        self.mic_button.bind(
            on_press=self.start_listening
        )

        self.layout.add_widget(
            self.mic_button
        )

        self.stop_button = Button(
            text="STOP",
            font_size="20sp",
            size_hint=(1, 0.20)
        )

        self.stop_button.bind(
            on_press=self.stop_all
        )

        self.layout.add_widget(
            self.stop_button
        )

        if platform == "android":
            Clock.schedule_once(
                self.initialize_tts,
                0.5
            )

        return self.layout

    def initialize_tts(self, dt):

        if platform != "android":
            return

        try:

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            TextToSpeech = autoclass(
                "android.speech.tts.TextToSpeech"
            )

            self.tts_listener = TTSListener(
                self.on_tts_init
            )

            self.tts = TextToSpeech(
                PythonActivity.mActivity,
                self.tts_listener
            )

            print(
                "[JARVIS] Initializing Android TTS..."
            )

        except Exception as e:

            print(
                "[JARVIS] TTS initialization error:",
                e
            )

    def on_tts_init(self, status):

        Clock.schedule_once(
            lambda dt: self.finish_tts_init(
                status
            ),
            0
        )

    def finish_tts_init(self, status):

        try:

            TextToSpeech = autoclass(
                "android.speech.tts.TextToSpeech"
            )

            if status != TextToSpeech.SUCCESS:

                self.tts_ready = False

                print(
                    "[JARVIS] TTS initialization failed."
                )

                return

            Locale = autoclass(
                "java.util.Locale"
            )

            result = self.tts.setLanguage(
                Locale.US
            )

            if result == TextToSpeech.LANG_MISSING_DATA:

                self.tts_ready = False

                print(
                    "[JARVIS] TTS language data missing."
                )

                self.label.text = (
                    "TTS language data is missing."
                )

                return

            if result == TextToSpeech.LANG_NOT_SUPPORTED:

                self.tts_ready = False

                print(
                    "[JARVIS] TTS language not supported."
                )

                self.label.text = (
                    "TTS language is not supported."
                )

                return

            self.tts_ready = True

            print(
                "[JARVIS] Android TTS ready."
            )

        except Exception as e:

            self.tts_ready = False

            print(
                "[JARVIS] TTS setup error:",
                e
            )

    def start_listening(self, instance):

        if self.is_listening:
            return

        if platform == "android" and self.tts:

            try:
                if self.tts.isSpeaking():
                    self.tts.stop()
            except Exception:
                pass

        self.is_listening = True
        self.mic_button.disabled = True

        self.label.text = (
            "🎤 Listening..."
        )

        if platform == "android":

            threading.Thread(
                target=self.android_speech,
                daemon=True
            ).start()

        else:

            self.label.text = (
                "Speech recognition is available on Android."
            )

            self.mic_button.disabled = False
            self.is_listening = False

    def android_speech(self):

        try:

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            SpeechRecognizer = autoclass(
                "android.speech.SpeechRecognizer"
            )

            RecognizerIntent = autoclass(
                "android.content.Intent"
            )

            self.destroy_speech_recognizer()

            self.speech_recognizer = (
                SpeechRecognizer.createSpeechRecognizer(
                    PythonActivity.mActivity
                )
            )

            self.recognition_listener = RecognitionListener(
                self.on_speech_result
            )

            self.speech_recognizer.setRecognitionListener(
                self.recognition_listener
            )

            intent = RecognizerIntent(
                "android.speech.action.RECOGNIZE_SPEECH"
            )

            intent.putExtra(
                "android.speech.extra.LANGUAGE_MODEL",
                "free_form"
            )

            intent.putExtra(
                "android.speech.extra.MAX_RESULTS",
                1
            )

            intent.putExtra(
                "android.speech.extra.LANGUAGE",
                "en-US"
            )

            intent.putExtra(
                "android.speech.extra.PARTIAL_RESULTS",
                False
            )

            self.speech_recognizer.startListening(
                intent
            )

        except Exception as e:

            print(
                "[JARVIS] Speech recognition error:",
                e
            )

            Clock.schedule_once(
                lambda dt: self.speech_error(
                    str(e)
                ),
                0
            )

    def on_speech_result(
        self,
        text,
        error_code
    ):

        Clock.schedule_once(
            lambda dt: self.process_speech(
                text,
                error_code
            ),
            0
        )

    def process_speech(
        self,
        text,
        error_code
    ):

        self.is_listening = False
        self.mic_button.disabled = False

        if error_code != 0:

            self.show_speech_error(
                error_code
            )

            self.destroy_speech_recognizer()

            return

        if not text:

            self.label.text = (
                "❌ I didn't hear anything."
            )

            self.destroy_speech_recognizer()

            return

        self.label.text = (
            "You: " + text
        )

        print(
            "[JARVIS] User:",
            text
        )

        self.destroy_speech_recognizer()

        response = self.jarvis_response(
            text
        )

        self.show_response(
            response
        )

        self.speak(
            response
        )

    def jarvis_response(self, text):

        command = text.lower().strip()

        if "hello" in command:
            return (
                "Hello. I am Jarvis. "
                "How can I help you?"
            )

        if command == "hi" or command.startswith("hi "):
            return (
                "Hello. How can I help you?"
            )

        if "how are you" in command:
            return (
                "I am functioning normally."
            )

        if "your name" in command:
            return (
                "My name is Jarvis."
            )

        if "who are you" in command:
            return (
                "I am your personal assistant."
            )

        if "thank you" in command:
            return (
                "You're welcome."
            )

        if "thanks" in command:
            return (
                "You're welcome."
            )

        if "goodbye" in command:
            return "Goodbye."

        if command == "bye" or command.startswith("bye "):
            return "Goodbye."

        return "You said: " + text

    def show_response(self, response):

        self.label.text = (
            "Jarvis: " + response
        )

        print(
            "[JARVIS] Response:",
            response
        )

    def speak(self, text):

        if platform != "android":
            print(
                "[JARVIS] Android TTS unavailable."
            )
            return

        Clock.schedule_once(
            lambda dt: self._speak_android(
                text
            ),
            0
        )

    def _speak_android(self, text):

        if not self.tts:

            print(
                "[JARVIS] TTS is not initialized."
            )

            return

        if not self.tts_ready:

            print(
                "[JARVIS] TTS is not ready."
            )

            return

        try:

            TextToSpeech = autoclass(
                "android.speech.tts.TextToSpeech"
            )

            self.tts.speak(
                text,
                TextToSpeech.QUEUE_FLUSH,
                None,
                "jarvis"
            )

            print(
                "[JARVIS] Speaking:",
                text
            )

        except Exception as e:

            print(
                "[JARVIS] TTS error:",
                e
            )

    def stop_all(self, instance):

        self.is_listening = False
        self.mic_button.disabled = False

        self.destroy_speech_recognizer()

        if platform == "android" and self.tts:

            try:
                self.tts.stop()
            except Exception as e:
                print(
                    "[JARVIS] TTS stop error:",
                    e
                )

        self.label.text = (
            "Stopped. Tap Mic to talk."
        )

    def destroy_speech_recognizer(self):

        if platform != "android":
            return

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

            print(
                "[JARVIS] Recognizer cleanup error:",
                e
            )

    def show_speech_error(self, error_code):

        error_messages = {
            1: "Network timeout.",
            2: "Network error.",
            3: "Audio recording error.",
            4: "Server error.",
            5: "Client error.",
            6: "Speech timeout.",
            7: "I couldn't understand you.",
            8: "Recognition service is busy.",
            9: "Microphone permission is required.",
            10: "Language is not supported.",
            11: "Server busy.",
            12: "Server unavailable.",
            13: "Language download is unavailable."
        }

        message = error_messages.get(
            error_code,
            "Unknown speech recognition error."
        )

        self.label.text = (
            "❌ " + message
        )

        print(
            "[JARVIS] Speech error:",
            error_code,
            message
        )

    def speech_error(self, error):

        self.is_listening = False
        self.mic_button.disabled = False

        self.destroy_speech_recognizer()

        self.label.text = (
            "❌ Speech error: " + error
        )

    def on_stop(self):

        try:
            self.destroy_speech_recognizer()
        except Exception:
            pass

        if platform == "android" and self.tts:

            try:
                self.tts.stop()
            except Exception:
                pass

            try:
                self.tts.shutdown()
            except Exception:
                pass

            self.tts = None
            self.tts_listener = None
            self.tts_ready = False


if __name__ == "__main__":
    JarvisApp().run()