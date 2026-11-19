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
from jarvis_core.cloud.keystore_diagnostic import run_keystore_diagnostic


BG = (0.0, 0.0, 0.0, 1)
PANEL = (0.025, 0.035, 0.029, 1)
GREEN = (0.18, 0.92, 0.48, 1)
HIGHLIGHT = (0.34, 1.0, 0.62, 1)
CYAN = GREEN  # Compatibility alias for existing UI references.
TEXT = (0.72, 0.91, 0.78, 1)
MUTED = (0.38, 0.55, 0.43, 1)
AMBER = (1.0, 0.62, 0.16, 1)


class RoundedBox(BoxLayout):
    def __init__(self, fill=PANEL, outline=None, radius=dp(24), **kwargs):
        super().__init__(**kwargs)
        self.fill = fill
        self.outline = outline
        self.radius = radius
        with self.canvas.before:
            self.bg_color = Color(*self.fill)
            self.bg_shape = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self.radius]
            )
            self.outline_color = Color(*(self.outline or (0, 0, 0, 0)))
            self.outline_shape = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, self.radius
                ),
                width=1,
            )
        self.bind(pos=self._sync_canvas, size=self._sync_canvas)

    def _sync_canvas(self, *_):
        self.bg_shape.pos = self.pos
        self.bg_shape.size = self.size
        self.outline_shape.rounded_rectangle = (
            self.x, self.y, self.width, self.height, self.radius
        )


class PillButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._pill_color = Color(*GREEN)
            self._pill_shape = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self.height / 2]
            )
        self.bind(pos=self._sync_pill, size=self._sync_pill)

    def _sync_pill(self, *_):
        self._pill_shape.pos = self.pos
        self._pill_shape.size = self.size
        self._pill_shape.radius = [self.height / 2]


class StartupProgress(Widget):
    """A simple progress bar updated only when a startup milestone completes."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.value = 0
        with self.canvas:
            Color(0.10, 0.15, 0.18, 1)
            self.track = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(4)]
            )
            self.fill_color = Color(*AMBER)
            self.fill = RoundedRectangle(
                pos=self.pos, size=(0, self.height), radius=[dp(4)]
            )
        self.bind(pos=self._redraw, size=self._redraw)

    def set_value(self, value):
        self.value = max(0, min(100, int(value)))
        self._redraw()

    def _redraw(self, *_):
        self.track.pos = self.pos
        self.track.size = self.size
        self.fill.pos = self.pos
        self.fill.size = (self.width * self.value / 100.0, self.height)


class StartupScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=[dp(32), dp(24), dp(32), dp(36)],
            spacing=dp(14),
            **kwargs,
        )
        with self.canvas.before:
            Color(*BG)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self.add_widget(Widget())
        brand = Label(
            text="J.A.R.V.I.S",
            color=HIGHLIGHT,
            font_size=dp(29),
            size_hint_y=None,
            height=dp(54),
        )
        self.add_widget(brand)
        self.add_widget(Widget(size_hint_y=None, height=dp(24)))

        self.headline = Label(
            text="JARVIS INITIALISING",
            color=AMBER,
            font_size=dp(19),
            bold=True,
            size_hint_y=None,
            height=dp(42),
        )
        self.add_widget(self.headline)

        self.progress = StartupProgress(size_hint_y=None, height=dp(6))
        self.add_widget(self.progress)

        self.detail = Label(
            text="Preparing interface...",
            color=MUTED,
            font_size=dp(12),
            size_hint_y=None,
            height=dp(28),
        )
        self.add_widget(self.detail)
        self.add_widget(Widget())

    def _sync_bg(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def set_stage(self, value, detail):
        self.progress.set_value(value)
        self.detail.text = detail

    def show_online(self):
        self.progress.set_value(100)
        self.headline.text = "JARVIS IS ONLINE"
        self.headline.color = HIGHLIGHT
        self.detail.text = "Ready to assist."


class ChatMessage(BoxLayout):
    def __init__(self, speaker, message, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            spacing=dp(8),
            padding=[0, dp(5), 0, dp(5)],
            **kwargs,
        )
        is_user = speaker == "YOU"
        bubble = RoundedBox(
            orientation="vertical",
            size_hint=(None, None),
            width=dp(270),
            padding=[dp(15), dp(11), dp(15), dp(11)],
            fill=(0.025, 0.12, 0.065, 1) if is_user else PANEL,
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
        body.bind(
            texture_size=lambda obj, size: setattr(
                obj, "height", size[1] + dp(2)
            )
        )
        bubble.add_widget(body)
        bubble.bind(
            minimum_height=lambda obj, value: setattr(obj, "height", value)
        )
        bubble.height = max(dp(44), body.texture_size[1] + dp(24))
        if is_user:
            self.add_widget(Widget())
            self.add_widget(bubble)
        else:
            avatar = Label(
                text="J",
                color=HIGHLIGHT,
                font_size=dp(18),
                bold=True,
                size_hint=(None, None),
                size=(dp(34), dp(34)),
            )
            self.add_widget(avatar)
            self.add_widget(bubble)
            self.add_widget(Widget())
        self.height = bubble.height + dp(10)


class JarvisInterface(BoxLayout):
    def __init__(self, on_ready=None, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=[dp(17), dp(8), dp(17), dp(10)],
            spacing=dp(8),
            **kwargs,
        )
        self.on_ready = on_ready
        self.conversation = ""
        self.message_queue = queue.Queue()
        self.processing = False
        self.queue_lock = threading.Lock()
        self.history = []
        self.auth_popup = None
        self.auth_status = None
        self.auth_buttons = None
        self.message_list = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(3),
            padding=[0, dp(8), 0, dp(12)],
        )
        self.message_list.bind(
            minimum_height=self.message_list.setter("height")
        )

        with self.canvas.before:
            Color(*BG)
            self.background = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_background, size=self._sync_background)

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(58),
            spacing=dp(8),
        )
        menu = Button(
            text="MENU",
            font_size=dp(11),
            size_hint=(None, 1),
            width=dp(52),
            color=TEXT,
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
        )
        menu.bind(on_press=self.open_menu)
        self.title = Label(
            text="J.A.R.V.I.S",
            color=HIGHLIGHT,
            font_size=dp(25),
            bold=False,
            halign="center",
        )
        self.title.bind(
            size=lambda obj, value: setattr(obj, "text_size", value)
        )
        self.login_button = Button(
            text="USER",
            font_size=dp(11),
            size_hint=(None, 1),
            width=dp(52),
            color=CYAN,
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
        )
        self.login_button.bind(on_press=self.open_auth_popup)
        header.add_widget(menu)
        header.add_widget(self.title)
        header.add_widget(self.login_button)

        status_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(28),
            spacing=dp(7),
        )
        status_row.add_widget(Widget())
        self.status_dot = Label(
            text="●",
            color=GREEN,
            size_hint=(None, 1),
            width=dp(15),
            font_size=dp(12),
        )
        self.status = Label(
            text="READY  •  SIGN IN FOR CLOUD AI",
            color=MUTED,
            font_size=dp(11),
            halign="center",
        )
        self.status.bind(
            size=lambda obj, value: setattr(obj, "text_size", value)
        )
        status_row.add_widget(self.status_dot)
        status_row.add_widget(self.status)
        status_row.add_widget(Widget())

        self.scroll = ScrollView(
            do_scroll_x=False,
            bar_width=dp(2),
            scroll_type=["bars", "content"],
        )
        self.scroll.add_widget(self.message_list)

        # Intentionally no welcome message: the conversation starts empty.

        composer = RoundedBox(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(64),
            padding=[dp(8), dp(7), dp(8), dp(7)],
            spacing=dp(7),
            fill=PANEL,
            outline=(0.12, 0.34, 0.20, 1),
            radius=dp(32),
        )
        self.mic_button = Button(
            text="MIC",
            font_size=dp(11),
            size_hint=(None, 1),
            width=dp(43),
            color=CYAN,
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
        )
        self.mic_button.bind(on_press=self.voice_notice)
        self.input = TextInput(
            hint_text="Message Jarvis...",
            multiline=False,
            size_hint=(1, 1),
            font_size=dp(16),
            padding=[dp(5), dp(13)],
            foreground_color=TEXT,
            hint_text_color=MUTED,
            cursor_color=CYAN,
            background_normal="",
            background_active="",
            background_color=(0, 0, 0, 0),
            cursor_width=dp(2),
            input_type="text",
        )
        self.input.bind(on_text_validate=self.send_message)
        self.send_button = PillButton(
            text="SEND",
            font_size=dp(11),
            size_hint=(None, 1),
            width=dp(76),
            color=(0.0, 0.04, 0.02, 1),
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
        )
        self.send_button.bind(on_press=self.send_message)
        composer.add_widget(self.mic_button)
        composer.add_widget(self.input)
        composer.add_widget(self.send_button)

        self.add_widget(header)
        self.add_widget(status_row)
        self.add_widget(self.scroll)
        self.add_widget(composer)

        threading.Thread(
            target=self.restore_auth_session, daemon=True
        ).start()

    def _sync_background(self, *_):
        self.background.pos = self.pos
        self.background.size = self.size

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
            threading.Thread(
                target=self.process_queue, daemon=True
            ).start()
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
                response = ask_jarvis(
                    message, history=self.history[-12:]
                )
            except Exception as error:
                response = f"Something went wrong: {error}"
            self.history.append({"role": "user", "content": message})
            self.history.append(
                {"role": "assistant", "content": response}
            )
            Clock.schedule_once(
                lambda dt, answer=response: self.add_message(
                    "JARVIS", answer
                ),
                0,
            )
            self.message_queue.task_done()
            Clock.schedule_once(self.update_queue_status, 0)
        Clock.schedule_once(self.update_queue_status, 0)

    def update_queue_status(self, _dt):
        with self.queue_lock:
            processing = self.processing
            waiting = self.message_queue.qsize()
        self.update_ready_status(0)
        if processing:
            self.status.text = (
                f"JARVIS IS THINKING...  •  {waiting} WAITING"
                if waiting
                else "JARVIS IS THINKING..."
            )

    def update_ready_status(self, _dt):
        self.login_button.text = "USER"
        if session_manager.is_authenticated:
            self.status.text = "READY  •  CLOUD AI AVAILABLE"
        else:
            self.status.text = "READY  •  SIGN IN FOR CLOUD AI"

    def restore_auth_session(self):
        try:
            session_manager.restore_session()
        except Exception:
            # Local access remains available if cloud session restore fails.
            pass
        Clock.schedule_once(self._finish_auth_restore, 0)

    def _finish_auth_restore(self, _dt):
        self.update_ready_status(0)
        if callable(self.on_ready):
            callback = self.on_ready
            self.on_ready = None
            callback()

    def open_menu(self, _instance):
        content = BoxLayout(
            orientation="vertical", spacing=dp(10), padding=dp(16)
        )
        content.add_widget(
            Label(text="J.A.R.V.I.S", color=HIGHLIGHT, font_size=dp(22))
        )
        content.add_widget(
            Label(
                text="Personal Private Assistant",
                color=MUTED,
                halign="center",
            )
        )
        content.add_widget(
            Label(text="Made by GUTS", color=GREEN, font_size=dp(12))
        )
        popup = Popup(
            title="MENU",
            content=content,
            size_hint=(0.84, None),
            height=dp(220),
        )
        popup.open()

    def voice_notice(self, _instance):
        content = Label(
            text="Voice input is not enabled in this build.",
            color=TEXT,
        )
        Popup(
            title="VOICE",
            content=content,
            size_hint=(0.82, None),
            height=dp(150),
        ).open()

    def open_auth_popup(self, _instance):
        if session_manager.is_authenticated:
            self.sign_out_popup()
            return
        content = BoxLayout(
            orientation="vertical", spacing=dp(10), padding=dp(14)
        )
        email = TextInput(
            hint_text="Email address",
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            input_type="mail",
            foreground_color=TEXT,
            cursor_color=GREEN,
        )
        password = TextInput(
            hint_text="Password",
            password=True,
            foreground_color=TEXT,
            cursor_color=GREEN,
            multiline=False,
            size_hint_y=None,
            height=dp(48),
        )
        self.auth_status = Label(
            text="Sign in to enable Cloud AI. Local AI remains available.",
            color=TEXT,
            size_hint_y=None,
            height=dp(54),
        )
        actions = BoxLayout(
            size_hint_y=None, height=dp(48), spacing=dp(8)
        )
        sign_in = Button(
            text="SIGN IN", color=(0.0, 0.04, 0.02, 1),
            background_normal="", background_down="",
            background_color=GREEN,
        )
        sign_up = Button(
            text="CREATE ACCOUNT", color=GREEN,
            background_normal="", background_down="",
            background_color=(0.025, 0.035, 0.029, 1),
        )
        actions.add_widget(sign_in)
        actions.add_widget(sign_up)
        content.add_widget(email)
        content.add_widget(password)
        content.add_widget(self.auth_status)
        content.add_widget(actions)
        self.auth_buttons = (sign_in, sign_up)
        self.auth_popup = Popup(
            title="JARVIS ACCOUNT",
            content=content,
            size_hint=(0.92, None),
            height=dp(290),
            auto_dismiss=True,
        )
        sign_in.bind(
            on_press=lambda *_: self.begin_auth(
                "login", email.text, password.text
            )
        )
        sign_up.bind(
            on_press=lambda *_: self.begin_auth(
                "signup", email.text, password.text
            )
        )
        self.auth_popup.open()

    def begin_auth(self, mode, email, password):
        if not email.strip() or not password:
            self.auth_status.text = "Enter your email and password."
            return
        for button in self.auth_buttons:
            button.disabled = True
        self.auth_status.text = "Connecting securely..."
        threading.Thread(
            target=self.auth_worker,
            args=(mode, email.strip(), password),
            daemon=True,
        ).start()

    def auth_worker(self, mode, email, password):
        success = False
        message = ""
        try:
            diagnostic = run_keystore_diagnostic()
            if "ANDROID KEYSTORE: ENCRYPTION AND DECRYPTION PASSED" not in diagnostic:
                raise RuntimeError(diagnostic)

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
                    message = (
                        "Account created. Check your email if confirmation "
                        "is required, then sign in."
                    )
        except Exception as error:
            message = str(error)
        Clock.schedule_once(
            lambda dt: self.finish_auth(success, message), 0
        )

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
        content = BoxLayout(
            orientation="vertical", spacing=dp(12), padding=dp(14)
        )
        content.add_widget(
            Label(text="Sign out of your Jarvis account?")
        )
        actions = BoxLayout(
            size_hint_y=None, height=dp(48), spacing=dp(8)
        )
        confirm = Button(
            text="SIGN OUT", color=(0.0, 0.04, 0.02, 1),
            background_normal="", background_down="",
            background_color=GREEN,
        )
        cancel = Button(
            text="CANCEL", color=GREEN,
            background_normal="", background_down="",
            background_color=PANEL,
        )
        actions.add_widget(confirm)
        actions.add_widget(cancel)
        content.add_widget(actions)
        popup = Popup(
            title="ACCOUNT",
            content=content,
            size_hint=(0.85, None),
            height=dp(170),
        )
        confirm.bind(
            on_press=lambda *_: self.begin_sign_out(popup)
        )
        cancel.bind(on_press=lambda *_: popup.dismiss())
        popup.open()

    def begin_sign_out(self, popup):
        popup.dismiss()
        self.status.text = "SIGNING OUT..."
        threading.Thread(
            target=self.sign_out_worker, daemon=True
        ).start()

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

        self.root_layout = BoxLayout()
        self.splash = StartupScreen()
        self.splash.set_stage(12, "Starting Jarvis...")
        self.root_layout.add_widget(self.splash)

        # Construct the chat UI and restore the secure session while the
        # splash screen remains visible. The progress only advances when
        # these actual startup milestones complete.
        Clock.schedule_once(self._prepare_interface, 0)
        return self.root_layout

    def _prepare_interface(self, _dt):
        self.splash.set_stage(35, "Preparing interface...")
        self.interface = JarvisInterface(on_ready=self._session_ready)
        self.splash.set_stage(58, "Restoring secure session...")

    def _session_ready(self):
        self.splash.set_stage(82, "Finalising startup...")
        Clock.schedule_once(self._show_online, 0)

    def _show_online(self, _dt):
        self.splash.show_online()
        Clock.schedule_once(self._show_chat, 0.9)

    def _show_chat(self, _dt):
        self.root_layout.clear_widgets()
        self.root_layout.add_widget(self.interface)


if __name__ == "__main__":
    JarvisApp().run()
