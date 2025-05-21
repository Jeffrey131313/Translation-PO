import os
import re
import requests
import sys

def extract_urls(text):
    pattern = r'https://github\.com/user-attachments/files/[^\s]+'
    return re.findall(pattern, text)

def download_files(urls, download_dir):
    os.makedirs(download_dir, exist_ok=True)
    for i, url in enumerate(urls):
        filename = os.path.join(download_dir, f"file_{i}.txt")
        print(f"Downloading {url} to {filename}")
        r = requests.get(url)
        if r.status_code == 200:
            with open(filename, "wb") as f:
                f.write(r.content)
        else:
            print(f"Failed to download {url}")

if __name__ == "__main__":
    issue_body = os.environ.get("ISSUE_BODY")
    issue_number = os.environ.get("ISSUE_NUMBER")

    if not issue_body or not issue_number:
        print("Missing issue body or number.")
        sys.exit(1)

    urls = extract_urls(issue_body)
    if not urls:
        print("No file links found in issue body.")
        sys.exit(1)

    download_files(urls, "downloaded_files")
    print(f"Downloaded {len(urls)} files.")
