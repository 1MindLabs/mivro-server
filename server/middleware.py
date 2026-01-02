from flask import Response, jsonify, request
from database import runtime_error, validate_user_profile


def auth_handler() -> Response:
    if request.method == "OPTIONS":
        return None  # Skip authentication for OPTIONS requests

    # List of routes that do not require authentication
    unrestricted_routes = [
        "/health",
        "/metrics",
        "/api/v1/auth/signup",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/signin",
        "/api/v1/auth/reset-password",
    ]

    if request.path in unrestricted_routes:
        return None  # Skip authentication for unrestricted routes

    # Get email and password values from the request headers
    email = request.headers.get("Mivro-Email")
    password = request.headers.get("Mivro-Password")
    firebase_token = request.headers.get("Authorization")

    # Allow Firebase token authentication (website) or email+password (extension)
    if firebase_token and firebase_token.startswith("Bearer "):
        # Firebase authentication - only email is required
        if not email:
            return jsonify({"error": "Email is required."}), 401
        # Skip password validation for Firebase tokens
        return None

    # Traditional email+password authentication (extension)
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 401

    try:
        # Validate the user profile using the email and password
        result = validate_user_profile(email, password)
        if "error" in result:
            # Set the status code based on the error message
            status_code = 401 if "Incorrect password." in result["error"] else 404
            return jsonify(result), status_code
    except Exception as exc:
        runtime_error("auth_handler", str(exc), email=email)
        return jsonify({"error": str(exc)}), 500


def error_handler(exception) -> Response:
    return jsonify({"message": "Error with request path. Check and try again."}), 500
