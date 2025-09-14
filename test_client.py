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


def send_context_request(context, mcp_servers=None, image_path=None):
    """
    Send a POST request to the analyze_context_endpoint.

    Args:
        context (str): The context to analyze
        mcp_servers (list, optional): List of MCP servers to initialize
        image_path (str, optional): Path to an image file to include

    Returns:
        dict: Response from the endpoint
    """
    payload = {"context": context}

    if mcp_servers:
        payload["mcp_servers"] = mcp_servers

    if image_path:
        try:
            payload["image_data"] = encode_image_to_base64(image_path)
        except Exception as e:
            print(f"Failed to encode image: {e}")
            return {"status": "error", "error": f"Image encoding failed: {str(e)}"}

    try:
        response = requests.post(
            MODAL_ENDPOINT_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return {"status": "error", "error": str(e)}


def main():

    # Example 4: Context with image
    print("=== Example 4: Context with Image ===")
    context4 = "{prompt: 'Analyze this image and tell me what you see. Is there anything concerning about the person's environment or safety?', user_conversation: 'I shoudnt forget to set a timer for 5 mins from now.'"
    result4 = send_context_request(
        context4,
        image_path="./test_image.jpg",
        ,
    )
    print(f"Response: {json.dumps(result4, indent=2)}\n")


if __name__ == "__main__":
    print("Testing Modal Endpoint Client")
    print("=" * 50)

    # Update this with your actual Modal endpoint URL
    print(f"Endpoint URL: {MODAL_ENDPOINT_URL}")
    print("Note: Update MODAL_ENDPOINT_URL with your actual Modal app URL")
    print("=" * 50)

    main()
