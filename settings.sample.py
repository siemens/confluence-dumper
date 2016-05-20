# -*- coding: utf-8 -*-

# Confluence URL
CONFLUENCE_BASE_URL = 'http://192.168.240.188:8090'

# A list of space keys to export
SPACES_TO_EXPORT = ['TES', 'TE2', 'TE3']

# Confluence authentication
# Example for HTTP Basic Authentication: ('johndoe', 'sup3rs3cur3pw')
HTTP_AUTHENTICATION = ('johndoe', 'sup3rs3cur3pw')

# Additional headers
# Example for custom authentication: {'user': 'johndoe', 'password': 'sup3rs3cur3pw'}
HTTP_CUSTOM_HEADERS = None

# Export specific settings
EXPORT_FOLDER = 'export'
DOWNLOAD_SUB_FOLDER = 'attachments'
TEMPLATE_FILE = 'template.html'

# Supported Confluence image formats
CONFLUENCE_IMAGE_FORMATS = ['gif', 'jpeg', 'jpg', 'png']
