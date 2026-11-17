import queue
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
from kivy.uix.popup import Popup

from jarvis_core.brain import ask_jarvis
from jarvis_core.cloud.session import session_manager


class JarvisInterface(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=[dp(15), dp(15), dp(15), dp(8)], spacing=dp(10), **kwargs)
        self.conversation = "JARVIS INITIALIZED\n\n"
        self.message_queue = queue.Queue()
        self.processing = False
        self.queue_lock = threading.Lock()
        self.history = []
        self.auth_popup = None
        self.auth_status = None

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(58), spacing=dp(8))
        self.title = Label(text="J.A.R.V.I.S", font_size=dp(28), bold=True, halign="left")
        self.title.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        self.login_button = Button(text="ACCOUNT", size_hint=(None, 1), width=dp(100), background_normal="", background_color=(0.05, 0.30, 0.52, 1))
        self.login_button.bind(on_press=self.open_auth_popup)
        header.add_widget(self.title)
        header.add_widget(self.login_button)

        self.status = Label(text="LOCAL AI • READY", font_size=dp(12), size_hint_y=None, height=dp(26))
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(3), size_hint=(1, 1))
        self.message_label = Label(text=self.conversation, font_size=dp(16), halign="left", valign="top", size_hint_y=None)
        self.message_label.bind(width=self.update_message_size, texture_size=self.update_message_height)
        self.scroll.add_widget(self.message_label)

        self.input = TextInput(
            hint_text="Type your message here...", multiline=False, size_hint=(1, 1),
            font_size=dp(16), padding=[dp(12), dp(14)],
            foreground_color=(1, 1, 1, 1), hint_text_color=(0.75, 0.78, 0.84, 1),
            cursor_color=(0.2, 0.65, 1, 1), background_normal="", background_active="",
            background_color=(0.08, 0.10, 0.15, 1), cursor_width=dp(2), input_type="text"
        )
        self.input.bind(on_text_validate=self.send_message)
        self.send_button = Button(text="SEND", size_hint=(None, 1), width=dp(85), background_normal="", background_down="", background_color=(0.05, 0.38, 0.75, 1), bold=True)
        self.send_button.bind(on_press=self.send_message)
        self.input_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(58), spacing=dp(8))
        self.input_row.add_widget(self.input)
        self.input_row.add_widget(self.send_button)

        self.add_widget(header)
        self.add_widget(self.status)
        self.add_widget(self.scroll)
        self.add_widget(self.input_row)

        threading.Thread(target=self.restore_auth_session, daemon=True).start()

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

    def send_message(self, instance):
        message = self.input.text.strip()
        if not message:
            return

        self.input.text = ""
        self.add_message("YOU", message)

        with self.queue_lock:
            self.message_queue.put(message)
            start_worker = not self.processing
            if start_worker:
                self.processing = True
            waiting = self.message_queue.qsize()

        if start_worker:
            self.status.text = "JARVIS IS THINKING..."
            threading.Thread(target=self.process_queue, daemon=True).start()
        elif waiting:
            self.status.text = f"MESSAGE QUEUED • {waiting} WAITING"

    def process_queue(self):
        while True:
            # Submission and worker shutdown use the same lock.
            with self.queue_lock:
                try:
                    message = self.message_queue.get_nowait()
                except queue.Empty:
                    self.processing = False
                    break

            try:
                response = ask_jarvis(message, history=self.history[-12:])
            except Exception as error:
                response = f"Something went wrong: {error}"

            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": response})

            Clock.schedule_once(
                lambda dt, answer=response: self.add_message("JARVIS", answer), 0
            )
            self.message_queue.task_done()
            Clock.schedule_once(self.update_queue_status, 0)

        Clock.schedule_once(self.update_queue_status, 0)

    def update_queue_status(self, dt):
        self.update_ready_status(dt)

    def update_ready_status(self, dt):
        with self.queue_lock:
            processing = self.processing
            waiting = self.message_queue.qsize()

        if session_manager.is_authenticated:
            self.login_button.text = "SIGN OUT"
            ready_status = "CLOUD AI • READY (LOCAL FALLBACK)"
        else:
            self.login_button.text = "ACCOUNT"
            ready_status = "LOCAL AI • READY • SIGN IN FOR CLOUD"

        if processing:
            self.status.text = (
                f"JARVIS IS THINKING... • {waiting} WAITING"
                if waiting else "JARVIS IS THINKING..."
            )
        else:
            self.status.text = ready_status

    def restore_auth_session(self):
        try:
            restored = session_manager.restore_session()
        except Exception:
            restored = False
        Clock.schedule_once(lambda dt: self.update_ready_status(dt), 0)

    def open_auth_popup(self, instance):
        if session_manager.is_authenticated:
            self.sign_out_popup()
            return
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))
        email = TextInput(hint_text="Email address", multiline=False, size_hint_y=None, height=dp(48), input_type="mail")
        password = TextInput(hint_text="Password", password=True, multiline=False, size_hint_y=None, height=dp(48))
        self.auth_status = Label(text="Sign in to enable Cloud AI. Local AI remains available.", size_hint_y=None, height=dp(54))
        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        sign_in = Button(text="SIGN IN")
        sign_up = Button(text="CREATE ACCOUNT")
        actions.add_widget(sign_in)
        actions.add_widget(sign_up)
        content.add_widget(email)
        content.add_widget(password)
        content.add_widget(self.auth_status)
        content.add_widget(actions)
        self.auth_popup = Popup(title="JARVIS ACCOUNT", content=content, size_hint=(0.92, None), height=dp(290), auto_dismiss=True)
        sign_in.bind(on_press=lambda *_: self.begin_auth("login", email.text, password.text, sign_in, sign_up))
        sign_up.bind(on_press=lambda *_: self.begin_auth("signup", email.text, password.text, sign_in, sign_up))
        self.auth_popup.open()

    def begin_auth(self, mode, email, password, sign_in_button, sign_up_button):
        if not email.strip() or not password:
            self.auth_status.text = "Enter your email and password."
            return
        sign_in_button.disabled = True
        sign_up_button.disabled = True
        self.auth_status.text = "Connecting securely..."
        threading.Thread(target=self.auth_worker, args=(mode, email.strip(), password, sign_in_button, sign_up_button), daemon=True).start()

    def auth_worker(self, mode, email, password, sign_in_button, sign_up_button):
        success = False
        message = ""
        try:
            if mode == "login":
                session_manager.sign_in(email, password)
                success = True
                message = "Signed in. Cloud AI is ready."
            else:
                result = session_manager.create_account(email, password)
                if result.get("access_token") and result.get("refresh_token"):
                    session_manager.sign_in(email, password)
                    success = True
                    message = "Account created and signed in."
                else:
                    message = "Account created. Check your email if confirmation is required, then sign in."
        except Exception as error:
            message = str(error)
        Clock.schedule_once(lambda dt: self.finish_auth(success, message, sign_in_button, sign_up_button), 0)

    def finish_auth(self, success, message, sign_in_button, sign_up_button):
        if self.auth_status:
            self.auth_status.text = message
        sign_in_button.disabled = False
        sign_up_button.disabled = False
        if success:
            if self.auth_popup:
                self.auth_popup.dismiss()
            self.login_button.text = "SIGN OUT"
            self.status.text = "CLOUD AI • READY (LOCAL FALLBACK)"

    def sign_out_popup(self):
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(14))
        content.add_widget(Label(text="Sign out of your Jarvis account?"))
        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        confirm = Button(text="SIGN OUT")
        cancel = Button(text="CANCEL")
        actions.add_widget(confirm)
        actions.add_widget(cancel)
        content.add_widget(actions)
        popup = Popup(title="ACCOUNT", content=content, size_hint=(0.85, None), height=dp(170))
        confirm.bind(on_press=lambda *_: self.begin_sign_out(popup))
        cancel.bind(on_press=lambda *_: popup.dismiss())
        popup.open()

    def begin_sign_out(self, popup):
        popup.dismiss()
        self.login_button.text = "ACCOUNT"
        self.status.text = "SIGNING OUT..."
        threading.Thread(target=self.sign_out_worker, daemon=True).start()

    def sign_out_worker(self):
        try:
            session_manager.sign_out()
        except Exception:
            pass
        Clock.schedule_once(self.update_ready_status, 0)
        Clock.schedule_once(lambda dt: setattr(self.login_button, "text", "ACCOUNT"), 0)


class JarvisApp(App):
    def build(self):
        self.title = "Jarvis"
        Window.softinput_mode = "below_target"
        return JarvisInterface()


if __name__ == "__main__":
    JarvisApp().run()
