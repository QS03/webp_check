#!/usr/bin/env python3

import sys
import os
import requests
from PIL import Image
from config.tokens import CF_PURGE_CACHE,CF_ZONE_ID, CF_API_TOKEN, SITE_DOMAIN, FLUSH_DATABASE
from requests.exceptions import HTTPError, ConnectTimeout, ReadTimeout, SSLError
import subprocess

def replace_path(original_path, new_path):
    # Remove system path prefix
    original_string = original_path.replace("/var/www/html/wp-content/uploads/", "")
    new_string = new_path.replace("/var/www/html/wp-content/uploads/", "")
    
    command = [
        "sudo", "-u", "www-data", 
        "wp", "search-replace", original_string, new_string, 
        "--all-tables-with-prefix", f"--url={SITE_DOMAIN}"
        "--dry-run", 
        "--path=/var/www/html"
    ]
    subprocess.call(command)

    # Replace json encoded strings
    original_string = original_string.replace("/", "\\/")
    new_string = new_string.replace("/", "\\/")
    
    command = [
        "sudo", "-u", "www-data", 
        "wp", "search-replace", original_string, new_string, 
        "--all-tables-with-prefix", f"--url={SITE_DOMAIN}"
        "--dry-run", 
        "--path=/var/www/html"
    ]
    subprocess.call(command)    


def webp_check(file_dir):
    if os.path.exists(file_dir) and os.path.isdir(file_dir):
        purge_cache = False
        if not file_dir[-1] == "/":
            file_dir = file_dir + "/"
        files = os.listdir(file_dir)
        for f in files:
            f_path = file_dir + f
            if os.path.isfile(f_path):
                if f_path.split('.')[-1] == "jpg" or f_path.split('.')[-1] == "jpeg" or f_path.split('.')[-1] == "png":
                    # check if webp equivalent exists
                    ext = f_path.split('.')[-1:][0]
                    w_path = f_path.replace(ext,'webp')
                    if not os.path.exists(w_path):
                        convert2webp(f_path,w_path)
                        print(f"'{f_path}' Converted to '{w_path}'")
                        replace_path(f_path, w_path)
                        purge_cache = True
            elif os.path.isdir(f_path):
                webp_check(f_path)

        # Flush changes
        command = [
            "sudo", "-u", "www-data", 
            "wp", "cache", "flush", "--path=/var/www/html"
        ]
        if FLUSH_DATABASE:
            subprocess.call(command)

        if purge_cache and CF_PURGE_CACHE:
            purge_cloudflare_cache()
    else:
        print(f"'{file_dir}' either doesn't exist, or is not a dir...")

def convert2webp(f_image,webp_image):
    im = Image.open(f_image).convert("RGB")
    im.save(webp_image,"webp")
    im.close()

def purge_cloudflare_cache():
    URL = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/purge_cache'
    cf_headers = {"Content-Type": "Application/json", "Authorization": f"Bearer {CF_API_TOKEN}"}
    cf_data = '{"purge_everything":true}'

    try:
        response = requests.post(URL,headers=cf_headers,data=cf_data)
    except Exception as err:
        print("There was an issue calling cloudflare.")
    else:
        if response.status_code == 200 and response.json()['success']:
            print("cache has been purged.")
        else:
            print("cache has NOT been purged.")
            print(f"{response.json()}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        webp_check(sys.argv[1])
    else:
        print("missing argument...")
        exit(1)
