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


import os
import shutil
import sys
from typing import Dict, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

import utils
import settings


CONFLUENCE_DUMPER_VERSION = "1.0.0"
TITLE_OUTPUT = "C O N F L U E N C E   D U M P E R  %s" % CONFLUENCE_DUMPER_VERSION


def error_print(*args, **kwargs) -> None:
    """
    Wrapper for the print function which leads to stderr outputs.

    :param args: Not necessary.
    :param kwargs: Not necessary.
    """
    print(*args, file=sys.stderr, **kwargs)


def derive_downloaded_file_name(download_url: str) -> Optional[str]:
    """
    Generates the name of a downloaded/exported file.

    Examples:
        /download/attachments/524291/peak.jpeg?version=1&modificationDate=1459521827579&api=v2
            => <download_folder>/524291_attachments_peak.jpeg
        /download/thumbnails/524291/Harvey.jpg?version=1&modificationDate=1459521827579&api=v2
            => <download_folder>/524291_thumbnails_Harvey.jpg

    :param download_url: Confluence download URL which is used to derive the downloaded file name.
    :returns: Derived file name; if derivation is not possible, None is returned.
    """
    if "/download/" in download_url:
        download_url_parts = download_url.split("/")
        download_page_id = download_url_parts[3]
        download_file_type = download_url_parts[2]

        # Remove GET parameters
        last_question_mark_index = download_url_parts[4].rfind("?")
        download_original_file_name = download_url_parts[4][:last_question_mark_index]

        return f"{download_page_id}_{download_file_type}_{download_original_file_name}"
    elif "/rest/documentConversion/latest/conversion/thumbnail/" in download_url:
        file_id = download_url.split("/rest/documentConversion/latest/conversion/thumbnail/")[1][0:-2]
        return f"generated_preview_{file_id}.jpg"
    else:
        return None


def provide_unique_file_name(
    duplicate_file_names: Dict[str, int],
    file_matching: Dict[str, str],
    file_title: str,
    is_folder: bool = False,
    explicit_file_extension: Optional[str] = None,
) -> str:
    """
    Provides an unique AND sanitized file name for a given page title.
    Confluence does not allow the same page title in one particular space
    but collisions are possible after filesystem sanitization.

    :param duplicate_file_names: A dict in the structure {'<sanitized filename>': amount of duplicates}
    :param file_matching: A dict in the structure {'<file title>': '<used offline filename>'}
    :param file_title: File title which is used to generate the unique file name
    :param is_folder: (optional) Flag which states whether the file is a folder
    :param explicit_file_extension: (optional) Explicitly set file extension (e.g. 'html')
    """
    if file_title in file_matching:
        file_name = file_matching[file_title]
    else:
        file_name = utils.sanitize_for_filename(file_title)

        if is_folder:
            file_extension = None
        elif explicit_file_extension:
            file_extension = explicit_file_extension
        else:
            if "." in file_name:
                file_name, file_extension = file_name.rsplit(".", 1)
            else:
                file_extension = None

        if file_name in duplicate_file_names:
            duplicate_file_names[file_name] += 1
            file_name = f"{file_name}_{duplicate_file_names[file_name]}"
        else:
            duplicate_file_names[file_name] = 0

        if file_extension:
            file_name += f".{file_extension}"

        file_matching[file_title] = file_name
    return file_name


def handle_html_references(
    html_content: str, page_duplicate_file_names: Dict[str, int], page_file_matching: Dict[str, str], depth: int = 0
) -> str:
    """Repairs links in the page contents with local links.

    Args:
        html_content: Confluence HTML content.
        page_duplicate_file_names: A dict in the structure {'<sanitized filename>': amount of duplicates}
        page_file_matching: A dict in the structure {'<page title>': '<used offline filename>'}
        depth: (optional) Hierarchy depth of the handled Confluence page.

    Returns:
        Fixed HTML content.
    """
    if not html_content:
        return ""
    try:
        html_tree = BeautifulSoup(html_content, "html.parser")
    except Exception:
        print(f"{'   ' * (depth + 1)}WARNING: Could not parse HTML content of last page. DL as is. ")
        return html_content

    handle_links_to_pages(html_tree, page_duplicate_file_names, page_file_matching)
    handle_links_when_page_ids_used(html_tree)
    handle_attachment_links(html_tree)
    handle_image_links(html_tree)

    return str(html_tree)


def handle_links_to_pages(html_tree, page_duplicate_file_names, page_file_matching):
    link_elements = html_tree.select('a[href*="/display/"]')
    for link_element in link_elements:
        if not link_element.get("class"):
            print(f"LINK - {link_element['href']}")
            page_title = get_page_title(link_element)
            decoded_page_title = utils.decode_url(page_title)
            offline_link = provide_unique_file_name(
                page_duplicate_file_names, page_file_matching, decoded_page_title, explicit_file_extension="html"
            )
            link_element["href"] = utils.encode_url(offline_link)


def handle_links_when_page_ids_used(html_tree):
    link_elements = html_tree.select('a[href*="/pages/viewpage.action?pageId="]')
    for link_element in link_elements:
        if not link_element.get("class"):
            page_id = link_element["href"].split("/pages/viewpage.action?pageId=")[1]
            offline_link = f"{utils.sanitize_for_filename(page_id)}.html"
            link_element["href"] = utils.encode_url(offline_link)


def handle_attachment_links(html_tree):
    link_elements = html_tree.select("a.confluence-embedded-file")
    for link_element in link_elements:
        file_url = link_element["href"]
        file_name = derive_downloaded_file_name(file_url)
        relative_file_path = f"{settings.DOWNLOAD_SUB_FOLDER}/{file_name}"
        link_element["href"] = relative_file_path


def handle_image_links(html_tree):
    img_elements = html_tree.select(
        'img[src*="/download/"], img[src*="/rest/documentConversion/latest/conversion/thumbnail/"]'
    )
    for img_element in img_elements:
        file_url = img_element["src"]
        file_name = derive_downloaded_file_name(file_url)
        relative_file_path = f"{settings.DOWNLOAD_SUB_FOLDER}/{file_name}"
        img_element["src"] = relative_file_path
        if "alt" not in img_element.attrs:
            img_element["alt"] = relative_file_path


def get_page_title(link_element):
    try:
        page_title = link_element["href"].split("/")[4]
    except IndexError:
        page_title = link_element["href"].split("/")[3]
    return page_title.replace("+", " ")


def download_file(clean_url, download_folder, downloaded_file_name, depth=0, error_output=True):
    """Downloads a specific file.

    :param clean_url: Decoded URL to the file.
    :param download_folder: Folder to place the downloaded file in.
    :param downloaded_file_name: File name to save the download to.
    :param depth: (optional) Hierarchy depth of the handled Confluence page.
    :param error_output: (optional) Set to False if you do not want to see any error outputs
    :returns: Path to the downloaded file.
    """
    downloaded_file_path = "%s/%s" % (download_folder, downloaded_file_name)

    # Download file if it does not exist yet
    if not os.path.exists(downloaded_file_path):
        absolute_download_url = "%s%s" % (settings.CONFLUENCE_BASE_URL, clean_url)
        # print using f strings
        print(f"{(depth + 1) * '   '}DOWNLOAD: {downloaded_file_name}")
        try:
            utils.http_download_binary_file(
                absolute_download_url,
                downloaded_file_path,
                auth=settings.HTTP_AUTHENTICATION,
                headers=settings.HTTP_CUSTOM_HEADERS,
                verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
                proxies=settings.HTTP_PROXIES,
            )

        except utils.ConfluenceException as e:
            if error_output:
                error_print("%sERROR: %s" % ("\t" * (depth + 2), e))
            else:
                print("%sWARNING: %s" % ("\t" * (depth + 2), e))

    return downloaded_file_path


def download_attachment(
    download_url,
    download_folder,
    attachment_id,
    attachment_duplicate_file_names,
    attachment_file_matching,
    depth=0,
):
    """ Repairs links in the page contents with local links.

    :param download_url: Confluence download URL.
    :param download_folder: Folder to place downloaded files in.
    :param attachment_id: ID of the attachment to download.
    :param attachment_duplicate_file_names: A dict in the structure {'<sanitized attachment filename>': amount of \
                                            duplicates}
    :param attachment_file_matching: A dict in the structure {'<attachment title>': '<used offline filename>'}
    :param depth: (optional) Hierarchy depth of the handled Confluence page.
    :returns: Path and name of the downloaded file as dict.
    """
    clean_url = utils.decode_url(download_url)
    downloaded_file_name = derive_downloaded_file_name(clean_url)
    downloaded_file_name = provide_unique_file_name(
        attachment_duplicate_file_names, attachment_file_matching, downloaded_file_name
    )
    downloaded_file_path = download_file(download_url, download_folder, downloaded_file_name, depth=depth)

    # Download the thumbnail as well if the attachment is an image
    clean_thumbnail_url = clean_url.replace("/attachments/", "/thumbnails/", 1)
    downloaded_thumbnail_file_name = derive_downloaded_file_name(clean_thumbnail_url)
    downloaded_thumbnail_file_name = provide_unique_file_name(
        attachment_duplicate_file_names, attachment_file_matching, downloaded_thumbnail_file_name
    )
    if utils.is_file_format(downloaded_thumbnail_file_name, settings.CONFLUENCE_THUMBNAIL_FORMATS):
        # TODO: Confluence creates thumbnails always as PNGs but does not change the file extension to .png.
        download_file(
            clean_thumbnail_url,
            download_folder,
            downloaded_thumbnail_file_name,
            depth=depth,
            error_output=False,
        )

    # Download the image preview as well if Confluence generated one for the attachment
    if utils.is_file_format(downloaded_file_name, settings.CONFLUENCE_GENERATED_PREVIEW_FORMATS):
        clean_preview_url = "/rest/documentConversion/latest/conversion/thumbnail/%s/1" % attachment_id
        downloaded_preview_file_name = derive_downloaded_file_name(clean_preview_url)
        downloaded_preview_file_name = provide_unique_file_name(
            attachment_duplicate_file_names, attachment_file_matching, downloaded_preview_file_name
        )
        download_file(clean_preview_url, download_folder, downloaded_preview_file_name, depth=depth, error_output=False)

    return {"file_name": downloaded_file_name, "file_path": downloaded_file_path}


def create_html_attachment_index(attachments):
    """Creates a HTML list for a list of attachments.

    :param attachments: List of attachments.
    :returns: Attachment list as HTML.
    """
    html_content = "\n\n<h2>Attachments</h2>"
    if len(attachments) > 0:
        html_content += "<ul>\n"
        for attachment in attachments:
            relative_file_path = "/".join(attachment["file_path"].split("/")[2:])
            relative_file_path = utils.encode_url(relative_file_path)
            html_content += '\t<li><a href="%s">%s</a></li>\n' % (relative_file_path, attachment["file_name"])
        html_content += "</ul>\n"
    return html_content


def process_attachments(response, download_folder, attachment_duplicate_file_names, attachment_file_matching, depth=0):
    path_collection = {"child_attachments": []}
    skip_types = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov"]

    for attachment in response["results"]:
        download_url = attachment["_links"]["download"]
        attachment_id = attachment["id"][3:]

        parsed_url = urlparse(download_url)
        path = parsed_url.path

        if any(path.lower().endswith(extension) for extension in skip_types):
            continue

        attachment_info = download_attachment(
            download_url,
            download_folder,
            attachment_id,
            attachment_duplicate_file_names,
            attachment_file_matching,
            depth=depth + 1,
        )

        path_collection["child_attachments"].append(attachment_info)

    return path_collection


def fetch_page_recursively(
    page_id,
    folder_path,
    download_folder,
    html_template,
    space: str,
    depth=0,
    page_duplicate_file_names=None,
    page_file_matching=None,
    attachment_duplicate_file_names=None,
    attachment_file_matching=None,
):
    """ Fetches a Confluence page and its child pages (with referenced downloads).

    :param page_id: Confluence page id.
    :param folder_path: Folder to place downloaded pages in.
    :param download_folder: Folder to place downloaded files in.
    :param html_template: HTML template used to export Confluence pages.
    :param depth: (optional) Hierarchy depth of the handled Confluence page.
    :param page_duplicate_file_names: A dict in the structure {'<sanitized page filename>': amount of duplicates}
    :param page_file_matching: A dict in the structure {'<page title>': '<used offline filename>'}
    :param attachment_duplicate_file_names: A dict in the structure {'<sanitized attachment filename>': amount of \
                                            duplicates}
    :param attachment_file_matching: A dict in the structure {'<attachment title>': '<used offline filename>'}
    :returns: Information about downloaded files (pages, attachments, images, ...) as a dict (None for exceptions)
    """
    if not page_duplicate_file_names:
        page_duplicate_file_names = {}
    if not page_file_matching:
        page_file_matching = {}
    if not attachment_duplicate_file_names:
        attachment_duplicate_file_names = {}
    if not attachment_file_matching:
        attachment_file_matching = {}

    page_url = "%s/rest/api/content/%s?expand=children.page,children.attachment,body.view.value" % (
        settings.CONFLUENCE_BASE_URL,
        page_id,
    )
    web_url = f"https://boomtrain.atlassian.net/wiki/spaces/{space}/pages/{page_id}/"
    try:
        response = utils.http_get(
            page_url,
            auth=settings.HTTP_AUTHENTICATION,
            headers=settings.HTTP_CUSTOM_HEADERS,
            verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
            proxies=settings.HTTP_PROXIES,
        )
        page_content = response["body"]["view"]["value"]

        page_title = response["title"]
        print("%sPAGE: %s (%s)" % ("\t" * (depth + 1), page_title, page_id))

        # Construct unique file name
        file_name = provide_unique_file_name(
            page_duplicate_file_names, page_file_matching, page_title, explicit_file_extension="html"
        )

        # Remember this file and all children
        path_collection = {"file_path": file_name, "page_title": page_title, "child_pages": [], "child_attachments": []}

        # Download attachments of this page
        # TODO: Outsource/Abstract the following two while loops because of much duplicate code.
        page_url = "%s/rest/api/content/%s/child/attachment?limit=25" % (settings.CONFLUENCE_BASE_URL, page_id)
        counter = 0
        while page_url:
            print(f"URL: {page_url}")
            response = utils.http_get(
                page_url,
                auth=settings.HTTP_AUTHENTICATION,
                headers=settings.HTTP_CUSTOM_HEADERS,
                verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
                proxies=settings.HTTP_PROXIES,
            )
            counter += len(response["results"])

            # Process and download attachments
            path_collection = process_attachments(
                response, download_folder, attachment_duplicate_file_names, attachment_file_matching
            )

            if "next" in response["_links"]:
                page_url = f"{settings.CONFLUENCE_BASE_URL}{response['_links']['next']}"
                print(f"URL: {page_url}")
            else:
                page_url = None

        # Export HTML file
        page_content = handle_html_references(
            page_content,
            page_duplicate_file_names,
            page_file_matching,
            depth=depth + 1,
        )
        page_content = str(page_content)
        file_path = "%s/%s" % (folder_path, file_name)
        page_content += create_html_attachment_index(path_collection["child_attachments"])
        utils.write_html_2_file(file_path, page_title, page_content, html_template, web_url)

        # Save another file with page id which forwards to the original one
        id_file_path = "%s/%s.html" % (folder_path, page_id)
        id_file_page_title = "Forward to page %s" % page_title
        original_file_link = utils.encode_url(utils.sanitize_for_filename(file_name))
        id_file_page_content = settings.HTML_FORWARD_MESSAGE % (original_file_link, page_title)
        id_file_forward_header = '<meta http-equiv="refresh" content="0; url=%s" />' % original_file_link
        utils.write_html_2_file(
            id_file_path,
            id_file_page_title,
            id_file_page_content,
            html_template,
            web_url,
            additional_headers=[id_file_forward_header],
        )

        # Iterate through all child pages
        page_url = "%s/rest/api/content/%s/child/page?limit=25" % (settings.CONFLUENCE_BASE_URL, page_id)
        counter = 0
        while page_url:
            response = utils.http_get(
                page_url,
                auth=settings.HTTP_AUTHENTICATION,
                headers=settings.HTTP_CUSTOM_HEADERS,
                verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
                proxies=settings.HTTP_PROXIES,
            )
            counter += len(response["results"])
            for child_page in response["results"]:
                paths = fetch_page_recursively(
                    child_page["id"],
                    folder_path,
                    download_folder,
                    html_template,
                    space,
                    depth=depth + 1,
                    page_duplicate_file_names=page_duplicate_file_names,
                    page_file_matching=page_file_matching,
                )
                if paths and "child_pages" in list(paths.keys()):
                    path_collection["child_pages"].append(paths)

            if "next" in list(response["_links"].keys()):
                page_url = response["_links"]["next"]
                page_url = "%s%s" % (settings.CONFLUENCE_BASE_URL, page_url)
            else:
                page_url = None
        return path_collection

    except utils.ConfluenceException as e:
        error_print("%sERROR: %s" % ("\t" * (depth + 1), e))
        return None


def create_html_index(index_content):
    """Creates an HTML index (mainly to navigate through the exported pages).

    :param index_content: Dictionary which contains file paths, page titles and their children recursively.
    :returns: Content index as HTML.
    """
    if "file_path" in list(index_content.keys()):
        file_path = utils.encode_url(index_content["file_path"])
    else:
        return False
    page_title = index_content["page_title"]
    page_children = index_content["child_pages"]

    file_path = str(file_path)
    page_title = str(page_title)

    html_content = '<a href="%s">%s</a>' % (utils.sanitize_for_filename(file_path), page_title)  # todo drose

    if len(page_children) > 0:
        html_content += "<ul>\n"
        for child in page_children:
            html_content += "\t<li>%s</li>\n" % create_html_index(child)
        html_content += "</ul>\n"

    return html_content


def print_welcome_output():
    """Displays software title and some license information"""
    print("\n\t %s" % TITLE_OUTPUT)
    print("\t %s\n" % ("=" * len(TITLE_OUTPUT)))
    print("... a Python project to export spaces, pages and attachments\n")
    print("Copyright (c) Siemens AG, 2016\n")
    print("Authors:")
    print("  Thomas Maier <thomas.tm.maier@siemens.com>\n")
    print("This work is licensed under the terms of the MIT license.")
    print("See the LICENSE.md file in the top-level directory.\n\n")


def print_finished_output():
    """Displays exit message (for successful export)"""
    print("\n\nFinished!\n")


def main():
    """Main function to start the confluence-dumper."""

    # Welcome output
    print_welcome_output()
    # Delete old export
    if os.path.exists(settings.EXPORT_FOLDER):
        shutil.rmtree(settings.EXPORT_FOLDER)
    os.makedirs(settings.EXPORT_FOLDER)

    # Read HTML template
    template_file = open(settings.TEMPLATE_FILE)
    html_template = template_file.read()

    # Fetch all spaces if spaces were not configured via settings
    if len(settings.SPACES_TO_EXPORT) > 0:
        spaces_to_export = settings.SPACES_TO_EXPORT
    else:
        spaces_to_export = []
        page_url = "%s/rest/api/space?limit=25" % settings.CONFLUENCE_BASE_URL
        while page_url:
            response = utils.http_get(
                page_url,
                auth=settings.HTTP_AUTHENTICATION,
                headers=settings.HTTP_CUSTOM_HEADERS,
                verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
                proxies=settings.HTTP_PROXIES,
            )
            for space in response["results"]:
                spaces_to_export.append(space["key"])

            if "next" in list(response["_links"].keys()):
                page_url = response["_links"]["next"]
                page_url = "%s%s" % (settings.CONFLUENCE_BASE_URL, page_url)
            else:
                page_url = None

    print("Exporting %d space(s): %s\n" % (len(spaces_to_export), ", ".join(spaces_to_export)))

    # Export spaces
    space_counter = 0
    duplicate_space_names = {}
    space_matching = {}
    for space in spaces_to_export:
        space_counter += 1

        # Create folders for this space
        space_folder_name = provide_unique_file_name(duplicate_space_names, space_matching, space, is_folder=True)
        space_folder = "%s/%s" % (settings.EXPORT_FOLDER, space_folder_name)
        try:
            os.makedirs(space_folder)
            download_folder = "%s/%s" % (space_folder, settings.DOWNLOAD_SUB_FOLDER)
            os.makedirs(download_folder)

            space_url = "%s/rest/api/space/%s?expand=homepage" % (settings.CONFLUENCE_BASE_URL, space)
            response = utils.http_get(
                space_url,
                auth=settings.HTTP_AUTHENTICATION,
                headers=settings.HTTP_CUSTOM_HEADERS,
                verify_peer_certificate=settings.VERIFY_PEER_CERTIFICATE,
                proxies=settings.HTTP_PROXIES,
            )
            space_name = response["name"]

            print("SPACE (%d/%d): %s (%s)" % (space_counter, len(spaces_to_export), space_name, space))

            if "homepage" in list(response.keys()):
                space_page_id = response["homepage"]["id"]
            else:
                space_page_id = -1

            path_collection = fetch_page_recursively(space_page_id, space_folder, download_folder, html_template, space)

            if path_collection:
                # Create index file for this space
                space_index_path = "%s/index.html" % space_folder
                space_index_title = "Index of Space %s (%s)" % (space_name, space)
                space_index_content = create_html_index(path_collection)
                if space_index_content:
                    utils.write_html_2_file(space_index_path, space_index_title, space_index_content, html_template)
        except utils.ConfluenceException as e:
            error_print("ERROR: %s" % e)
        except OSError:
            print(
                "WARNING: The space %s has been exported already. Maybe you mentioned it twice in the settings" % space
            )

    # Finished output
    print_finished_output()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        error_print("ERROR: Keyboard Interrupt.")
        sys.exit(1)
