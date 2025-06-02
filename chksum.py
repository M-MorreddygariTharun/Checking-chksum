import os
import sys
import requests
from bs4 import BeautifulSoup
import py7zr
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Ensure immediate print flushing (good for Jenkins real-time logs)
sys.stdout.reconfigure(line_buffering=True)

# Configuration
DOWNLOAD_FOLDER = r"D:\CHKSUM_PYTHON_SCRIPT\Downloaded_files"
EXPECTED_CHKSUM_PATH = 'DeepScreen/GmXmlDeepScreen/chksum'

# Email config - fill these with your actual values
smtp_server = 'smtp.office365.com'
smtp_port = 587
smtp_username = 'tharun.morreddygari@rampgroup.com'
smtp_password = 'Mkumar#12345'
receiver_email = 'tharun.morreddygari@rampgroup.com'

def ensure_download_folder():
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

def cleanup_download_folder():
    """Delete all .7z files before starting new downloads."""
    if os.path.exists(DOWNLOAD_FOLDER):
        for f in os.listdir(DOWNLOAD_FOLDER):
            if f.lower().endswith(".7z"):
                try:
                    os.remove(os.path.join(DOWNLOAD_FOLDER, f))
                    print(f"[CLEANUP] Deleted old file: {f}")
                except Exception as e:
                    print(f"[ERROR] Could not delete {f}: {e}")

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

def send_chksum_email(recipient_email, files_without_chksum):
    subject = "CHECKING CHKSUM"
    # Create HTML list of files missing chksum
    files_list_html = "".join(f"<li>{file}</li>" for file in files_without_chksum)

    message = f"""
        <html><body>
        <p>Hello,</p>
        <p>CHKSUM not Available for the following 7z file(s):</p>
        <ul>
            {files_list_html}
        </ul>
        <p>Regards,<br>DevOps</p>
        </body></html>
    """

    msg = MIMEMultipart('alternative')
    msg['From'] = smtp_username
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'html'))

    print(f"[EMAIL] Sending email to {recipient_email} about missing chksum files...")
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        print("[EMAIL] Email sent successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")

def check_chksum_in_7z_files(base_url):
    ensure_download_folder()
    cleanup_download_folder()  # Clean up before downloads start

    links = extract_links(base_url)

    if not links:
        print("No .7z files found at the URL.")
        print("There are no 7z files in given link...")
        sys.exit(1)  # Exit early if no links

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

    # Cleanup downloaded files after processing
    for f in os.listdir(DOWNLOAD_FOLDER):
        if f.lower().endswith(".7z"):
            try:
                os.remove(os.path.join(DOWNLOAD_FOLDER, f))
            except Exception as e:
                print(f"[ERROR] Could not delete {f}: {e}")

    # Final summary with timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n--- FINAL SUMMARY ---")

    print(f"[{timestamp}] Files WITH 'chksum':")
    if files_with_chksum:
        for f in files_with_chksum:
            print(f"[{timestamp}]   - {f}")
    else:
        print(f"[{timestamp}]   - None")

    print(f"\n[{timestamp}] Files WITHOUT 'chksum':")
    if files_without_chksum:
        for f in files_without_chksum:
            print(f"[{timestamp}]   - {f}")
    else:
        print(f"[{timestamp}]   - None")

    # If any file is missing chksum, send email and exit with failure for Jenkins
    if files_without_chksum:
        print("\n[FAILURE] One or more .7z files are missing 'chksum'. Sending email notification.")
        send_chksum_email(receiver_email, files_without_chksum)
        sys.exit(1)  # Fail pipeline
    else:
        print("\n[SUCCESS] All .7z files contain 'chksum'.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python chksum.py <base_url>")
        sys.exit(1)

    base_url = sys.argv[1].rstrip('/') + '/'
    check_chksum_in_7z_files(base_url)
