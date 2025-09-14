import requests
import json
import base64
from pathlib import Path

# Replace with your actual Modal endpoint URL
MODAL_ENDPOINT_URL = (
    "https://antlaf6--minimalist-anthropic-agent-analyze-context--81a139-dev.modal.run"
)


def encode_image_to_base64(image_path: str) -> dict:
    """
    Encode an image file to base64 for sending to the endpoint.

    Args:
        image_path (str): Path to the image file

    Returns:
        dict: Contains 'data' (base64 string) and 'media_type'
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Determine media type based on file extension
    extension = path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
    }

    media_type = media_type_map.get(extension, "image/jpeg")

    # Read and encode the image
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

    return {"data": encoded_string, "media_type": media_type}


def send_image_analysis_request(context: str, image_path: str):
    """
    Send a request with both context and an image to analyze.

    Args:
        context (str): Text context describing what to analyze
        image_path (str): Path to the image file

    Returns:
        dict: Response from the endpoint
    """
    try:
        # Encode the image
        image_data = encode_image_to_base64(image_path)

        # Prepare the payload
        payload = {
            "context": {
                "request": context,
                "timestamp": "2024-01-01T00:00:00Z",
                "image_included": True,
            },
            "image_data": image_data,
        }

        # Send the request
        response = requests.post(
            MODAL_ENDPOINT_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        response.raise_for_status()
        return response.json()

    except Exception as e:
        print(f"Request failed: {e}")
        return {"status": "error", "error": str(e)}


def main():
    print("Testing Image Analysis with Modal Endpoint")
    print("=" * 50)

    # Example usage
    image_path = "example_image.jpg"  # Replace with your image path
    context = """
    This is an image from a dementia patient's home. Please analyze:
    1. Is the environment safe?
    2. Are there any hazards visible?
    3. Does anything require immediate attention?
    4. Are there any people in the image who should be identified?
    """

    print(f"Analyzing image: {image_path}")
    print(f"Context: {context}")
    print("-" * 50)

    # Check if image exists before trying to analyze
    if Path(image_path).exists():
        result = send_image_analysis_request(context, image_path)
        print("Response:")
        print(json.dumps(result, indent=2))
    else:
        print(f"Image file '{image_path}' not found.")
        print("Please update the 'image_path' variable with a valid image file path.")
        print("\nExample of how the request would look:")
        example_payload = {
            "context": {
                "request": context,
                "timestamp": "2024-01-01T00:00:00Z",
                "image_included": True,
            },
            "image_data": {
                "data": "base64_encoded_image_data_here...",
                "media_type": "image/jpeg",
            },
        }
        print(json.dumps(example_payload, indent=2))


if __name__ == "__main__":
    main()
