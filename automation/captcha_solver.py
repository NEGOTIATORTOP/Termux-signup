from PIL import Image
import pytesseract
import requests
import openai
import os
import logging

# Set your OpenAI API key here or via environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
logger = logging.getLogger(__name__)

def solve_captcha_ocr(image_path):
    try:
        img = Image.open(image_path)
        code = pytesseract.image_to_string(img, config="--psm 8")
        return ''.join(filter(str.isalnum, code)).strip()
    except Exception as e:
        logger.error(f"OCR captcha error: {e}")
        return ""

def solve_captcha_ai(image_path):
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        response = openai.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": "What is the text in this captcha image? Only return the code."},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + image_data.hex()}}
                ]}
            ],
            max_tokens=10,
        )
        code = response.choices[0].message.content.strip()
        return ''.join(filter(str.isalnum, code))
    except Exception as e:
        logger.error(f"AI captcha error: {e}")
        return ""

def solve_captcha_beast(image_path):
    # Try OCR first, then fall back to AI
    code = solve_captcha_ocr(image_path)
    if code and len(code) >= 4:
        return code
    code = solve_captcha_ai(image_path)
    if code and len(code) >= 4:
        return code
    return ""
