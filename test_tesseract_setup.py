import pytesseract
import os

DEFAULT_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

def setup_tesseract(tesseract_path=None):
    try:
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"Set tesseract_cmd to: {tesseract_path}")
            return True
        for default_path in DEFAULT_TESSERACT_PATHS:
            if os.path.exists(default_path):
                pytesseract.pytesseract.tesseract_cmd = default_path
                print(f"Set tesseract_cmd to: {default_path}")
                return True
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if setup_tesseract():
        print("Setup successful")
        try:
            # Try to get tesseract version to verify it's working
            version = pytesseract.get_tesseract_version()
            print(f"Tesseract version: {version}")
        except Exception as e:
            print(f"Execution Error: {e}")
    else:
        print("Setup failed")
