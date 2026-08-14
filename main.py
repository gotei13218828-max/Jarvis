from kivy.app import App
from kivy.uix.button import Button

class JarvisApp(App):
    def build(self):
        return Button(text="Jarvis")

JarvisApp().run()
