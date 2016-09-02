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

"""
Confluence-dumper is a Python project to export spaces, pages and attachments
"""

from __future__ import print_function
import sys
import codecs

import os
import shutil
from lxml import html
from lxml.etree import XMLSyntaxError

import utils
import settings


CONFLUENCE_DUMPER_VERSION = '1.0.0'
TITLE_OUTPUT = 'C O N F L U E N C E   D U M P E R  %s' % CONFLUENCE_DUMPER_VERSION


def error_print(*args, **kwargs):
    """ Wrapper for the print function which leads to stderr outputs.

    :param args: Not necessary.
    :param kwargs: Not necessary.
    """
    print(*args, file=sys.stderr, **kwargs)


def derive_downloaded_file_name(download_url):
    """ Generates the name of a downloaded/exported file.

        Example: /download/attachments/524291/peak.jpeg?version=1&modificationDate=1459521827579&api=v2
            => <download_folder>/524291_attachments_peak.jpeg
        Example: /download/thumbnails/524291/Harvey.jpg?version=1&modificationDate=1459521827579&api=v2
            => <download_folder>/524291_thumbnails_Harvey.jpg

    :param download_url: Confluence download URL which is used to derive the downloaded file name.
    :returns: Derived file name; if derivation is not possible, None is returned.
    """
    if '/download/' in download_url:
        download_url_parts = download_url.split('/')
        download_page_id = download_url_parts[3]
        download_file_type = download_url_parts[2]
        download_original_file_name = download_url_parts[4].split('?')[0]
        return '%s_%s_%s' % (download_page_id, download_file_type, download_original_file_name)
    elif '/rest/documentConversion/latest/conversion/thumbnail/' in download_url:
        file_id = download_url.split('/rest/documentConversion/latest/conversion/thumbnail/')[1][0:-2]
        return 'generated_preview_%s.jpg' % file_id
    else:
        return None


def provide_unique_file_name(duplicate_file_names, page_file_matching, page_title):
    """ Provides an unique AND sanitized file name for a given page title. Confluence does not allow the same page title
    in one particular space but collisions are possible after filesystem sanitization.

    :param duplicate_file_names: A dict in the structure {'<sanitized filename>': amount of duplicates}
    :param page_file_matching: A dict in the structure {'<page title>': '<used offline filename>'}
    :param page_title: Page title which is used to generate the unique file name
    """
    if page_title in page_file_matching:
        file_name = page_file_matching[page_title]
    else:
        file_name = utils.sanitize_for_filename(page_title)
        if file_name in duplicate_file_names:
            duplicate_file_names[file_name] += 1
            file_name = '%s_%d.html' % (file_name, duplicate_file_names[file_name])
        else:
            duplicate_file_names[file_name] = 0
            file_name = '%s.html' % file_name
        page_file_matching[page_title] = file_name
    return file_name


def handle_html_references(html_content, duplicate_file_names, page_file_matching, depth=0):
    """ Repairs links in the page contents with local links.

    :param html_content: Confluence HTML content.
    :param duplicate_file_names: A dict in the structure {'<sanitized filename>': amount of duplicates}
    :param page_file_matching: A dict in the structure {'<page title>': '<used offline filename>'}
    :param depth: (optional) Hierarchy depth of the handled Confluence page.
    :returns: Fixed HTML content.
    """
    try:
        html_tree = html.fromstring(html_content)
    except XMLSyntaxError:
        print('%sWARNING: Could not parse HTML content of last page. Original content will be downloaded as it is.'
              % ('\t'*(depth+1)))
        return html_content

    # Fix links to other Confluence pages
    # Example: /display/TES/pictest1
    #       => pictest1.html
    # TODO: This code does not work for "Recent space activity" areas in space pages because of a different url format.
    xpath_expr = '//a[contains(@href, "/display/")]'
    for link_element in html_tree.xpath(xpath_expr):
        if not link_element.get('class'):
            page_title = link_element.attrib['href'].split('/')[3]
            page_title = page_title.replace('+', ' ')
            decoded_page_title = utils.decode_url(page_title)
            link_element.attrib['href'] = provide_unique_file_name(duplicate_file_names, page_file_matching,
                                                                   decoded_page_title)

    # Fix links to other Confluence pages when page ids are used
    xpath_expr = '//a[contains(@href, "/pages/viewpage.action?pageId=")]'
    for link_element in html_tree.xpath(xpath_expr):
        if not link_element.get('class'):
            page_id = link_element.attrib['href'].split('/pages/viewpage.action?pageId=')[1]
            link_element.attrib['href'] = '%s.html' % utils.sanitize_for_filename(page_id)

    # Fix attachment links
    xpath_expr = '//a[contains(@class, "confluence-embedded-file")]'
    for link_element in html_tree.xpath(xpath_expr):
        file_url = link_element.attrib['href']
        file_name = derive_downloaded_file_name(file_url)
        relative_file_path = '%s/%s' % (settings.DOWNLOAD_SUB_FOLDER, file_name)
        link_element.attrib['href'] = relative_file_path

    # Fix file paths for img tags
    # TODO: Handle non-<img> tags as well if necessary.
    # TODO: Support files with different versions as well if necessary.
    possible_image_xpaths = ['//img[contains(@src, "/download/")]',
                             '//img[contains(@src, "/rest/documentConversion/latest/conversion/thumbnail/")]']
    xpath_expr = '|'.join(possible_image_xpaths)
    for img_element in html_tree.xpath(xpath_expr):
        # Replace file path
        file_url = img_element.attrib['src']
        file_name = derive_downloaded_file_name(file_url)
        relative_file_path = '%s/%s' % (settings.DOWNLOAD_SUB_FOLDER, file_name)
        img_element.attrib['src'] = relative_file_path

        # Add alt attribute if it does not exist yet
        if not 'alt' in img_element.attrib.keys():
            img_element.attrib['alt'] = relative_file_path

    return html.tostring(html_tree)


def download_file(clean_url, download_folder, downloaded_file_name, depth=0, error_output=True):
    """ Downloads a specific file.

    :param clean_url: Decoded URL to the file.
    :param download_folder: Folder to place the downloaded file in.
    :param downloaded_file_name: File name to save the download to.
    :param depth: (optional) Hierarchy depth of the handled Confluence page.
    :param error_output: (optional) Set to False if you do not want to see any error outputs
    :returns: Path to the downloaded file.
    """
    downloaded_file_path = '%s/%s' % (download_folder, downloaded_file_name)

    # Download file if it does not exist yet
    if not os.path.exists(downloaded_file_path):
        absolute_download_url = '%s%s' % (settings.CONFLUENCE_BASE_URL, clean_url)
        print('%sDOWNLOAD: %s' % ('\t'*(depth+1), downloaded_file_name))
        try:
            utils.http_download_binary_file(absolute_download_url, downloaded_file_path,
                                            auth=settings.HTTP_AUTHENTICATION, headers=settings.HTTP_CUSTOM_HEADERS,
                                            verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
                                            proxies=settings.HTTP_PROXIES)

        except utils.ConfluenceException as e:
            if error_output:
                error_print('%sERROR: %s' % ('\t'*(depth+2), e))
            else:
                print('%sWARNING: %s' % ('\t'*(depth+2), e))

    return downloaded_file_path


def download_attachment(download_url, download_folder, attachment_id, depth=0):
    """ Repairs links in the page contents with local links.

    :param download_url: Confluence download URL.
    :param download_folder: Folder to place downloaded files in.
    :param attachment_id: ID of the attachment to download.
    :param depth: (optional) Hierarchy depth of the handled Confluence page.
    :returns: Path and name of the downloaded file as dict.
    """
    clean_url = utils.decode_url(download_url)
    downloaded_file_name = derive_downloaded_file_name(clean_url)
    downloaded_file_path = download_file(download_url, download_folder, downloaded_file_name, depth=depth)

    # Download the thumbnail as well if the attachment is an image
    clean_thumbnail_url = clean_url.replace('/attachments/', '/thumbnails/', 1)
    downloaded_thumbnail_file_name = derive_downloaded_file_name(clean_thumbnail_url)
    if utils.is_file_format(downloaded_thumbnail_file_name, settings.CONFLUENCE_THUMBNAIL_FORMATS):
        # TODO: Confluence creates thumbnails always as PNGs but does not change the file extension to .png.
        download_file(clean_thumbnail_url, download_folder, downloaded_thumbnail_file_name, depth=depth,
                      error_output=False)

    # Download the image preview as well if Confluence generated one for the attachment
    if utils.is_file_format(downloaded_file_name, settings.CONFLUENCE_GENERATED_PREVIEW_FORMATS):
        clean_preview_url = '/rest/documentConversion/latest/conversion/thumbnail/%s/1' % attachment_id
        downloaded_preview_file_name = derive_downloaded_file_name(clean_preview_url)
        download_file(clean_preview_url, download_folder, downloaded_preview_file_name, depth=depth, error_output=False)

    return {'file_name': downloaded_file_name, 'file_path': downloaded_file_path}


def create_html_attachment_index(attachments):
    """ Creates a HTML list for a list of attachments.

    :param attachments: List of attachments.
    :returns: Attachment list as HTML.
    """
    html_content = '\n\n<h2>Attachments</h2>'
    if len(attachments) > 0:
        html_content += '<ul>\n'
        for attachment in attachments:
            relative_file_path = '/'.join(attachment['file_path'].split('/')[2:])
            html_content += '\t<li><a href="%s">%s</a></li>\n' % (relative_file_path, attachment['file_name'])
        html_content += '</ul>\n'
    return html_content


def fetch_page_recursively(page_id, folder_path, download_folder, html_template, depth=0, duplicate_file_names=None,
                           page_file_matching=None):
    """ Fetches a Confluence page and its child pages (with referenced downloads).

    :param page_id: Confluence page id.
    :param folder_path: Folder to place downloaded pages in.
    :param download_folder: Folder to place downloaded files in.
    :param html_template: HTML template used to export Confluence pages.
    :param depth: (optional) Hierarchy depth of the handled Confluence page.
    :param duplicate_file_names: A dict in the structure {'<sanitized filename>': amount of duplicates}
    :param page_file_matching: A dict in the structure {'<page title>': '<used offline filename>'}
    :returns: Information about downloaded files (pages, attachments, images, ...) as a dict (None for exceptions)
    """
    if not duplicate_file_names:
        duplicate_file_names = {}
    if not page_file_matching:
        page_file_matching = {}

    page_url = '%s/rest/api/content/%s?expand=children.page,children.attachment,body.view.value' \
               % (settings.CONFLUENCE_BASE_URL, page_id)
    try:
        response = utils.http_get(page_url, auth=settings.HTTP_AUTHENTICATION, headers=settings.HTTP_CUSTOM_HEADERS,
                                  verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
                                  proxies=settings.HTTP_PROXIES)
        page_content = response['body']['view']['value']

        page_title = response['title']
        print('%sPAGE: %s (%s)' % ('\t'*(depth+1), page_title, page_id))

        # Construct unique file name
        file_name = provide_unique_file_name(duplicate_file_names, page_file_matching, page_title)

        # Remember this file and all children
        path_collection = {'file_path': file_name, 'page_title': page_title, 'child_pages': [], 'child_attachments': []}

        # Download attachments of this page
        # TODO: Outsource/Abstract the following two while loops because of much duplicate code.
        page_url = '%s/rest/api/content/%s/child/attachment?limit=25' % (settings.CONFLUENCE_BASE_URL, page_id)
        counter = 0
        while page_url:
            response = utils.http_get(page_url, auth=settings.HTTP_AUTHENTICATION, headers=settings.HTTP_CUSTOM_HEADERS,
                                      verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
                                      proxies=settings.HTTP_PROXIES)
            counter += len(response['results'])
            for attachment in response['results']:
                download_url = attachment['_links']['download']
                attachment_id = attachment['id'][3:]
                attachment_info = download_attachment(download_url, download_folder, attachment_id, depth=depth+1)
                path_collection['child_attachments'].append(attachment_info)

            if 'next' in response['_links'].keys():
                page_url = response['_links']['next']
                page_url = '%s%s' % (settings.CONFLUENCE_BASE_URL, page_url)
            else:
                page_url = None

        # Export HTML file
        page_content = handle_html_references(page_content, duplicate_file_names, page_file_matching, depth=depth+1)
        file_path = '%s/%s' % (folder_path, file_name)
        page_content += create_html_attachment_index(path_collection['child_attachments'])
        utils.write_html_2_file(file_path, page_title, page_content, html_template)

        # Save another file with page id which forwards to the original one
        id_file_path = '%s/%s.html' % (folder_path, page_id)
        id_file_page_title = 'Forward to page %s' % page_title
        original_file_link = utils.sanitize_for_filename(file_name)
        id_file_page_content = settings.HTML_FORWARD_MESSAGE % (original_file_link, page_title)
        id_file_forward_header = '<meta http-equiv="refresh" content="0; url=%s" />' % original_file_link
        utils.write_html_2_file(id_file_path, id_file_page_title, id_file_page_content, html_template,
                                additional_headers=[id_file_forward_header])

        # Iterate through all child pages
        page_url = '%s/rest/api/content/%s/child/page?limit=25' % (settings.CONFLUENCE_BASE_URL, page_id)
        counter = 0
        while page_url:
            response = utils.http_get(page_url, auth=settings.HTTP_AUTHENTICATION, headers=settings.HTTP_CUSTOM_HEADERS,
                                      verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
                                      proxies=settings.HTTP_PROXIES)
            counter += len(response['results'])
            for child_page in response['results']:
                paths = fetch_page_recursively(child_page['id'], folder_path, download_folder, html_template,
                                               depth=depth+1, duplicate_file_names=duplicate_file_names,
                                               page_file_matching=page_file_matching)
                if paths:
                    path_collection['child_pages'].append(paths)

            if 'next' in response['_links'].keys():
                page_url = response['_links']['next']
                page_url = '%s%s' % (settings.CONFLUENCE_BASE_URL, page_url)
            else:
                page_url = None
        return path_collection

    except utils.ConfluenceException as e:
        error_print('%sERROR: %s' % ('\t'*(depth+1), e))
        return None


def create_html_index(index_content):
    """ Creates an HTML index (mainly to navigate through the exported pages).

    :param index_content: Dictionary which contains file paths, page titles and their children recursively.
    :returns: Content index as HTML.
    """
    file_path = index_content['file_path']
    page_title = index_content['page_title']
    page_children = index_content['child_pages']

    html_content = '<a href="%s">%s</a>' % (utils.sanitize_for_filename(file_path), page_title)

    if len(page_children) > 0:
        html_content += '<ul>\n'
        for child in page_children:
            html_content += '\t<li>%s</li>\n' % create_html_index(child)
        html_content += '</ul>\n'

    return html_content


def print_welcome_output():
    """ Displays software title and some license information """
    print()
    print('\t %s' % TITLE_OUTPUT)
    print('\t %s\n' % ('='*len(TITLE_OUTPUT)))
    print('... a Python project to export spaces, pages and attachments\n')
    print('Copyright (c) Siemens AG, 2016\n')
    print('Authors:')
    print('  Thomas Maier <thomas.tm.maier@siemens.com>\n')
    print('This work is licensed under the terms of the MIT license.')
    print('See the LICENSE.md file in the top-level directory.\n')


def main():
    """ Main function to start the confluence-dumper. """

    # Configure console for unicode output via stdout/stderr
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

    # Delete old export
    if os.path.exists(settings.EXPORT_FOLDER):
        shutil.rmtree(settings.EXPORT_FOLDER)
    os.makedirs(settings.EXPORT_FOLDER)

    # Read HTML template
    template_file = open(settings.TEMPLATE_FILE)
    html_template = template_file.read()

    # Welcome output
    print_welcome_output()

    # Fetch all spaces if spaces were not configured via settings
    if len(settings.SPACES_TO_EXPORT) > 0:
        spaces_to_export = settings.SPACES_TO_EXPORT
    else:
        spaces_to_export = []
        page_url = '%s/rest/api/space?limit=25' % settings.CONFLUENCE_BASE_URL
        while page_url:
            response = utils.http_get(page_url, auth=settings.HTTP_AUTHENTICATION, headers=settings.HTTP_CUSTOM_HEADERS,
                                      verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
                                      proxies=settings.HTTP_PROXIES)
            for space in response['results']:
                spaces_to_export.append(space['key'])

            if 'next' in response['_links'].keys():
                page_url = response['_links']['next']
                page_url = '%s%s' % (settings.CONFLUENCE_BASE_URL, page_url)
            else:
                page_url = None

    print('Exporting %d space(s): %s' % (len(spaces_to_export), ', '.join(spaces_to_export)))

    # Export spaces
    space_counter = 0
    for space in spaces_to_export:
        space_counter += 1

        # Create folders for this space
        space_folder = '%s/%s' % (settings.EXPORT_FOLDER, utils.sanitize_for_filename(space))
        os.makedirs(space_folder)
        download_folder = '%s/%s' % (space_folder, settings.DOWNLOAD_SUB_FOLDER)
        os.makedirs(download_folder)

        space_url = '%s/rest/api/space/%s?expand=homepage' % (settings.CONFLUENCE_BASE_URL, space)

        print()
        try:
            response = utils.http_get(space_url, auth=settings.HTTP_AUTHENTICATION,
                                      headers=settings.HTTP_CUSTOM_HEADERS,
                                      verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
                                      proxies=settings.HTTP_PROXIES)
            space_name = response['name']

            print('SPACE (%d/%d): %s (%s)' % (space_counter, len(spaces_to_export), space_name, space))

            space_page_id = response['homepage']['id']
            path_collection = fetch_page_recursively(space_page_id, space_folder, download_folder, html_template)

            if path_collection:
                # Create index file for this space
                space_index_path = '%s/index.html' % space_folder
                space_index_title = 'Index of Space %s (%s)' % (space_name, space)
                space_index_content = create_html_index(path_collection)
                utils.write_html_2_file(space_index_path, space_index_title, space_index_content, html_template)
        except utils.ConfluenceException as e:
            error_print('ERROR: %s' % e)


if __name__ == "__main__":
    try:
        main()
        print('Finished!')
    except KeyboardInterrupt:
        error_print('ERROR: Keyboard Interrupt.')
        sys.exit(1)
