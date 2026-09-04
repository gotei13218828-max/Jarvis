from kivy.app import App
from kivy.uix.label import Label

class JarvisShellApp(App):
    def build(self):
        return Label(
            text="Jarvis Shell — Build Successful!",
            font_size="24sp",
            halign="center"
        )

if __name__ == "__main__":
    JarvisShellApp().run()