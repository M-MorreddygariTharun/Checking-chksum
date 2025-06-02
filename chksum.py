import os
import sys
import requests
from bs4 import BeautifulSoup
import py7zr

# Configuration
DOWNLOAD_FOLDER = r"D:\CHKSUM_PYTHON_SCRIPT\Downloaded_files"
EXPECTED_CHKSUM_PATH = 'DeepScreen/GmXmlDeepScreen/chksum'

def ensure_download_folder():
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

def download_file(url, save_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    else:
        print(f"[ERROR] Failed to download {url} (status: {response.status_code})")
        return False

def extract_links(base_url):
    response = requests.get(base_url)
    if response.status_code != 200:
        print(f"[ERROR] Failed to access URL: {base_url}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    links = [a['href'] for a in soup.find_all('a', href=True)]
    return [base_url + link for link in links if link.endswith('.7z')]

def check_chksum_in_7z_files(base_url):
    ensure_download_folder()
    links = extract_links(base_url)

    if not links:
        print("No .7z files found at the URL.")
        return

    files_with_chksum = []
    files_without_chksum = []

    for file_url in links:
        file_name = os.path.basename(file_url)
        local_path = os.path.join(DOWNLOAD_FOLDER, file_name)

        print(f"\n[INFO] Downloading: {file_name}")
        if not download_file(file_url, local_path):
            continue

        try:
            with py7zr.SevenZipFile(local_path, mode='r') as archive:
                file_list = archive.getnames()
                if EXPECTED_CHKSUM_PATH in file_list:
                    print(f"[FOUND] 'chksum' found in {file_name}")
                    files_with_chksum.append(file_name)
                else:
                    print(f"[MISSING] 'chksum' NOT found in {file_name}")
                    files_without_chksum.append(file_name)
        except Exception as e:
            print(f"[ERROR] Could not open {file_name}: {e}")

    # Cleanup: delete all downloaded .7z files
    for f in os.listdir(DOWNLOAD_FOLDER):
        if f.lower().endswith(".7z"):
            try:
                os.remove(os.path.join(DOWNLOAD_FOLDER, f))
            except Exception as e:
                print(f"[ERROR] Could not delete {f}: {e}")

    # Final summary in clean list format
    print("\n--- FINAL SUMMARY ---")

    print("✅ Files WITH 'chksum':")
    if files_with_chksum:
        for f in files_with_chksum:
            print(f)
    else:
        print("None")

    print("\n❌ Files WITHOUT 'chksum':")
    if files_without_chksum:
        for f in files_without_chksum:
            print(f)
    else:
        print("None")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python chksum.py <base_url>")
        sys.exit(1)

    base_url = sys.argv[1].rstrip('/') + '/'
    check_chksum_in_7z_files(base_url)
