#!/usr/bin/env python3

import sys
import os
import requests
from PIL import Image
from config.tokens import CF_PURGE_CACHE, CF_ZONE_ID, CF_API_TOKEN, SITE_DOMAIN, FLUSH_DATABASE
from requests.exceptions import HTTPError, ConnectTimeout, ReadTimeout, SSLError
from subprocess import check_output

import logging
logging.basicConfig(filename='logs.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def replace_path(original_path, new_path):
    # Remove system path prefix
    original_string = original_path.replace("/var/www/html/wp-content/uploads/", "")
    new_string = new_path.replace("/var/www/html/wp-content/uploads/", "")

    command = [
        "sudo", "-u", "www-data",
        "wp", "search-replace", original_string, new_string,
        "wp_post*",
        "--all-tables-with-prefix", f"--url={SITE_DOMAIN}"
                                    "--dry-run",
        "--path=/var/www/html"
    ]
    output = check_output(command)
    logger.info(output)

    # Replace json encoded strings
    original_string = original_string.replace("/", "\\/")
    new_string = new_string.replace("/", "\\/")

    command = [
        "sudo", "-u", "www-data",
        "wp", "search-replace", original_string, new_string,
        "wp_post*",
        "--all-tables-with-prefix", f"--url={SITE_DOMAIN}"
                                    "--dry-run",
        "--path=/var/www/html"
    ]
    output = check_output(command)
    logger.info(output)


def webp_check(file_dir):
    extensions = [".jpg", ".jpeg", ".png", ".gif"]

    for root, dirs, files in os.walk(file_dir):
        for file_name in files:
            file_path = f"{root}/{file_name}"
            purge_cache = True

            if file_path.endswith(tuple(extensions)):
                ext = file_path.split('.')[-1:][0]
                webp_path = file_path.replace(f".{ext}", '.webp')
                logger.info(webp_path)

                if not os.path.exists(webp_path):
                    convert2webp(file_path, webp_path)
                    logger.info(f"'{file_path}' Converted to '{webp_path}'")
                    replace_path(file_path, webp_path)
                    purge_cache = True

            # Flush changes
            command = [
                "sudo", "-u", "www-data",
                "wp", "cache", "flush", "--path=/var/www/html"
            ]
            if FLUSH_DATABASE:
                output = check_output(command)
                logger.info(output)

            if purge_cache and CF_PURGE_CACHE:
                purge_cloudflare_cache()


def convert2webp(f_image, webp_image):
    im = Image.open(f_image).convert("RGB")
    im.save(webp_image, "webp")
    im.close()


def purge_cloudflare_cache():
    URL = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/purge_cache'
    cf_headers = {"Content-Type": "Application/json", "Authorization": f"Bearer {CF_API_TOKEN}"}
    cf_data = '{"purge_everything":true}'

    try:
        response = requests.post(URL, headers=cf_headers, data=cf_data)
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
