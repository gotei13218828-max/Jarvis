from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp


class JarvisShell(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(30), spacing=dp(20), **kwargs)

        self.title = Label(
            text="JARVIS",
            font_size=dp(42),
            bold=True,
            size_hint=(1, 0.25)
        )

        self.status = Label(
            text="Jarvis v1\nShell initialized",
            font_size=dp(22),
            halign="center",
            valign="middle",
            size_hint=(1, 0.45)
        )
        self.status.bind(size=self._update_text_size)

        self.button = Button(
            text="JARVIS",
            font_size=dp(22),
            size_hint=(1, 0.2)
        )
        self.button.bind(on_press=self.on_button_pressed)

        self.info = Label(
            text="v1.0 • Core shell only",
            font_size=dp(14),
            size_hint=(1, 0.1)
        )

        self.add_widget(self.title)
        self.add_widget(self.status)
        self.add_widget(self.button)
        self.add_widget(self.info)

    def _update_text_size(self, instance, value):
        instance.text_size = value

    def on_button_pressed(self, instance):
        self.status.text = "Jarvis v1\nReady."


class JarvisApp(App):
    def build(self):
        self.title = "Jarvis"
        return JarvisShell()


if __name__ == "__main__":
    JarvisApp().run()