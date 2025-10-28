☀️ AI-Enhanced Weather Reporter (PyQt5)
A simple, aesthetically pleasing desktop weather application built with PyQt5 and Python. This app fetches real-time weather conditions and uses the Google Gemini API to generate a friendly, conversational summary of the current conditions.
✨ Features
Real-time Weather: Fetches current temperature, humidity, and wind speed using the OpenWeatherMap API.
Intelligent Summarization: Uses the Gemini 2.5 Flash model to convert raw weather data into a short, insightful, and conversational text description.
Intuitive UI: Built with PyQt5, featuring a fixed-size, clean layout, and expressive weather emojis.
Secure API Handling: Loads sensitive API keys securely via environment variables.
⚙️ Installation and Setup
Prerequisites
Python 3.8+
OpenWeatherMap API Key (Required)
1. Clone the Repository
git clone [https://github.com/YourUsername/ai-weather-reporter.git](https://github.com/YourUsername/ai-weather-reporter.git)
cd ai-weather-reporter


2. Create and Activate Virtual Environment
It is highly recommended to use a virtual environment:
python3 -m venv venv
source venv/bin/activate  # On Linux/macOS
# or
venv\Scripts\activate     # On Windows


3. Install Dependencies
pip install -r requirements.txt


4. Configure API Keys
The application requires an OpenWeatherMap API key.
Rename the provided .env.example file to .env.
Edit the .env file and replace the placeholder with your actual key:
OPENWEATHER_API_KEY="your_openweathermap_api_key_here"
Note: The Gemini API key is often managed automatically in development environments, but if you need to set it explicitly, you would use the GEMINI_API_KEY variable as shown in the example file.
▶️ Running the Application
Once setup is complete, run the main file:
python weather_app.py


🛠️ Technologies Used
Python 3
PyQt5: For the Graphical User Interface (GUI).
Requests: For making HTTP requests to external APIs.
OpenWeatherMap API: Source of real-time weather data.
Google Gemini API (2.5 Flash): For Generative AI text summarization.
