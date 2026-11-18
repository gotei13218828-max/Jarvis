import queue
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget

from jarvis_core.brain import ask_jarvis
from jarvis_core.cloud.session import session_manager


BG = (0.018, 0.025, 0.038, 1)
PANEL = (0.055, 0.075, 0.095, 1)
CYAN = (0.02, 0.78, 0.80, 1)
TEXT = (0.86, 0.91, 0.96, 1)
MUTED = (0.48, 0.56, 0.64, 1)


class RoundedBox(BoxLayout):
    def __init__(self, fill=PANEL, outline=None, radius=dp(24), **kwargs):
        super().__init__(**kwargs)
        self.fill = fill
        self.outline = outline
        self.radius = radius
        with self.canvas.before:
            self.bg_color = Color(*self.fill)
            self.bg_shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            self.outline_color = Color(*(self.outline or (0, 0, 0, 0)))
            self.outline_shape = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, self.radius), width=1)
        self.bind(pos=self._sync_canvas, size=self._sync_canvas)

    def _sync_canvas(self, *_):
        self.bg_shape.pos = self.pos
        self.bg_shape.size = self.size
        self.outline_shape.rounded_rectangle = (self.x, self.y, self.width, self.height, self.radius)


class ChatMessage(BoxLayout):
    def __init__(self, speaker, message, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, spacing=dp(8), padding=[0, dp(5), 0, dp(5)], **kwargs)
        is_user = speaker == "YOU"
        bubble = RoundedBox(
            orientation="vertical",
            size_hint=(None, None),
            width=dp(270),
            padding=[dp(15), dp(11), dp(15), dp(11)],
            fill=(0.015, 0.22, 0.24, 1) if is_user else (0.065, 0.085, 0.11, 1),
            radius=dp(20),
        )
        body = Label(
            text=message,
            color=TEXT,
            font_size=dp(16),
            halign="left",
            valign="middle",
            text_size=(dp(238), None),
            size_hint_y=None,
        )
        body.bind(texture_size=lambda obj, size: setattr(obj, "height", size[1] + dp(2)))
        bubble.add_widget(body)
        bubble.bind(minimum_height=lambda obj, value: setattr(obj, "height", value))
        bubble.height = max(dp(44), body.texture_size[1] + dp(24))
        if is_user:
            self.add_widget(Widget())
            self.add_widget(bubble)
        else:
            avatar = Label(text="[b]A[/b]", markup=True, color=CYAN, font_size=dp(17), size_hint=(None, None), size=(dp(34), dp(34)))
            self.add_widget(avatar)
            self.add_widget(bubble)
            self.add_widget(Widget())
        self.height = bubble.height + dp(10)


class JarvisInterface(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=[dp(17), dp(8), dp(17), dp(10)], spacing=dp(8), **kwargs)
        self.conversation = ""
        self.message_queue = queue.Queue()
        self.processing = False
        self.queue_lock = threading.Lock()
        self.history = []
        self.auth_popup = None
        self.auth_status = None
        self.auth_buttons = None
        self.message_list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(3), padding=[0, dp(8), 0, dp(12)])
        self.message_list.bind(minimum_height=self.message_list.setter("height"))

        with self.canvas.before:
            Color(*BG)
            self.background = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_background, size=self._sync_background)

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(58), spacing=dp(8))
        menu = Button(text="☰", font_size=dp(27), size_hint=(None, 1), width=dp(48), color=TEXT, background_normal="", background_down="", background_color=(0, 0, 0, 0))
        menu.bind(on_press=self.open_menu)
        self.title = Label(text="J.A.R.V.I.S", color=TEXT, font_size=dp(25), bold=False, halign="center")
        self.title.bind(size=lambda obj, value: setattr(obj, "text_size", value))
        self.login_button = Button(text="◉", font_size=dp(27), size_hint=(None, 1), width=dp(48), color=CYAN, background_normal="", background_down="", background_color=(0, 0, 0, 0))
        self.login_button.bind(on_press=self.open_auth_popup)
        header.add_widget(menu)
        header.add_widget(self.title)
        header.add_widget(self.login_button)

        status_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(7))
        status_row.add_widget(Widget())
        self.status_dot = Label(text="●", color=(0.05, 0.88, 0.49, 1), size_hint=(None, 1), width=dp(15), font_size=dp(12))
        self.status = Label(text="LOCAL AI READY  •  CHECKING CLOUD", color=MUTED, font_size=dp(11), halign="center")
        self.status.bind(size=lambda obj, value: setattr(obj, "text_size", value))
        status_row.add_widget(self.status_dot)
        status_row.add_widget(self.status)
        status_row.add_widget(Widget())

        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(2), scroll_type=["bars", "content"])
        self.scroll.add_widget(self.message_list)

        self.add_welcome()

        composer = RoundedBox(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(64),
            padding=[dp(8), dp(7), dp(8), dp(7)],
            spacing=dp(7),
            fill=(0.055, 0.075, 0.10, 1),
            outline=(0.15, 0.20, 0.25, 1),
            radius=dp(32),
        )
        self.mic_button = Button(text="🎙", font_size=dp(25), size_hint=(None, 1), width=dp(43), color=CYAN, background_normal="", background_down="", background_color=(0, 0, 0, 0))
        self.mic_button.bind(on_press=self.voice_notice)
        self.input = TextInput(
            hint_text="Message Jarvis...", multiline=False, size_hint=(1, 1),
            font_size=dp(16), padding=[dp(5), dp(13)],
            foreground_color=TEXT, hint_text_color=MUTED,
            cursor_color=CYAN, background_normal="", background_active="",
            background_color=(0, 0, 0, 0), cursor_width=dp(2), input_type="text",
        )
        self.input.bind(on_text_validate=self.send_message)
        self.send_button = Button(text="➤", font_size=dp(25), size_hint=(None, 1), width=dp(48), color=(1, 1, 1, 1), background_normal="", background_down="", background_color=CYAN)
        self.send_button.bind(on_press=self.send_message)
        composer.add_widget(self.mic_button)
        composer.add_widget(self.input)
        composer.add_widget(self.send_button)

        self.add_widget(header)
        self.add_widget(status_row)
        self.add_widget(self.scroll)
        self.add_widget(composer)

        threading.Thread(target=self.restore_auth_session, daemon=True).start()

    def _sync_background(self, *_):
        self.background.pos = self.pos
        self.background.size = self.size

    def add_welcome(self):
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(88), spacing=dp(12), padding=[0, dp(18), 0, 0])
        avatar = Label(text="[b]Λ[/b]", markup=True, color=CYAN, font_size=dp(28), size_hint=(None, None), size=(dp(52), dp(52)))
        greeting = Label(text="Hello! I'm J.A.R.V.I.S.\nHow can I help you today? ✨", color=TEXT, font_size=dp(17), halign="left", valign="middle")
        greeting.bind(size=lambda obj, value: setattr(obj, "text_size", value))
        row.add_widget(avatar)
        row.add_widget(greeting)
        self.message_list.add_widget(row)

    def add_message(self, speaker, message):
        self.message_list.add_widget(ChatMessage(speaker, message))
        Clock.schedule_once(self.scroll_to_bottom, 0.12)

    def scroll_to_bottom(self, _dt):
        self.scroll.scroll_y = 0

    def send_message(self, _instance):
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
            self.status.text = f"MESSAGE QUEUED  •  {waiting} WAITING"

    def process_queue(self):
        while True:
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
            Clock.schedule_once(lambda dt, answer=response: self.add_message("JARVIS", answer), 0)
            self.message_queue.task_done()
            Clock.schedule_once(self.update_queue_status, 0)
        Clock.schedule_once(self.update_queue_status, 0)

    def update_queue_status(self, _dt):
        with self.queue_lock:
            processing = self.processing
            waiting = self.message_queue.qsize()
        self.update_ready_status(0)
        if processing:
            self.status.text = f"JARVIS IS THINKING...  •  {waiting} WAITING" if waiting else "JARVIS IS THINKING..."

    def update_ready_status(self, _dt):
        if session_manager.is_authenticated:
            self.login_button.text = "◉"
            ready_status = "CLOUD AI READY  •  LOCAL FALLBACK"
        else:
            self.login_button.text = "◉"
            ready_status = "LOCAL AI READY  •  CLOUD OFFLINE"
        self.status.text = ready_status

    def restore_auth_session(self):
        try:
            session_manager.restore_session()
        except Exception:
            pass
        Clock.schedule_once(self.update_ready_status, 0)

    def open_menu(self, _instance):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(16))
        content.add_widget(Label(text="J.A.R.V.I.S", color=TEXT, font_size=dp(20)))
        content.add_widget(Label(text="Local AI with optional secure cloud access", color=MUTED, halign="center"))
        content.add_widget(Label(text="Made by GUTS", color=MUTED, font_size=dp(12)))
        popup = Popup(title="MENU", content=content, size_hint=(0.84, None), height=dp(220))
        popup.open()

    def voice_notice(self, _instance):
        content = Label(text="Voice input is not enabled in this build.", color=TEXT)
        Popup(title="VOICE", content=content, size_hint=(0.82, None), height=dp(150)).open()

    def open_auth_popup(self, _instance):
        if session_manager.is_authenticated:
            self.sign_out_popup()
            return
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))
        email = TextInput(hint_text="Email address", multiline=False, size_hint_y=None, height=dp(48), input_type="mail")
        password = TextInput(hint_text="Password", password=True, multiline=False, size_hint_y=None, height=dp(48))
        self.auth_status = Label(text="Sign in to enable Cloud AI. Local AI remains available.", color=TEXT, size_hint_y=None, height=dp(54))
        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        sign_in = Button(text="SIGN IN")
        sign_up = Button(text="CREATE ACCOUNT")
        actions.add_widget(sign_in)
        actions.add_widget(sign_up)
        content.add_widget(email)
        content.add_widget(password)
        content.add_widget(self.auth_status)
        content.add_widget(actions)
        self.auth_buttons = (sign_in, sign_up)
        self.auth_popup = Popup(title="JARVIS ACCOUNT", content=content, size_hint=(0.92, None), height=dp(290), auto_dismiss=True)
        sign_in.bind(on_press=lambda *_: self.begin_auth("login", email.text, password.text))
        sign_up.bind(on_press=lambda *_: self.begin_auth("signup", email.text, password.text))
        self.auth_popup.open()

    def begin_auth(self, mode, email, password):
        if not email.strip() or not password:
            self.auth_status.text = "Enter your email and password."
            return
        for button in self.auth_buttons:
            button.disabled = True
        self.auth_status.text = "Connecting securely..."
        threading.Thread(target=self.auth_worker, args=(mode, email.strip(), password), daemon=True).start()

    def auth_worker(self, mode, email, password):
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
        Clock.schedule_once(lambda dt: self.finish_auth(success, message), 0)

    def finish_auth(self, success, message):
        if self.auth_status:
            self.auth_status.text = message
        if self.auth_buttons:
            for button in self.auth_buttons:
                button.disabled = False
        if success:
            if self.auth_popup:
                self.auth_popup.dismiss()
            self.update_ready_status(0)

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
        self.status.text = "SIGNING OUT..."
        threading.Thread(target=self.sign_out_worker, daemon=True).start()

    def sign_out_worker(self):
        try:
            session_manager.sign_out()
        except Exception:
            pass
        Clock.schedule_once(self.update_ready_status, 0)


class JarvisApp(App):
    def build(self):
        self.title = "Jarvis"
        Window.clearcolor = BG
        Window.softinput_mode = "below_target"
        return JarvisInterface()


if __name__ == "__main__":
    JarvisApp().run()
