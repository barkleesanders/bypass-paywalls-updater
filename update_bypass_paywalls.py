import requests
import os

DOWNLOAD_URL = "https://gitflic.ru/project/magnolia1234/bpc_uploads/blob/raw?file=bypass-paywalls-chrome-clean-master.zip"
DOWNLOAD_DIR = os.path.expanduser("~/Downloads")
LAST_CONTENT_LENGTH_FILE = os.path.expanduser("~/.last_content_length_bypass_paywalls")
EXTENSION_FILENAME = "bypass-paywalls-chrome-clean-master.zip"

def check_for_updates():
    print("Checking for updates to Bypass Paywalls Chrome Clean...")
    try:
        # Get current content-length from headers
        response = requests.head(DOWNLOAD_URL, allow_redirects=True, timeout=10)
        response.raise_for_status()
        current_content_length = int(response.headers.get('Content-Length', 0))

        if current_content_length == 0:
            print("Warning: Could not get Content-Length from headers. Skipping update check.")
            return

        # Read last known content-length
        last_content_length = 0
        if os.path.exists(LAST_CONTENT_LENGTH_FILE):
            with open(LAST_CONTENT_LENGTH_FILE, 'r') as f:
                try:
                    last_content_length = int(f.read().strip())
                except ValueError:
                    pass # File might be empty or corrupted, treat as 0

        if current_content_length > last_content_length:
            print(f"New version detected! Downloading {EXTENSION_FILENAME}...")
            download_path = os.path.join(DOWNLOAD_DIR, EXTENSION_FILENAME)
            
            # Download the new file
            download_response = requests.get(DOWNLOAD_URL, allow_redirects=True, stream=True, timeout=60)
            download_response.raise_for_status()
            
            with open(download_path, 'wb') as f:
                for chunk in download_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Downloaded to: {download_path}")
            print("Please manually install the updated .crx file into Chrome via chrome://extensions (drag and drop).")
            
            # Update last known content-length
            with open(LAST_CONTENT_LENGTH_FILE, 'w') as f:
                f.write(str(current_content_length))
            print("Update check complete. Content-Length updated.")
        else:
            print("No new version found.")

    except requests.exceptions.RequestException as e:
        print(f"Error during update check: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    check_for_updates()
