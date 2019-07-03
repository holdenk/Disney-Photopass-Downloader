#!/usr/bin/python

import os
import sys
import string
import time
import re  # regex
import httplib, urllib, urllib2  # url encode, image saving
import json
from cookielib import CookieJar
import datetime
from subprocess import call  # call linux command to set exif data

# from datutil.parser import parse #requires python-dateutil package. used to parse with timezone
# from gi.repository import GExiv2 # requires python-gi
save_location = "./photos/"


def module_exists(module_name):
    try:
        __import__(module_name)
    except ImportError:
        return False
    else:
        return True


# Import user created settings. This will override built-in settings if defined.
if module_exists("config"):
    import config
else:
    print("Please set up the config.py file. Copy 'sample.config.py' to 'config.py' and set up options")
    sys.exit(2)


# Initialize cookie jar and session
cookies = CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))

print("Load login page")

### Load the login page. This will initialize some cookies. Save them.
login_page = opener.open('https://disneyland.disney.go.com/login/?returnUrl=https%3A%2F%2Fdisneyland.disney.go.com%2Fphotopass')
# cookies are automatically saved.

# grab the unique CSRF key. parse it.
csrf_key = re.search('id="pep_csrf" value=".*"', login_page.read())
csrf_key = csrf_key.group(0)
csrf_key = string.split(csrf_key, "\"")  # split on double quote. easiest way.
csrf_key = csrf_key[len(csrf_key) - 2]  # get the second to last item (last item is empty). array is 0-based, length is 1-based, so subtract 2

print("POST login info")
### Post the login page with credentials (and cookies). Save the cookies.
post_data = urllib.urlencode({'pep_csrf': csrf_key, 'username': config.username, 'password': config.password})
login_post = opener.open('https://disneyland.disney.go.com/login/?returnUrl=https%3A%2F%2Fdisneyland.disney.go.com%2Fphotopass', post_data)
print(login_post)

fetch_gallery = opener.open('https://disneyland.disney.go.com/photopass/gallery')
print(fetch_gallery)


print("Get photo URLs & details")
### Grab the list of photos with their unique ids and medium resolution urls
details_url_list = opener.open("https://disneyland.disney.go.com/photopass-api/all-media?pagenum=1&pagesize=20&sortAscending=false")
details_list = json.load(details_url_list)
print (json.dumps(details_list, sort_keys=True, indent=4))

print("Save photos")

def process_encounters(encounters):
    for encounter in encounters:
        for photo in encounter['mediaList']:
            if photo['mediaType'] != "PICTURE":
                continue
            photo_id = photo['mediaId']
            filename = '%s.jpg' % photo_id
            url = photo['mediaBase']['uri']
            date_created = datetime.datetime.strptime(photo['captureDate'], "%Y-%m-%dT%H:%M:%SZ")
            print (url)
            if url:  # one final check to make sure the url is defined
                print('File ' + filename)
                # Skip download if target already exists but stll update metadata.
                if os.path.isfile(filename):
                    print('Skipping dl - already downloaded')
                else:
                    print('Fetching...')
                    urllib.urlretrieve(url, filename)  # gets the file and saves it
                date_created_exif_format = datetime.datetime.strftime(date_created, '%Y:%m:%d-%H:%M:%S')
                try:
                    call(['jhead', '-mkexif', filename])  # initialize exif
                    call(['jhead', '-ts' + date_created_exif_format, filename])  # set timestamp
                    call(['jhead', '-ft', filename])  # set the OS timestamp to be the same as the exif timestamp
                except OSError as e:
                    print("'jhead' is not installed. EXIF and OS timestamp not set.")
                try:
                    call(['exiftool', '-GPSLatitude="33.8121"', '-GPSLongitude="-117.918976"', filename]) # Set lat long to disneyland
                except OSError as e:
                    print("exiftool not installed, not updating lat/lon")
            print('')


while details_list['nextPage'] is not None:
    next_url = details_list['nextPage']
    process_encounters(details_list['guestMedia']['encounters'])
    details_list = json.load(opener.open(next_url))

process_encounters(details_list['guestMedia']['encounters'])

print('Done!')

### After saving, add EXIF information to include timestamp
