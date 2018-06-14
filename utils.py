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

import requests
import shutil
import re
import urllib.parse


class ConfluenceException(Exception):
    """ Exception for Confluence export issues """
    def __init__(self, message):
        super(ConfluenceException, self).__init__(message)


def http_get(request_url, auth=None, headers=None, verify_peer_certificate=True, proxies=None):
    """ Requests a HTTP url and returns a requested JSON response.

    :param request_url: HTTP URL to request.
    :param auth: (optional) Auth tuple to use HTTP Auth (supported: Basic/Digest/Custom).
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param verify_peer_certificate: (optional) Flag to decide whether peer certificate has to be validated.
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :returns: JSON response.
    :raises: ConfluenceException in the case of the server does not answer HTTP code 200.
    """
    response = requests.get(request_url, auth=auth, headers=headers, verify=verify_peer_certificate, proxies=proxies)
    if 200 == response.status_code:
        return response.json()
    else:
        raise ConfluenceException('Error %s: %s on requesting %s' % (response.status_code, response.reason,
                                                                     request_url))


def http_download_binary_file(request_url, file_path, auth=None, headers=None, verify_peer_certificate=True,
                              proxies=None):
    """ Requests a HTTP url to save a file on the local filesystem.

    :param request_url: Requested HTTP URL.
    :param file_path: Local file path.
    :param auth: (optional) Auth tuple to use HTTP Auth (supported: Basic/Digest/Custom).
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param verify_peer_certificate: (optional) Flag to decide whether peer certificate has to be validated.
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :raises: ConfluenceException in the case of the server does not answer with HTTP code 200.
    """
    response = requests.get(request_url, stream=True, auth=auth, headers=headers, verify=verify_peer_certificate,
                            proxies=proxies)
    if 200 == response.status_code:
        with open(file_path, 'wb') as downloaded_file:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, downloaded_file)
    else:
        raise ConfluenceException('Error %s: %s on requesting %s' % (response.status_code, response.reason,
                                                                     request_url))


def write_2_file(path, content):
    """ Writes a string to a file.

    :param path: Local file path.
    :param content: String content to persist.
    """
    with open(path, 'w', encoding='utf8') as the_file:
        the_file.write(content)


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
    # Note: One backslash has to be escaped with two avoid that backslashes are interpreted as escape chars
    replacements = {'title': title, 'content': content, 'additional_headers': additional_html_headers}

    for placeholder, replacement in replacements.items():
        regex_placeholder = r'{%\s*' + placeholder + r'\s*%\}'
        try:
            html_content = re.sub(regex_placeholder, replacement.replace('\\', '\\\\'), html_content,
                                  flags=re.IGNORECASE)
        except Exception as e:
            raise ConfluenceException('Error %s: Cannot replace placeholders in template file.' % e)

    write_2_file(path, html_content)


def sanitize_for_filename(original_string):
    """ Sanitizes a string to use it as a filename on most filesystems.

    :param original_string: Original string to sanitize
    :returns: Sanitized string/filename
    """
    sanitized_file_name = re.sub('[\\\\/:*?\"<>|]', '_', original_string)
    return sanitized_file_name


def decode_url(encoded_url):
    """ Unquotes and decodes a given URL.

    :param encoded_url: Encoded URL.
    :returns: Decoded URL.
    """
    return urllib.parse.unquote(encoded_url)


def encode_url(decoded_url):
    """ Quotes and encodes a given URL.

    :param decoded_url: Decoded URL.
    :returns: Encoded URL.
    """
    return urllib.parse.quote(decoded_url)


def is_file_format(file_name, file_extensions):
    """ Checks whether the extension of the given file is in a list of file extensions.

    :param file_name: Filename to check
    :param file_extensions: File extensions as a list
    :returns: True if the list contains the extension of the given file_name
    """
    file_extension = file_name.split('.')[-1]
    return file_extension in file_extensions
