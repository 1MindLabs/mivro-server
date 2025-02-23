# Mivro Python Server

This is the backend server for the Mivro project, built with Flask framework. It serves as the core of the Mivro ecosystem, handling several critical functions, including user authentication, data processing, and API integrations.

**Maintained By**: [Areeb Ahmed](https://github.com/areebahmeddd)

## Repository Structure

### Instructions (`instructions/`)

Contains templates used by the Gemini AI model for various functionalities:

- **`lumi_instructions.md`**: Template for analyzing nutrients and categorizing them into positive and negative.
- **`savora_instructions.md`**: Template for the recipe chatbot, guiding the AI in generating personalized recipe recommendations.
- **`swapr_instructions.md`**: Template for providing healthier product alternatives based on user preferences.

### Metadata (`metadata/`)

Contains essential JSON files used for data processing and mapping:

- **`additives_names.json`**: Maps additive codes (e.g., "E100") to their corresponding names (e.g., "Curcumin"). This is used during data processing to convert numeric codes into readable names.
- **`food_categories.json`**: Maps food categories (e.g., "Milk") to broader categories (e.g., "Milk Products", "Milk Solids") to associate appropriate icons with nutrients.
- **`nutrient_limits.json`**: Defines the lower and upper limits for various nutrients (e.g., "calcium": { "unit": "mg", "lower_limit": 1000, "upper_limit": 1300 }). Although deprecated, it was originally used for sorting nutrients into positive and negative categories based on their range.
- **`product_schema.json`**: Specifies the required fields from the OpenFoodFacts API, defining the structure for product data.

### Python Server (`server/`)

Contains the main application code, including routes, configurations, and utility functions:

- **`app.py`**: Defines the main application blueprint and routes.
- **`auth.py`**: Manages Firebase-based user authentication, including registration and login.
- **`chat.py`**: Handles routes for user chat functionalities, such as loading and updating messages.
- **`config.py`**: Contains environment variables and server configuration settings.
- **`database.py`**: Provides methods for interacting with the Firebase database, including data storage and retrieval.
- **`gemini.py`**: Interfaces with the Gemini AI model for nutrient analysis and product recommendations.
- **`mapping.py`**: Manages mappings for additives, NOVA groups, NutriScore grades, and food icons.
- **`middleware.py`**: Implements global request authentication and error handling.
- **`models.py`**: Defines the database schema and model structures.
- **`search.py`**: Connects to the OpenFoodFacts API to process and map product data.
- **`user.py`**: Manages user profile routes, including profile updates and history management.
- **`utils.py`**: Contains utility functions for data processing and structuring API responses.

## Getting Started

Follow these steps to set up and run the Mivro Python Server on your local machine, or you can watch the [demo video](https://youtube.com/watch?v=ToXUq-NSkUg).

### Prerequisites

- [Python >= 3.11.9](https://python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe).
- **Firebase account**: Obtain Firebase credentials by creating a Firebase project [here](https://console.firebase.google.com).
- **Gemini API key**: Obtain your Gemini API key by signing up for access [here](https://aistudio.google.com/app/apikey).

### Installation

#### Option 1: Docker Setup

1. **Pull the Docker Image**:

   ```bash
   docker pull areebahmeddd/mivro-python:latest
   ```

2. **Run the Docker Container**:

   ```bash
   docker run -p 5000:5000 -e GEMINI_KEY=your_gemini_key areebahmeddd/mivro-python:latest
   ```

   - Replace `your_gemini_key` with your actual API key.

#### Option 2: Local Setup

1. **Fork the Repository**:

   - Go to the [Mivro Python Server repository](https://github.com/1MindLabs/mivro-python) and click "Fork" to create a copy under your GitHub account.

2. **Clone the Repository**:

   ```bash
   git clone https://github.com/<your-username>/mivro-python.git
   ```

3. **Create a Virtual Environment (Optional but Recommended)**:

   ```bash
   python -m venv .venv
   ```

4. **Activate the Virtual Environment**:

   - **Windows**:
     ```bash
     .venv\Scripts\activate
     ```
   - **macOS and Linux**:
     ```bash
     source .venv/bin/activate
     ```

5. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

6. **Set Up Environment Variables**:

   - Create a `.env` file in the project root directory with the following template:

     ```ini
     FLASK_SECRET_KEY=your_secret_key
     GEMINI_KEY=your_GEMINI_KEY
     ```

   - Create a `firebase-config.json` file in the project root directory with the following template:
     ```json
     {
       "type": "service_account",
       "project_id": "your_project_id",
       "private_key_id": "your_private_key_id",
       "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
       "client_email": "your_client_email",
       "client_id": "your_client_id",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       "auth_provider_x509_cert_url": "https://googleapis.com/oauth2/v1/certs",
       "client_x509_cert_url": "https://googleapis.com/robot/v1/metadata/x509/your_client_email",
       "universe_domain": "googleapis.com"
     }
     ```

7. **Run the Python Application**:
   ```bash
   python server/app.py
   ```

## Usage

To interact with the Mivro Python Server, you can use API calls via Postman or any HTTP client. Below is an example of how to search for a product using its barcode.

**NOTE**: Replace `Mivro-Email`, `Mivro-Password`, and `product_barcode` with actual values depending on the route you are testing.

### Example API Call

- **Endpoint**: `/api/v1/search/barcode`
- **Method**: `POST`
- **Headers**:
  - `Mivro-Email: your_email@example.com`
  - `Mivro-Password: your_password`
- **Body (JSON)**:
  ```json
  {
    "product_barcode": "8901719104046"
  }
  ```

### Example Response

To see an example of the response you can expect, refer to the [response-example.json](https://github.com/1MindLabs/mivro-docs/blob/main/response-example.json) file.

## Documentation

For detailed documentation, please visit the [Documentation Repository](https://github.com/1MindLabs/mivro-docs).

## Contributing

We welcome contributions! Please follow the guidelines in our [Contributing Guide](https://github.com/1MindLabs/mivro-docs/blob/main/CONTRIBUTING.md) to get started.

## License

This project is licensed under the [MIT License](https://github.com/1MindLabs/mivro-docs/blob/main/LICENSE).

## Acknowledgments

- [Open Food Facts](https://world.openfoodfacts.org) for providing access to a comprehensive food product database.
- [All Contributors](https://github.com/1MindLabs/mivro-python/graphs/contributors) for their valuable contributions to the development and improvement of this project.
