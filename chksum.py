#!/usr/bin/env python3
import os
import sys
import requests
from bs4 import BeautifulSoup
import py7zr
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Make printing flush immediately (safe on modern Python)
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Config read from environment (set these as GitHub Secrets / env)
DOWNLOAD_FOLDER = os.environ.get("DOWNLOAD_FOLDER", os.path.join(os.getcwd(), "downloaded_files"))
DEFAULT_CHKSUM_PATH = os.environ.get("DEFAULT_CHKSUM_PATH", "DeepScreen/GmXmlDeepScreen/chksum")
SPECIAL_CHKSUM_PATH = os.environ.get("SPECIAL_CHKSUM_PATH", "QNX/chksum")

SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = os.environ.get("SMTP_PORT")
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

def require_envs():
    missing = []
    for name in ("SMTP_SERVER", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "RECEIVER_EMAIL"):
        if not os.environ.get(name):
            missing.append(name)
    if missing:
        print(f"[ERROR] Missing required environment variables: {', '.join(missing)}")
        sys.exit(2)

def ensure_download_folder():
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    print(f"[INFO] Using download folder: {DOWNLOAD_FOLDER}")

def cleanup_download_folder():
    if os.path.exists(DOWNLOAD_FOLDER):
        for f in os.listdir(DOWNLOAD_FOLDER):
            if f.lower().endswith(".7z"):
                try:
                    os.remove(os.path.join(DOWNLOAD_FOLDER, f))
                    print(f"[CLEANUP] Deleted old file: {f}")
                except Exception as e:
                    print(f"[ERROR] Could not delete {f}: {e}")

def download_file(url, save_path):
    try:
        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with open(save_path, "wb") as fh:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download {url}: {e}")
        return False

def extract_links(base_url):
    try:
        resp = requests.get(base_url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to access URL {base_url}: {e}")
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".7z"):
            if href.startswith("http://") or href.startswith("https://"):
                links.append(href)
            else:
                # ensure proper join even if link is relative
                links.append(base_url.rstrip("/") + "/" + href.lstrip("/"))
    return links

def send_chksum_email(recipient_email, files_without_chksum):
    subject = "CHECKING CHKSUM"
    files_list_html = "".join(f"<li>{file}</li>" for file in files_without_chksum)
    message = f"""<html><body>
    <p>Hello,</p>
    <p>CHKSUM not Available for the following 7z file(s):</p>
    <ul>{files_list_html}</ul>
    <p>Regards,<br>DevOps</p>
    </body></html>"""
    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USERNAME
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "html"))

    print(f"[EMAIL] Sending email to {recipient_email} about missing chksum files...")
    try:
        server = smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT))
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("[EMAIL] Email sent successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")

def check_chksum_in_7z_files(base_url):
    ensure_download_folder()
    cleanup_download_folder()
    links = extract_links(base_url)
    if not links:
        print("[INFO] No .7z files found at the URL.")
        sys.exit(1)

    files_with_chksum = []
    files_without_chksum = []

    for file_url in links:
        file_name = os.path.basename(file_url)
        local_path = os.path.join(DOWNLOAD_FOLDER, file_name)
        print(f"[INFO] Downloading: {file_url} -> {local_path}")
        if not download_file(file_url, local_path):
            continue

        expected = SPECIAL_CHKSUM_PATH if file_name.endswith("-12_HIGH.7z") else DEFAULT_CHKSUM_PATH

        try:
            with py7zr.SevenZipFile(local_path, mode="r") as archive:
                file_list = archive.getnames()
                if expected in file_list:
                    print(f"[FOUND] '{expected}' found in {file_name}")
                    files_with_chksum.append(file_name)
                else:
                    print(f"[MISSING] '{expected}' NOT found in {file_name}")
                    files_without_chksum.append(file_name)
        except Exception as e:
            print(f"[ERROR] Could not open {file_name}: {e}")

    # cleanup
    for f in os.listdir(DOWNLOAD_FOLDER):
        if f.lower().endswith(".7z"):
            try:
                os.remove(os.path.join(DOWNLOAD_FOLDER, f))
            except Exception as e:
                print(f"[ERROR] Could not delete {f}: {e}")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n--- FINAL SUMMARY ---")
    print(f"[{timestamp}] Files WITH 'chksum':")
    for f in files_with_chksum or ["- None -"]:
        print(f"   - {f}")
    print(f"\n[{timestamp}] Files WITHOUT 'chksum':")
    for f in files_without_chksum or ["- None -"]:
        print(f"   - {f}")

    print(f"\nTotal WITH: {len(files_with_chksum)}; WITHOUT: {len(files_without_chksum)}")

    if files_without_chksum:
        print("\n[FAILURE] One or more .7z files are missing 'chksum'. Sending email notification.")
        send_chksum_email(RECEIVER_EMAIL, files_without_chksum)
        sys.exit(1)
    else:
        print("\n[SUCCESS] All .7z files contain 'chksum'.")
        sys.exit(0)

if __name__ == "__main__":
    require_envs()

    # Accept base_url either from command line or BASE_URL env
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        base_url = sys.argv[1].rstrip("/") + "/"
    else:
        base_url = os.environ.get("BASE_URL")
        if not base_url:
            print("Usage: python chksum.py <base_url>  OR set BASE_URL env var")
            sys.exit(1)
        base_url = base_url.rstrip("/") + "/"

    check_chksum_in_7z_files(base_url)
