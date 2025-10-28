import sys
import os  # For environment variables
import requests
import json
import time  # For exponential backoff
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject, pyqtSlot


# --- 1. Worker Signals (Handles communication from Worker to Main Thread) ---
class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    result = pyqtSignal(dict)  # Signal to deliver the final weather data dictionary
    error = pyqtSignal(str)  # Signal to deliver an error message string
    finished = pyqtSignal()  # Signal to indicate the thread is complete


# --- 2. Worker Runnable (Performs API Calls Off-Thread) ---
class WeatherWorker(QRunnable):
    """
    Runnable that performs network operations (Weather and Gemini API calls)
    in a separate thread to prevent the GUI from freezing.
    """

    def __init__(self, city_name):
        super().__init__()
        self.city_name = city_name
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """Main thread logic for the worker."""
        openweather_api_key = os.getenv("OPENWEATHER_API_KEY")

        if not openweather_api_key:
            self.signals.error.emit("ERROR: OPENWEATHER_API_KEY not set.")
            return

        # --- STEP 1: Get Weather Data ---
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={self.city_name}&appid={openweather_api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            weather_data = response.json()

            if weather_data.get('cod') != 200:
                self.signals.error.emit("City not found or invalid response from weather API.")
                return

            # --- STEP 2: Generate AI Description (also off-thread) ---
            ai_description = self._generate_ai_description(weather_data)
            weather_data['ai_description'] = ai_description

            # Emit success signal with complete data
            self.signals.result.emit(weather_data)

        except requests.exceptions.HTTPError as Http_Error:
            status_code = response.status_code if 'response' in locals() else None
            error_message = ""
            match status_code:
                case 400:
                    error_message = "Bad Request: Check city spelling."
                case 401:
                    error_message = "Unauthorized: Invalid OpenWeatherMap Key."
                case 404:
                    error_message = "Not Found: City not found."
                case _:
                    error_message = f"HTTP Error {status_code}: Please try again."
            self.signals.error.emit(error_message)

        except requests.exceptions.RequestException as e:
            self.signals.error.emit(f"Connection Error: Check your internet or API access. ({e})")

        except Exception as e:
            self.signals.error.emit(f"An unexpected error occurred during weather fetch: {e}")

        finally:
            self.signals.finished.emit()  # Always signal completion

    def _generate_ai_description(self, data):
        """Generates a conversational weather summary using the Gemini API."""

        city_name = data.get('name', 'Unknown Location')
        current_temp_c = data["main"]["temp"] - 273.15
        feels_like_c = data["main"]["feels_like"] - 273.15
        humidity = data["main"]["humidity"]
        wind_speed_ms = data["wind"]["speed"]
        main_weather = data["weather"][0]["main"]
        raw_description = data["weather"][0]["description"]

        system_instruction = (
            "You are a friendly, conversational weather reporter and AI assistant. "
            "Your response must be a single, short paragraph (under 30 words) "
            "that summarizes the current weather and provides a brief insight into how it feels."
            "Do not use markdown formatting like bullet points or bold text."
        )

        user_prompt = (
            f"Write a summary for the weather in {city_name}. "
            f"The current temperature is {current_temp_c:.1f}°C, "
            f"but it feels like {feels_like_c:.1f}°C. "
            f"Humidity is {humidity}% and wind speed is {wind_speed_ms} m/s."
            f"The main condition is '{main_weather}' with a detailed description of '{raw_description}'."
        )

        apiKey = os.getenv("GEMINI_API_KEY") or ""
        model = "gemini-2.5-flash-preview-09-2025"
        apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={apiKey}"

        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]}
        }

        max_retries = 3
        wait_time = 1

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    apiUrl,
                    headers={'Content-Type': 'application/json'},
                    data=json.dumps(payload),
                    timeout=15
                )
                response.raise_for_status()

                result = response.json()
                text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text',
                                                                                                      'AI response unavailable.')

                return text

            except requests.exceptions.RequestException:
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    wait_time *= 2  # Exponential backoff
                else:
                    return "AI reporter failed to connect after multiple attempts."
            except Exception:
                return "AI reporter analyzing data..."

        return "AI reporter is offline."


# --- 3. Main Application Class ---
class WeatherApp(QWidget):
    """
    A PyQt5 GUI application that fetches real-time weather data
    and generates a conversational summary using the Gemini AI API.
    """

    def __init__(self):
        super().__init__()

        # Initialize the Thread Pool
        self.threadpool = QThreadPool()

        self.city_label = QLabel("Enter City Name", self)
        self.city_input = QLineEdit(self)
        self.get_weather_button = QPushButton("Get Weather", self)
        self.temperature_label = QLabel(self)
        self.emoji_label = QLabel(self)
        self.description_label = QLabel(self)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("AI Weather Reporter")

        self.setFixedSize(500, 620)

        weather_hbox = QHBoxLayout()
        weather_hbox.addWidget(self.temperature_label)
        weather_hbox.addWidget(self.emoji_label)

        vbox = QVBoxLayout()
        vbox.addWidget(self.city_label)
        vbox.addWidget(self.city_input)
        vbox.addWidget(self.get_weather_button)
        vbox.addLayout(weather_hbox)
        vbox.addWidget(self.description_label)

        self.setLayout(vbox)

        self.city_label.setAlignment(Qt.AlignCenter)
        self.city_input.setAlignment(Qt.AlignCenter)
        self.temperature_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.emoji_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.description_label.setAlignment(Qt.AlignCenter)

        self.description_label.setWordWrap(True)

        self.city_label.setObjectName("city_label")
        self.city_input.setObjectName("city_input")
        self.get_weather_button.setObjectName("get_weather_button")
        self.temperature_label.setObjectName("temperature_label")
        self.emoji_label.setObjectName("emoji_label")
        self.description_label.setObjectName("description_label")

        self.setStyleSheet("""
        QWidget { background-color: #f0f4f8; }
        QLabel, QPushButton, QLineEdit { font-family: 'Calibri', 'Arial', sans-serif; color: #333; padding: 5px; }
        QLabel#city_label{ font-size: 40px; font-style: italic; color: #1a73e8; }
        QLineEdit#city_input{ font-size: 40px; border: 2px solid #ccc; border-radius: 10px; padding: 10px; }
        QPushButton#get_weather_button{
            font-size: 30px; font-weight: bold; background-color: #4285f4; color: white;
            border-radius: 10px; padding: 15px;
        }
        QPushButton#get_weather_button:hover { background-color: #3b78e7; }
        QLabel#temperature_label{
            font-size: 75px; font-weight: 600; color: #e53935; margin-top: 10px;
        }
        QLabel#emoji_label{
            font-size: 85px;
            font-family: 'Segoe UI Emoji', 'Apple Color Emoji', 'Segoe UI Symbol';
        }
        QLabel#description_label{
            font-size: 32px; font-weight: 600; font-style: normal;
            color: #3f51b5; padding: 20px;
        }
        """)
        self.get_weather_button.clicked.connect(self.start_worker)

    def start_worker(self):
        """Starts the asynchronous weather fetch worker."""
        city = self.city_input.text()
        if not city:
            self.dispaly_error("Please enter a city name.")
            return

        # Disable the button and show loading text while the worker runs
        self.get_weather_button.setEnabled(False)
        self.description_label.setText("Fetching weather and generating AI summary...")
        self.temperature_label.clear()
        self.emoji_label.clear()

        # Create the worker and connect its signals to the main thread slots
        worker = WeatherWorker(city)
        worker.signals.result.connect(self.display_weather)
        worker.signals.error.connect(self.display_error)
        worker.signals.finished.connect(self.worker_finished)

        # Execute the worker in the thread pool
        self.threadpool.start(worker)

    @pyqtSlot(str)
    def display_error(self, message):
        """Slot to handle error signals from the worker."""
        self.temperature_label.setStyleSheet("font-size:30px;")
        self.temperature_label.setText(message)
        self.emoji_label.clear()
        self.description_label.clear()

    @pyqtSlot()
    def worker_finished(self):
        """Slot to re-enable the button when the worker completes."""
        self.get_weather_button.setEnabled(True)

    @pyqtSlot(dict)
    def display_weather(self, data):
        """Slot to handle successful weather data signals from the worker."""

        # --- 1. Get Temperature and Emoji ---
        temperature_in_K = data["main"]["temp"]
        temperature_in_C = temperature_in_K - 273.15

        self.temperature_label.setStyleSheet("font-size:75px;")
        self.temperature_label.setText(f"{temperature_in_C:.0f}°")

        weather_id = data["weather"][0]["id"]
        self.emoji_label.setText(self.get_wether_emoji(weather_id))

        # --- 2. Set AI Description ---
        ai_description = data.get('ai_description', 'AI analysis failed.')
        self.description_label.setText(ai_description)

    # --- Static Method for Emoji Mapping ---
    @staticmethod
    def get_wether_emoji(weather_id):
        if 200 <= weather_id <= 232:
            return "⛈️"
        elif 300 <= weather_id <= 321:
            return "🌦️"
        elif weather_id == 511:
            return "🧊🌧️"
        elif (500 <= weather_id <= 504) or (520 <= weather_id <= 531):
            return "🌧️"
        elif 600 <= weather_id <= 622:
            return "🌨️"
        elif weather_id in [701, 721, 741, 761]:
            return "🌫️"
        elif weather_id == 711:
            return "💨"
        elif weather_id == 731:
            return "🌫️"
        elif weather_id == 751:
            return "🏜️"
        elif weather_id == 762:
            return "🌋"
        elif weather_id == 771:
            return "💨"
        elif weather_id == 781:
            return "🌪️"
        elif weather_id == 800:
            return "🌞"
        elif weather_id == 801:
            return "🌤️"
        elif weather_id == 802:
            return "⛅"
        elif weather_id == 803:
            return "🌥️"
        elif weather_id == 804:
            return "☁️"
        else:
            return "❓"


if __name__ == "__main__":
    # Load environment variables from a local .env file
    # Requires 'pip install python-dotenv'
    from dotenv import load_dotenv

    load_dotenv()

    app = QApplication(sys.argv)
    weather_app = WeatherApp()
    weather_app.show()
    sys.exit(app.exec_())
