# -*- coding: utf-8 -*-

import requests
import shutil
import re
import urllib


def http_get(request_url, auth=None, headers=None):
    """ Requests a HTTP url and returns a requested JSON response.

    :param request_url: HTTP URL to request.
    :param auth: (optional) Auth tuple to use HTTP Auth (supported: Basic/Digest/Custom).
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :returns: JSON response.
    :raises: Exception in the case of the server does not answer with HTTP code 200.
    """
    response = requests.get(request_url, auth=auth, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception('Error %s: %s' % (response.status_code, response.reason))


def http_download_binary_file(request_url, file_path, auth=None, headers=None):
    """ Requests a HTTP url to save a file on the local filesystem.

    :param request_url: Requested HTTP URL.
    :param file_path: Local file path.
    :param auth: (optional) Auth tuple to use HTTP Auth (supported: Basic/Digest/Custom).
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    """
    response = requests.get(request_url, stream=True, auth=auth, headers=headers)
    if response.status_code == 200:
        with open(file_path, 'wb') as downloaded_file:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, downloaded_file)
    else:
        raise Exception('Error %s: %s' % (response.status_code, response.reason))


def write_2_file(path, content):
    """ Writes a string to a file.

    :param path: Local file path.
    :param content: String content to persist.
    """
    with open(path, 'w') as the_file:
        the_file.write(content.encode('utf8'))


def write_html_2_file(path, title, content, html_template, additional_headers=None):
    """ Writes HTML content to a file using a template.

    :param path: Local file path
    :param title: page title
    :param content: page content
    :param html_template: page template; supported placeholders: ``{% title %}``, ``{% content %}``
    :param additional_headers: (optional) Additional HTML headers.
    """
    html_content = html_template

    # Build additional HTML headers
    additional_html_headers = '\n\t'.join(additional_headers) if additional_headers else ''

    # Replace placeholders
    replacements = {'title': title,
                    'content': content,
                    'additional_headers': additional_html_headers}

    for placeholder, replacement in replacements.iteritems():
        regex_placeholder = r'{%\s*' + placeholder + r'\s*%\}'
        html_content = re.sub(regex_placeholder, replacement, html_content, flags=re.IGNORECASE)

    write_2_file(path, html_content)


def decode_url(encoded_url):
    """ Unquotes and decodes a given URL.

    :param encoded_url: Encoded URL.
    :returns: Decoded URL.
    """
    return urllib.unquote(encoded_url).decode('utf8')


def encode_url(decoded_url):
    """ Quotes and encodes a given URL.

    :param decoded_url: Decoded URL.
    :returns: Encoded URL.
    """
    return urllib.quote(decoded_url).encode('utf8')


def is_file_format(file_name, file_extensions):
    """ Checks whether the extension of the given file is in a list of file extensions.

    :param file_name: Filename to check
    :param file_extensions: File extensions as a list
    :returns: True if the list contains the extension of the given file_name
    """
    file_extension = file_name.split('.')[-1]
    return file_extension in file_extensions
