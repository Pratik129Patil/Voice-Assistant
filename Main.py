import sys
import threading as th
import speech_recognition as sr
import pyttsx3
import pywhatkit as wh
import subprocess as sub
import os
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QGridLayout, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QEvent, QTimer

# Initialize the recognizer and the text-to-speech engine
r = sr.Recognizer()
engine = pyttsx3.init()

# Set voice and rate for text-to-speech
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)
engine.setProperty('rate', 180)  # Slightly increased rate

# Global variables
MyText = ""
res = False
lock = th.Lock()  # To ensure thread-safe operations
conversation_mode = False  # Flag to track conversation mode


# Load responses from JSON file
def load_responses():
  try:
    with open('responses.json', 'r') as file:
      return json.load(file)
  except FileNotFoundError:
    return {}


# Save responses to JSON file
def save_responses(responses):
  with open('responses.json', 'w') as file:
    json.dump(responses, file, indent=4)


# Get response from JSON data
def get_response(responses, input_text):
  return responses.get(input_text.lower())


# Add response to JSON data
def add_response(responses, question, answer):
  responses[question.lower()] = answer
  save_responses(responses)


# Function to speak out a given command
def talk(command):
  with lock:
    engine.say(command)
    engine.runAndWait()


# Function to process voice commands and respond accordingly
def process_command():
  global MyText, res, conversation_mode
  responses = load_responses()
  try:
    # Update status label to "Thinking..."
    status_label.setText("Thinking...")
    
    if "play" in MyText:
      pycmd = MyText.replace("play", "").strip()
      th.Thread(target=wh.playonyt, args=(pycmd,)).start()
      talk("Playing " + pycmd + " on YouTube")
      res = True
    
    elif "open" in MyText:
      opapp = MyText.replace("open", "").strip()
      th.Thread(target=sub.Popen, args=(["start", opapp],), kwargs={'shell': True}).start()
      talk("Opening " + opapp)
      res = True
    
    elif "close" in MyText:
      clapp0 = MyText.replace("close", "").strip()
      clapp = "".join([clapp0, ".exe"])
      th.Thread(target=sub.Popen, args=(["taskkill", "/im", clapp, "/f"],), kwargs={'shell': True}).start()
      talk("Closing " + clapp0)
      res = True
    
    elif "shutdown" in MyText:
      talk("Shutting down the PC")
      th.Thread(target=os.system, args=("shutdown /s /t 1",)).start()
    
    elif "sleep" in MyText:
      talk("Putting the PC to sleep")
      th.Thread(target=os.system, args=("rundll32.exe powrprof.dll,SetSuspendState 0,1,0",)).start()
    
    elif "on bluetooth" in MyText:
      talk("Turning on Bluetooth")
      th.Thread(target=os.system, args=("powershell -command \"& {Set-BluetoothRadio -State On}\"",)).start()
      res = True
    
    elif "on wifi" in MyText:
      talk("Turning on Wi-Fi")
      th.Thread(target=os.system, args=("netsh interface set interface Wi-Fi enabled",)).start()
    
    elif "talk" in MyText:
      talk("Starting conversation mode.")
      conversation_mode = True
    
    elif "silent" in MyText:
      talk("Exiting conversation mode.")
      conversation_mode = False
    
    elif "search" in MyText:
      search_query = MyText.replace("search", "").strip()
      talk(f"Searching for {search_query}")
      th.Thread(target=wh.search, args=(search_query,)).start()
      res = True
    
    else:
      # Check if the command is in the existing responses
      answer = get_response(responses, MyText)
      if answer:
        talk(answer)
      else:
        # If the command is not recognized, ask the user for the correct response
        talk("I don't know the answer to that. Can you teach me?")
        with sr.Microphone() as source:
          audio = r.listen(source, timeout=3)
          try:
            user_response = r.recognize_google(audio).lower()
            talk("Got it. I'll remember that.")
            add_response(responses, MyText, user_response)
          except sr.UnknownValueError:
            talk("Sorry, I did not catch that. Could you please repeat?")
          except sr.RequestError as e:
            talk("Could not request results; {0}".format(e))
  except Exception as e:
    talk("An error occurred: {0}".format(e))
    res = False


# Function to continuously listen for voice commands
def cmd():
  global MyText, res, conversation_mode
  try:
    while True:
      with sr.Microphone() as source2:
        if not conversation_mode:
          # Adjust for ambient noise and listen for wake word
          r.adjust_for_ambient_noise(source2, duration=0.1)
          status_label.setText("Listening for wake word...")
          audio2 = r.listen(source2, timeout=None)  # Listen indefinitely for wake word
          try:
            wake_word = r.recognize_google(audio2)
            wake_word = wake_word.lower()
            if "alexa" in wake_word:
              status_label.setText("Wake word detected. Listening for command...")
              talk("Yes?")
              audio2 = r.listen(source2, timeout=3)  # Listen for command after wake word
              MyText = r.recognize_google(audio2)
              MyText = MyText.lower()
              command_label.setText("Cmd: " + MyText)  # Update the command label
              th.Thread(target=process_command).start()
            else:
              status_label.setText("Wake word not detected.")
          except sr.UnknownValueError:
            status_label.setText("Sorry, I did not catch that. Could you please repeat?")
          except sr.RequestError as e:
            status_label.setText("Could not request results; {0}".format(e))
        else:
          # In conversation mode, listen for commands continuously
          status_label.setText("In conversation mode. Listening for command...")
          r.adjust_for_ambient_noise(source2, duration=0.1)
          audio2 = r.listen(source2, timeout=None)
          try:
            MyText = r.recognize_google(audio2)
            MyText = MyText.lower()
            command_label.setText("Command: " + MyText)  # Update the command label
            th.Thread(target=process_command).start()
          except sr.UnknownValueError:
            status_label.setText("Sorry, I did not catch that. Could you please repeat?")
          except sr.RequestError as e:
            status_label.setText("Could not request results; {0}".format(e))
  except Exception as e:
    talk("An error occurred in cmd: {0}".format(e))
    res = False


# Function to start the voice assistant
def start_assistant():
  assistant_thread = th.Thread(target=cmd)
  assistant_thread.daemon = True
  assistant_thread.start()
  status_label.setText("Assistant started.")


class VoiceAssistantGUI(QMainWindow):
  def __init__(self):
    super().__init__()
    
    # Window settings
    self.setWindowTitle("Voice Assistant")
    self.setGeometry(0, 0, 1920, 1080)
    self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)  # Remove window decorations
    self.setAttribute(Qt.WA_TranslucentBackground)  # Set transparent background
    
    # Central widget
    self.central_widget = QWidget()
    self.setCentralWidget(self.central_widget)
    
    # Layout
    self.layout = QGridLayout(self.central_widget)
    self.layout.setContentsMargins(0, 0, 0, 0)  # Remove margins around the layout
    
    # Text label to show commands
    global command_label
    command_label = QLabel("Cmd: ")
    command_label.setStyleSheet(self.get_label_style())
    self.layout.addWidget(command_label, 1, 1, 1, 3, alignment=Qt.AlignCenter | Qt.AlignTop)
    
    # Status label
    global status_label
    status_label = QLabel("Press 'Start' to begin.")
    status_label.setStyleSheet(self.get_label_style())
    self.layout.addWidget(status_label, 2, 1, 1, 3, alignment=Qt.AlignCenter | Qt.AlignBottom)
    
    # Button sizes
    button_sizew = 50
    button_sizeh = 50
    
    # Start button
    start_button = QPushButton("S")
    start_button.setFixedSize(button_sizew, button_sizeh)
    start_button.setStyleSheet(self.get_button_style())
    start_button.clicked.connect(start_assistant)
    start_button.installEventFilter(self)
    
    # Exit button
    exit_button = QPushButton("X")
    exit_button.setFixedSize(button_sizew, button_sizeh)
    exit_button.setStyleSheet(self.get_button_style())
    exit_button.clicked.connect(self.exit_program)
    exit_button.installEventFilter(self)
    
    # Create a vertical layout to hold the buttons together
    button_layout = QVBoxLayout()
    button_layout.addWidget(start_button)
    button_layout.addWidget(exit_button)
    
    # Add the button layout to the right edge of the grid layout
    self.layout.addLayout(button_layout, 1, 3, 2, 1, alignment=Qt.AlignCenter | Qt.AlignTrailing | Qt.AlignBottom)
    
    # Maximize the window
    self.showMaximized()
  
  def get_label_style(self):
    return """
            QLabel {
                color: #bf00ff;
                background-color: black;
                border: 2px solid #bf00ff;
                border-radius: 20px;
                font-size: 16px;
                margin-bottom: 20px;
                padding: 10px 20px;
                transition: all 0.3s ease;
            }
        """
  
  def get_button_style(self):
    return """
                  QPushButton {
                      background-color: black;
                      color: #bf00ff;
                      border: 2px solid #bf00ff;
                      border-radius: 20px;
                      font-size: 20px;
                  }
                  
                  """
  
  def eventFilter(self, obj, event):
    if event.type() == QEvent.Enter:
      obj.setStyleSheet("""
                          QPushButton {
                              background-color: #bf00ff;
                              color: black;
                              border: 8px solid transparent;
                              border-radius: 25px;
                              font-size: 14px;
                              padding: 10px 20px;
                          }
                          """)
    elif event.type() == QEvent.Leave:
      obj.setStyleSheet(self.get_button_style())
    return super().eventFilter(obj, event)
  
  def exit_program(self):
    sys.exit()


if __name__ == "__main__":
  app = QApplication(sys.argv)
  voice_assistant_gui = VoiceAssistantGUI()
  sys.exit(app.exec_())
