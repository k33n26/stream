import re
import requests
import sys
import json
import os
from urllib.parse import urljoin
from slugify import slugify
from tqdm import tqdm

DEFAULT_TIMEOUT = 10  # Saniye cinsinden zaman aşımı süresi

def get_stream_url(url, pattern, method="GET", headers={}, body={}):
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        elif method == "POST":
            r = requests.post(url, json=body, headers=headers, timeout=DEFAULT_TIMEOUT)
        else:
            print(f"{method} is not supported or wrong.")
            return None
        
        r.raise_for_status()
        results = re.findall(pattern, r.text)
        
        if len(results) > 0:
            return results[0]
        else:
            print(f"No result found in the response.\nCheck your regex pattern {method} for {url}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed for {url}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error for {url}: {e}")
        return None

def playlist_text(url):
    text = ""
    try:
        r = requests.get(url, timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200:
            for line in r.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8', errors='ignore')
                if line[0] != "#":
                    text = text + urljoin(url, str(line))
                else:
                    text = str(text) + str(line)
                text += "\n"
            return text
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch playlist from {url}: {e}")
    return ""

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <config_file>")
        sys.exit(1)

    try:
        with open(sys.argv[1], "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except Exception as e:
        print(f"Failed to load config file: {e}")
        sys.exit(1)

    for site in config:
        site_path = os.path.join(os.getcwd(), site["slug"])
        os.makedirs(site_path, exist_ok=True)
        
        for channel in tqdm(site["channels"]):
            channel_file_path = os.path.join(site_path, slugify(channel["name"].lower()) + ".m3u8")
            channel_url = site["url"]
            
            for variable in channel["variables"]:
                channel_url = channel_url.replace(variable["name"], variable["value"])
            
            stream_url = get_stream_url(
                channel_url, 
                site["pattern"], 
                method=site.get("method", "GET"),
                headers=site.get("headers", {}),
                body=site.get("body", {})
            )
            
            if not stream_url:
                if os.path.isfile(channel_file_path):
                    os.remove(channel_file_path)
                continue
            
            if site.get("output_filter") and site["output_filter"] not in stream_url:
                if os.path.isfile(channel_file_path):
                    os.remove(channel_file_path)
                continue
            
            if site.get("mode") == "variant":
                text = playlist_text(stream_url)
            elif site.get("mode") == "master":
                text = f"#EXTM3U\n##EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH={site.get('bandwidth', 1280000)}\n{stream_url}"
            else:
                print("Wrong or missing playlist mode argument")
                text = ""
            
            if text:
                with open(channel_file_path, "w", encoding="utf-8") as channel_file:
                    channel_file.write(text)
            else:
                if os.path.isfile(channel_file_path):
                    os.remove(channel_file_path)

if __name__ == "__main__": 
    main()
