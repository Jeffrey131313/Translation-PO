import sys
import os
import requests
import re

issue_number = sys.argv[1]
repo = os.environ["GITHUB_REPOSITORY"]
token = os.environ["GITHUB_TOKEN"]
api_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"

res = requests.get(api_url, headers={"Authorization": f"token {token}"})
issue = res.json()
body = issue.get("body", "")

urls = re.findall(r'\!\[.*?\]\((https://user-images\.githubusercontent\.com/.*?)\)', body)

for i, url in enumerate(urls):
    filename = url.split("/")[-1].split("?")[0]
    filepath = os.path.join("uploaded", filename)
    print(f"Downloading: {url} -> {filepath}")
    r = requests.get(url)
    with open(filepath, "wb") as f:
        f.write(r.content)
