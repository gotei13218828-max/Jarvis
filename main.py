import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

from jarvis_core.brain import ask_jarvis
from jarvis_core.cloud.keystore_diagnostic import (
    run_keystore_diagnostic,
)


class JarvisInterface(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=[dp(15), dp(15), dp(15), dp(8)],
            spacing=dp(10),
            **kwargs
        )

        self.conversation = "JARVIS INITIALIZED\n\n"
        self.busy = False
        self.diagnostic_running = False

        self.title = Label(
            text="J.A.R.V.I.S",
            font_size=dp(32),
            bold=True,
            size_hint_y=None,
            height=dp(65)
        )

        self.status = Label(
            text="LOCAL AI • READY",
            font_size=dp(13),
            size_hint_y=None,
            height=dp(30)
        )

        self.test_button = Button(
            text="TEST ANDROID KEYSTORE",
            size_hint_y=None,
            height=dp(42),
            background_normal="",
            background_color=(0.12, 0.35, 0.55, 1),
            color=(1, 1, 1, 1),
            bold=True
        )

        self.test_button.bind(
            on_press=self.start_keystore_test
        )

        self.scroll = ScrollView(
            do_scroll_x=False,
            bar_width=dp(3),
            size_hint=(1, 1)
        )

        self.message_label = Label(
            text=self.conversation,
            font_size=dp(17),
            halign="left",
            valign="top",
            size_hint_y=None
        )

        self.message_label.bind(
            width=self.update_message_size,
            texture_size=self.update_message_height
        )

        self.scroll.add_widget(self.message_label)

        self.input = TextInput(
            hint_text="Type your message here...",
            multiline=False,
            size_hint=(1, 1),
            font_size=dp(16),
            padding=[dp(12), dp(14)],
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.75, 0.78, 0.84, 1),
            cursor_color=(0.2, 0.65, 1, 1),
            background_normal="",
            background_active="",
            background_color=(0.08, 0.10, 0.15, 1),
            cursor_width=dp(2)
        )

        self.input.bind(
            on_text_validate=self.send_message
        )

        self.send_button = Button(
            text="SEND",
            size_hint=(None, 1),
            width=dp(85),
            background_normal="",
            background_down="",
            background_color=(0.05, 0.38, 0.75, 1),
            color=(1, 1, 1, 1),
            bold=True
        )

        self.send_button.bind(
            on_press=self.send_message
        )

        self.input_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(58),
            spacing=dp(8)
        )

        self.input_row.add_widget(self.input)
        self.input_row.add_widget(self.send_button)

        self.add_widget(self.title)
        self.add_widget(self.status)
        self.add_widget(self.test_button)
        self.add_widget(self.scroll)
        self.add_widget(self.input_row)

    def update_message_size(self, instance, width):
        instance.text_size = (width, None)

    def update_message_height(self, instance, texture_size):
        instance.height = texture_size[1] + dp(25)

    def add_message(self, speaker, message):
        self.conversation += f"{speaker}:\n{message}\n\n"
        self.message_label.text = self.conversation

        Clock.schedule_once(self.scroll_to_bottom, 0.1)

    def scroll_to_bottom(self, dt):
        self.scroll.scroll_y = 0

    def start_keystore_test(self, instance):
        if self.diagnostic_running:
            return

        self.diagnostic_running = True
        self.test_button.disabled = True
        self.status.text = "TESTING ANDROID KEYSTORE..."

        threading.Thread(
            target=self.process_keystore_test,
            daemon=True
        ).start()

    def process_keystore_test(self):
        try:
            result = run_keystore_diagnostic()
        except Exception as error:
            result = (
                "KEYSTORE TEST FAILED: "
                + type(error).__name__
                + ": "
                + str(error)
            )

        Clock.schedule_once(
            lambda dt: self.finish_keystore_test(result),
            0
        )

    def finish_keystore_test(self, result):
        self.add_message("KEYSTORE DIAGNOSTIC", result)

        if "PASSED" in result:
            self.status.text = "ANDROID KEYSTORE • VERIFIED"
        else:
            self.status.text = "KEYSTORE TEST • FAILED"

        self.test_button.disabled = False
        self.diagnostic_running = False

    def send_message(self, instance):
        message = self.input.text.strip()

        if not message or self.busy:
            return

        self.input.text = ""
        self.busy = True
        self.send_button.disabled = True

        self.add_message("YOU", message)
        self.status.text = "JARVIS IS THINKING..."

        threading.Thread(
            target=self.process_message,
            args=(message,),
            daemon=True
        ).start()

    def process_message(self, message):
        try:
            response = ask_jarvis(message)
        except Exception as error:
            response = f"Something went wrong: {error}"

        Clock.schedule_once(
            lambda dt: self.finish_response(response),
            0
        )

    def finish_response(self, response):
        self.add_message("JARVIS", response)

        self.status.text = "LOCAL AI • READY"
        self.busy = False
        self.send_button.disabled = False


class JarvisApp(App):

    def build(self):
        self.title = "Jarvis"
        Window.softinput_mode = "below_target"

        return JarvisInterface()


if __name__ == "__main__":
    JarvisApp().run()
