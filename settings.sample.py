# -*- coding: utf-8 -*-

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
CONFLUENCE_BASE_URL = 'http://192.168.240.188:8090'

# A list of space keys to export
SPACES_TO_EXPORT = ['TES', 'TE2', 'TE3']

# Confluence authentication
# Example for HTTP Basic Authentication: ('johndoe', 'sup3rs3cur3pw')
HTTP_AUTHENTICATION = ('johndoe', 'sup3rs3cur3pw')

# Verify x.509 certificate of confluence http server
VERIFY_PEER_CERTIFICATE = True

# Proxy configuration
# Example: {'http': 'http://localhost:3128', 'https': 'http://localhost:3128'}
HTTP_PROXIES = {}

# Additional headers
# Example for custom authentication: {'user': 'johndoe', 'password': 'sup3rs3cur3pw'}
HTTP_CUSTOM_HEADERS = None

# Export specific settings
EXPORT_FOLDER = 'export'
DOWNLOAD_SUB_FOLDER = 'attachments'
TEMPLATE_FILE = 'template.html'

# Confluence generates thumbnails for the following image formats
CONFLUENCE_THUMBNAIL_FORMATS = ['gif', 'jpeg', 'jpg', 'png']

# Confluence generates image previews for the following file formats
CONFLUENCE_GENERATED_PREVIEW_FORMATS = ['pdf']

# The following message is displayed for page forwardings
HTML_FORWARD_MESSAGE = '<a href="%s">If you are not automatically forwarded to %s, please click here!</a>'
