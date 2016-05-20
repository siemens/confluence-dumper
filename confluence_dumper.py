# -*- coding: utf-8 -*-

import os
import shutil

from lxml import html

import utils
import settings


def derive_downloaded_file_name(download_url):
    """ Generates the name of a downloaded/exported file.

        Example: /download/attachments/524291/peak.jpeg?version=1&modificationDate=1459521827579&api=v2
            => <download_folder>/524291_attachments_peak.jpeg
        Example: /download/thumbnails/524291/Harvey.jpg?version=1&modificationDate=1459521827579&api=v2
            => <download_folder>/524291_thumbnails_Harvey.jpg

    :param download_url: Confluence download URL which is used to derive the downloaded file name.
    :returns: Derived file name.
    """
    download_url_parts = download_url.split('/')
    download_page_id = download_url_parts[3]
    download_file_type = download_url_parts[2]
    download_original_file_name = download_url_parts[4].split('?')[0]
    return '%s_%s_%s' % (download_page_id, download_file_type, download_original_file_name)


def handle_html_references(html_content):
    """ Repairs links in the page contents with local links.

    :param html_content: Confluence HTML content.
    :returns: Fixed HTML content.
    """
    html_tree = html.fromstring(html_content)

    # Fix links to other Confluence pages
    # Example: /display/TES/pictest1
    #       => pictest1.html
    # TODO: This code does not work for "Recent space activity" areas in space pages because of a different url format.
    xpath_expr = '//a[starts-with(@href, "/display/")]'
    for link_element in html_tree.xpath(xpath_expr):
        if not link_element.get('class'):
            page_title = link_element.attrib['href'].split('/')[3]
            page_title = page_title.replace('+', ' ')
            link_element.attrib['href'] = '%s.html' % page_title

    # Fix file paths for img tags
    # TODO: Handle non-<img> tags as well if necessary.
    # TODO: Support files with different versions as well if necessary.
    xpath_expr = '//img[starts-with(@src, "/download/")]'
    for link_element in html_tree.xpath(xpath_expr):
        # Replace file path
        file_url = link_element.attrib['src']
        file_name = derive_downloaded_file_name(file_url)
        relative_file_path = '%s/%s' % (settings.DOWNLOAD_SUB_FOLDER, file_name)
        link_element.attrib['src'] = relative_file_path

        # Add alt attribute if it does not exist yet
        if not 'alt' in link_element.attrib.keys():
            link_element.attrib['alt'] = relative_file_path

    return html.tostring(html_tree)


def download_file(clean_url, download_folder, downloaded_file_name, depth=0):
    """ Downloads a specific file.

    :param clean_url: Decoded URL to the file.
    :param download_folder: Folder to place the downloaded file in.
    :param downloaded_file_name: File name to save the download to.
    :param depth: (optional) Hierarchy depth of the handled Confluence page.
    """
    downloaded_file_path = '%s/%s' % (download_folder, downloaded_file_name)

    # Download file if it does not exist yet
    if not os.path.exists(downloaded_file_path):
        absolute_download_url = '%s/%s' % (settings.CONFLUENCE_BASE_URL, clean_url)
        utils.http_download_binary_file(absolute_download_url, downloaded_file_path, auth=settings.HTTP_AUTHENTICATION,
                                        headers=settings.HTTP_CUSTOM_HEADERS)
        print '%sDOWNLOAD: %s' % ('\t'*(depth+1), downloaded_file_name)


def download_attachment(download_url, download_folder, depth=0):
    """ Repairs links in the page contents with local links.

    :param download_url: Confluence download URL.
    :param download_folder: Folder to place downloaded files in.
    :param depth: (optional) Hierarchy depth of the handled Confluence page.
    """
    clean_url = utils.decode_url(download_url)
    downloaded_file_name = derive_downloaded_file_name(clean_url)
    download_file(clean_url, download_folder, downloaded_file_name, depth=depth)

    # Download the thumbnail as well if the attachment is an image
    thumbnail_url = clean_url.replace('/attachments/', '/thumbnails/', 1)
    downloaded_file_name = derive_downloaded_file_name(thumbnail_url)
    if utils.is_file_format(downloaded_file_name, settings.CONFLUENCE_IMAGE_FORMATS):
        # TODO: Confluence creates thumbnails always as PNGs but does not change the file extension to .png.
        download_file(thumbnail_url, download_folder, downloaded_file_name, depth=depth)


def fetch_page_recursively(page_id, folder_path, download_folder, html_template, depth=0):
    """ Fetches a Confluence page and its child pages (with referenced downloads).

    :param page_id: Confluence page id.
    :param folder_path: Folder to place downloaded pages in.
    :param download_folder: Folder to place downloaded files in.
    :param depth: (optional) Hierarchy depth of the handled Confluence page.
    :returns: Information about downloaded files as a dict.
    """
    page_url = '%s/rest/api/content/%s?expand=children.page,children.attachment,body.view.value' \
               % (settings.CONFLUENCE_BASE_URL, page_id)
    response = utils.http_get(page_url, auth=settings.HTTP_AUTHENTICATION, headers=settings.HTTP_CUSTOM_HEADERS)

    page_title = response['title']
    print '%sPAGE: %s (%s)' % ('\t'*(depth+1), page_title, page_id)

    # Export file
    page_content = response['body']['view']['value']
    file_name = '%s.html' % page_title
    file_path = '%s/%s' % (folder_path, file_name)
    page_content = handle_html_references(page_content)
    # TODO: Replace page title in filename with page id.
    utils.write_html_2_file(file_path, page_title, page_content, html_template)

    # Remember this file and all children
    path_collection = {'file_path': file_name, 'page_title': page_title, 'children': []}

    # Download attachments of this page
    # TODO: Outsource/Abstract the following two while loops because of much duplicate code.
    page_url = '%s/rest/api/content/%s/child/attachment?limit=25' % (settings.CONFLUENCE_BASE_URL, page_id)
    counter = 0
    while page_url:
        response = utils.http_get(page_url, auth=settings.HTTP_AUTHENTICATION, headers=settings.HTTP_CUSTOM_HEADERS)
        counter += len(response['results'])
        for attachment in response['results']:
            download_url = attachment['_links']['download']
            download_attachment(download_url, download_folder, depth=depth+1)

        if 'next' in response['_links'].keys():
            page_url = response['_links']['next']
            page_url = '%s%s' % (settings.CONFLUENCE_BASE_URL, page_url)
        else:
            page_url = None

    # Iterate through all child pages
    page_url = '%s/rest/api/content/%s/child/page?limit=25' % (settings.CONFLUENCE_BASE_URL, page_id)
    counter = 0
    while page_url:
        response = utils.http_get(page_url, auth=settings.HTTP_AUTHENTICATION, headers=settings.HTTP_CUSTOM_HEADERS)
        counter += len(response['results'])
        for child_page in response['results']:
            paths = fetch_page_recursively(child_page['id'], folder_path, download_folder, html_template, depth=depth+1)
            path_collection['children'].append(paths)

        if 'next' in response['_links'].keys():
            page_url = response['_links']['next']
            page_url = '%s%s' % (settings.CONFLUENCE_BASE_URL, page_url)
        else:
            page_url = None

    return path_collection


def create_html_index(index_content):
    """ Creates an HTML index (mainly to navigate through the exported pages).

    :param index_content: Dictionary which contains file paths, page titles and their children recursively.
    :returns: Content index as HTML.
    """
    file_path = index_content['file_path']
    page_title = index_content['page_title']
    page_children = index_content['children']

    html_content = '<a href="%s">%s</a>\n' % (file_path, page_title)

    if len(page_children) > 0:
        html_content += '<ul>\n'
        for child in page_children:
            html_content += '\t<li>%s</li>\n' % create_html_index(child)
        html_content += '</ul>\n'

    return html_content


def main():
    """ Main function to start the confluence-dumper. """
    # Delete old export
    if os.path.exists(settings.EXPORT_FOLDER):
        shutil.rmtree(settings.EXPORT_FOLDER)
    os.makedirs(settings.EXPORT_FOLDER)

    # Read HTML template
    template_file = open(settings.TEMPLATE_FILE)
    html_template = template_file.read()

    # Export spaces
    for space in settings.SPACES_TO_EXPORT:
        # Create folders for this space
        space_folder = '%s/%s' % (settings.EXPORT_FOLDER, space)
        os.makedirs(space_folder)
        download_folder = '%s/%s' % (space_folder, settings.DOWNLOAD_SUB_FOLDER)
        os.makedirs(download_folder)

        space_url = '%s/rest/api/space/%s?expand=homepage' % (settings.CONFLUENCE_BASE_URL, space)
        response = utils.http_get(space_url, auth=settings.HTTP_AUTHENTICATION, headers=settings.HTTP_CUSTOM_HEADERS)
        space_name = response['name']

        print
        print 'SPACE: %s (%s)' % (space_name, space)

        space_page_id = response['homepage']['id']
        path_collection = fetch_page_recursively(space_page_id, space_folder, download_folder, html_template)

        # Create index file for this space
        space_index_path = '%s/index.html' % space_folder
        space_index_title = 'Index of space %s (%s)' % (space_name, space)
        space_index_content = create_html_index(path_collection)
        utils.write_html_2_file(space_index_path, space_index_title, space_index_content, html_template)


if __name__ == "__main__":
    main()
