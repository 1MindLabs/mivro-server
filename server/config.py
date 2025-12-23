import os

from dotenv import load_dotenv

# Load the environment variables
load_dotenv()

# Access the environment variables
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Set the default name and photo for a user
DEFAULT_NAME = "Mivro User"
DEFAULT_PHOTO = "https://images.pexels.com/photos/756856/pexels-photo-756856.jpeg"

# Set the default timeout values for API requests
API_TIMEOUT = 60
GEMINI_TIMEOUT = 60
