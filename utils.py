# -*- coding: utf-8 -*-

import requests
import shutil
import re
import urllib


def http_get(request_url, auth=None):
    """ Requests a HTTP url and returns a requested JSON response.

    :param request_url: HTTP URL to request.
    :param auth: (optional) Auth tuple to use HTTP Auth (supported: Basic/Digest/Custom).
    """
    response = requests.get(request_url, auth=auth)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception('Error %s: %s' % (response.status_code, response.reason))


def http_download_binary_file(request_url, file_path, auth=None):
    """ Requests a HTTP url to save a file on the local filesystem.

    :param request_url: Requested HTTP URL.
    :param file_path: Local file path.
    :param auth: (optional) Auth tuple to use HTTP Auth (supported: Basic/Digest/Custom).
    """
    response = requests.get(request_url, stream=True, auth=auth)
    if response.status_code == 200:
        with open(file_path, 'wb') as downloaded_file:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, downloaded_file)


def write_2_file(path, content):
    """ Writes a string to a file.

    :param path: Local file path.
    :param content: String content to persist.
    """
    with open(path, 'w') as the_file:
        the_file.write(content.encode('utf8'))


def write_html_2_file(path, title, content, html_template):
    """ Writes HTML content to a file using a template.

    :param path: Local file path
    :param title: page title
    :param content: page content
    :param html_template: page template; supported placeholders: ``{% title %}``, ``{% content %}``
    """
    html_content = html_template

    # Replace placeholders
    replacements = {'title': title,
                    'content': content}

    for placeholder, replacement in replacements.iteritems():
        regex_placeholder = r'{%\s*' + placeholder + r'\s*%\}'
        html_content = re.sub(regex_placeholder, replacement, html_content, flags=re.IGNORECASE)

    write_2_file(path, html_content)


def decode_url(encoded_url):
    """ Unquotes and decodes a given URL.

    :param encoded_url: Encoded URL
    """
    return urllib.unquote(encoded_url).decode('utf8')
