# -*- coding: utf-8 -*-
import os
# confluence-dumper, a Python project to export spaces, pages and attachments
#
# Copyright (c) Siemens AG, 2016
#
# Authors:
#   Thomas Maier <thomas.tm.maier@siemens.com>
#
# This work is licensed under the terms of the MIT license.
# See the LICENSE.md file in the top-level directory.

# Confluence URL
CONFLUENCE_BASE_URL = os.getenv('CONFLUENCE_BASE_URL').strip("/") #have to remove slash in the end just in case
# print(CONFLUENCE_BASE_URL)
# A list of space keys to export (leave it empty to export all available spaces)
SPACES_TO_EXPORT = [ i.strip() for i in os.getenv('SPACES_TO_EXPORT').split(", ") ]

# Confluence authentication
# Example for HTTP Basic Authentication: ('johndoe', 'sup3rs3cur3pw')
HTTP_AUTHENTICATION = (os.getenv('HTTP_AUTHENTICATION_USERNAME'), os.getenv('HTTP_AUTHENTICATION_PASSWORD'))

# Verify x.509 certificate of confluence http server
VERIFY_PEER_CERTIFICATE = bool(os.getenv('VERIFY_PEER_CERTIFICATE'))

# Proxy configuration
# Example: {'http': 'http://localhost:3128', 'https': 'http://localhost:3128'}
HTTP_PROXIES = {}
# HTTP_PROXIES is set to {}, standard python request proxy environment variables are used.
HTTP_PROXY = os.getenv('HTTP_PROXY')
HTTPS_PROXY = os.getenv('HTTPS_PROXY')

# Additional headers
# Example for custom authentication HTTP_CUSTOM_HEADERS: "user: johndoe, password:sup3rs3cur3pw"
# Example for custom authentication HTTP_CUSTOM_HEADERS: "cookie: anycookie value"
HTTP_CUSTOM_HEADERS = dict(map(str.strip, sub.split(':', 1)) for sub in os.getenv('HTTP_CUSTOM_HEADERS').split(', ') if ':' in sub)

# Export specific settings
EXPORT_FOLDER = os.getenv('EXPORT_FOLDER')
DOWNLOAD_SUB_FOLDER = os.getenv('DOWNLOAD_SUB_FOLDER')
TEMPLATE_FILE = os.getenv('TEMPLATE_FILE')

# Confluence generates thumbnails for the following image formats
CONFLUENCE_THUMBNAIL_FORMATS = [ i.strip() for i in os.getenv('CONFLUENCE_THUMBNAIL_FORMATS').split(", ") ]

# Confluence generates image previews for the following file formats
CONFLUENCE_GENERATED_PREVIEW_FORMATS = [ i.strip() for i in os.getenv('CONFLUENCE_GENERATED_PREVIEW_FORMATS').split(", ") ]

# The following message is displayed for page forwardings
HTML_FORWARD_MESSAGE = '<a href="%s">If you are not automatically forwarded to %s, please click here!</a>'
