import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, ParseResult
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from internal_services.url_tags.constants import REQUEST_TIMEOUT_SECONDS, URL_HIT_RETRIES, RETRY_BACKOFF_FACTOR, \
    FORCE_STATUS_LIST, BROWSER_USER_AGENT
from internal_services.url_tags.uri_tags_manager import UriTagsManager


class UriTagsImpl(UriTagsManager):
    uri: str = None
    tags: dict = dict({
        'title': '',
        'image': '',
        'description': '',
        'url': ''
    })
    default_title: str = 'Tap to open the website url'

    logger: logging.Logger = logging.getLogger("info_logger")

    def __init__(self, uri: str):
        self.uri = uri

    def get_uri(self) -> str:
        return self.uri

    def get_tags(self) -> dict:
        return self.tags

    def set_tags(self, tags: dict):
        self.tags = tags

    def get_tags_from_uri(self) -> dict:
        validated_uri: str = UriTagsHelper.validate_uri(self.get_uri())
        uri_page: str = UriTagsHelper.get_uri_page(validated_uri)
        page_tags: dict = self._get_tags_from_page(uri_page)
        self._fill_tags(self.get_uri(), page_tags)

        return self.get_tags()

    def _get_tags_from_page(self, uri_page: str) -> dict:
        parsed_page: BeautifulSoup = UriTagsHelper.parse_html_page_data_with_beautiful_soup(uri_page)
        tags: dict = self._get_og_tags(parsed_page)
        tags = self._get_html_tags_for_empty_tags(tags, parsed_page)
        tags = self._get_default_tags_for_empty_tags(tags)

        return tags

    @staticmethod
    def _get_og_tags(parsed_page: BeautifulSoup) -> dict:
        og_tags: dict = dict({
            'title': parsed_page.find("meta", property="og:title"),
            'image': parsed_page.find("meta", property="og:image"),
            'description': parsed_page.find("meta", property="og:description")
        })
        for key in og_tags.keys():
            if og_tags[key]:
                og_tags[key] = og_tags[key].get('content')
            else:
                og_tags[key] = None

        return og_tags

    def _get_html_tags_for_empty_tags(self, tags: dict, parsed_page: BeautifulSoup) -> dict:
        if not tags['title']:
            tags['title'] = self._get_html_title_tag(parsed_page)

        if not tags['image']:
            tags['image'] = self._get_html_image_tag(parsed_page)

        if not tags['description']:
            tags['description'] = self._get_html_description_tag(parsed_page)

        return tags

    @staticmethod
    def _get_html_title_tag(parsed_page: BeautifulSoup) -> str:
        title: str = ''
        properties: list = list(['title'])
        for html_property in properties:
            title_element: BeautifulSoup.element.PageElement = parsed_page.find(html_property)
            if title_element:
                title = title_element.get_text()
                break

        return title

    @staticmethod
    def _get_html_image_tag(parsed_page: BeautifulSoup) -> str:
        image: str = ''
        properties: list = list(['image', 'logo'])
        for html_property in properties:
            image_element: BeautifulSoup.element.PageElement = parsed_page.find(html_property)
            if image_element:
                image = image_element.get_text()
                break

        return image

    @staticmethod
    def _get_html_description_tag(parsed_page: BeautifulSoup) -> str:
        description: str = ''
        properties: list = list(['description', 'details'])
        for html_property in properties:
            description_element: BeautifulSoup.element.PageElement = parsed_page.find(html_property)
            if description_element:
                description = description_element.get_text()
                break

            description_element = parsed_page.find('meta', attrs={'name': html_property})
            if description_element:
                description = description_element.unwrap()['content']
                break

        return description

    def _get_default_tags_for_empty_tags(self, tags: dict) -> dict:
        if not tags['title']:
            tags['title'] = self.default_title

        return tags

    def _fill_tags(self, uri: str, page_tags: dict):
        tags = self.get_tags()
        tags['url'] = uri
        for key in page_tags.keys():
            tags[key] = page_tags[key]
        self.set_tags(tags)

        return


class UriTagsHelper:

    @staticmethod
    def validate_uri(uri: str) -> str:
        validated_uri: str = UriTagsHelper.correct_scheme_typo(uri)
        return validated_uri

    @staticmethod
    def correct_scheme_typo(uri: str) -> str:
        uri_scheme_http: str = 'http'
        uri_scheme_https: str = 'https'

        if UriTagsHelper.check_url_scheme_http(uri):
            return UriTagsHelper.scheme_typo_corrected_uri(uri, uri_scheme_http)

        if UriTagsHelper.check_url_scheme_https(uri):
            return UriTagsHelper.scheme_typo_corrected_uri(uri, uri_scheme_https)

        return UriTagsHelper.scheme_typo_corrected_uri(uri, f'{uri_scheme_https}://')

    @staticmethod
    def check_url_scheme_http(uri: str) -> bool:
        parsed_url: ParseResult = urlparse(uri.lower())
        if parsed_url.scheme == 'http':
            return True
        return False

    @staticmethod
    def check_url_scheme_https(uri: str) -> bool:
        parsed_url: ParseResult = urlparse(uri.lower())
        if parsed_url.scheme == 'https':
            return True
        return False

    @staticmethod
    def scheme_typo_corrected_uri(uri: str, scheme: str):
        parsed_url: ParseResult = urlparse(uri)
        return parsed_url.geturl().replace(parsed_url.scheme, scheme, 1)

    @staticmethod
    def get_uri_page(uri: str) -> str:
        requests_session: requests.sessions.Session = requests.Session()
        retries: Retry = Retry(total=URL_HIT_RETRIES,
                               backoff_factor=RETRY_BACKOFF_FACTOR,
                               status_forcelist=FORCE_STATUS_LIST)

        requests_session.mount('https://', HTTPAdapter(max_retries=retries))
        headers = {
            'User-Agent': BROWSER_USER_AGENT
        }
        response: requests.models.Response = requests_session.get(uri, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        requests_session.close()

        return response.text

    @staticmethod
    def parse_html_page_data_with_beautiful_soup(uri_page: str) -> BeautifulSoup:
        return BeautifulSoup(uri_page, 'html.parser')
