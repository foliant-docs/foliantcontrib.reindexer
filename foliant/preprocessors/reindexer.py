'''
Preprocessor for Foliant documentation authoring tool.

Calls Reindexer HTTP REST API to generate a search index
based on Markdown content.
'''

import re
import json
from os import getenv
from pathlib import Path
from urllib import request
from urllib.error import HTTPError
from markdown import markdown
from bs4 import BeautifulSoup

from foliant.preprocessors.base import BasePreprocessor


class Preprocessor(BasePreprocessor):
    defaults = {
        'reindexer_url': 'http://127.0.0.1:9088/',
        'insert_max_bytes': 0,
        'database': '',
        'namespace': '',
        'namespace_renamed': '',
        'fulltext_config': {},
        'actions': [
            'drop_database',
            'create_database',
            'create_namespace',
            'insert_items'
        ],
        'use_chapters': True,
        'format': 'plaintext',
        'escape_html': True,
        'url_transform': [
            {'\/?index\.md$': '/'},
            {'\.md$': '/'},
            {'^([^\/]+)': '/\g<1>'}
        ],
        'require_env': False,
        'targets': []
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.options['insert_max_bytes'] < 1024:
            self.options['insert_max_bytes'] = float('inf')

        self._db_endpoint = f'{self.options["reindexer_url"].rstrip("/")}/api/v1/db'

        self.logger = self.logger.getChild('reindexer')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')

    def _get_url(self, markdown_file_path: str) -> str:
        url = str(markdown_file_path.relative_to(self.working_dir))
        url_transformation_rules = self.options['url_transform']

        if not isinstance(url_transformation_rules, list):
            url_transformation_rules = [url_transformation_rules]

        for url_transformation_rule in url_transformation_rules:
            for pattern, replacement in url_transformation_rule.items():
                url = re.sub(pattern, replacement, url)

        return url

    def _get_title(self, markdown_content: str) -> str:
        headings_found = re.search(
            r'^\#{1,6}\s+(.+?)(?:\s+\{\#\S+\})?\s*$',
            markdown_content,
            flags=re.MULTILINE
        )

        if headings_found:
            return headings_found.group(1)

        return ''

    def _get_chapters_paths(self) -> list:
        def _recursive_process_chapters(chapters_subset):
            if isinstance(chapters_subset, dict):
                processed_chapters_subset = {}

                for key, value in chapters_subset.items():
                    processed_chapters_subset[key] = _recursive_process_chapters(value)

            elif isinstance(chapters_subset, list):
                processed_chapters_subset = []

                for item in chapters_subset:
                    processed_chapters_subset.append(_recursive_process_chapters(item))

            elif isinstance(chapters_subset, str):
                if chapters_subset.endswith('.md'):
                    chapters_paths.append(self.working_dir / chapters_subset)

                processed_chapters_subset = chapters_subset

            else:
                processed_chapters_subset = chapters_subset

            return processed_chapters_subset

        chapters_paths = []
        _recursive_process_chapters(self.config['chapters'])

        self.logger.debug(f'Chapters files paths: {chapters_paths}')

        return chapters_paths

    def _escape_html(self, content: str) -> str:
        return content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def _http_request(
        self,
        request_url: str,
        request_method: str = 'GET',
        request_headers: dict or None = None,
        request_data: bytes or None = None
    ) -> dict:
        http_request = request.Request(request_url, method=request_method)

        if request_headers:
            http_request.headers = request_headers

        if request_data:
            http_request.data = request_data

        try:
            with request.urlopen(http_request) as http_response:
                response_status = http_response.getcode()
                response_headers = http_response.info()
                response_data = http_response.read()

        except HTTPError as http_response_not_ok:
            response_status = http_response_not_ok.getcode()
            response_headers = http_response_not_ok.info()
            response_data = http_response_not_ok.read()

        return {
            'status': response_status,
            'headers': response_headers,
            'data': response_data
        }

    def _drop_database(self) -> None:
        request_url = f'{self._db_endpoint}/{self.options["database"]}'

        self.logger.debug(f'Requesting Reindexer API to drop database, URL: {request_url}')

        response = self._http_request(
            request_url,
            'DELETE'
        )

        response_data = json.loads(response['data'].decode('utf-8'))

        self.logger.debug(f'Response received, status: {response["status"]}')
        self.logger.debug(f'Response headers: {response["headers"]}')
        self.logger.debug(f'Response data: {response_data}')

        if response['status'] == 200:
            self.logger.debug('Database dropped')

        elif response['status'] == 400 and response_data.get(
            'description', ''
        ) == f'Database {self.options["database"]} not found':
            self.logger.debug('Database does not exist')

        else:
            error_message = 'Failed to drop database'
            self.logger.error(f'{error_message}')
            raise RuntimeError(f'{error_message}')

        return None

    def _create_database(self) -> None:
        request_url = self._db_endpoint

        self.logger.debug(f'Requesting Reindexer API to create database, URL: {request_url}')

        response = self._http_request(
            request_url,
            'POST',
            {
                'Content-Type': 'application/json; charset=utf-8'
            },
            json.dumps(
                {'name': self.options['database']},
                ensure_ascii=False
            ).encode('utf-8')
        )

        response_data = json.loads(response['data'].decode('utf-8'))

        self.logger.debug(f'Response received, status: {response["status"]}')
        self.logger.debug(f'Response headers: {response["headers"]}')
        self.logger.debug(f'Response data: {response_data}')

        if response['status'] == 200:
            self.logger.debug('Database created')

        elif response['status'] == 400 and response_data.get(
            'description', ''
        ) == 'Database already exists':
            self.logger.debug('Database already exists')

        else:
            error_message = 'Failed to create database'
            self.logger.error(f'{error_message}')
            raise RuntimeError(f'{error_message}')

        return None

    def _drop_namespace(self) -> None:
        request_url = f'{self._db_endpoint}/{self.options["database"]}/namespaces/{self.options["namespace"]}'

        self.logger.debug(f'Requesting Reindexer API to drop namespace, URL: {request_url}')

        response = self._http_request(
            request_url,
            'DELETE'
        )

        response_data = json.loads(response['data'].decode('utf-8'))

        self.logger.debug(f'Response received, status: {response["status"]}')
        self.logger.debug(f'Response headers: {response["headers"]}')
        self.logger.debug(f'Response data: {response_data}')

        if response['status'] == 200:
            self.logger.debug('Namespace dropped')

        elif response['status'] == 404 and response_data.get(
            'description', ''
        ) == f'Namespace \'{self.options["namespace"]}\' does not exist':
            self.logger.debug('Namespace does not exist')

        else:
            error_message = 'Failed to drop namespace'
            self.logger.error(f'{error_message}')
            raise RuntimeError(f'{error_message}')

        return None

    def _truncate_namespace(self) -> None:
        request_url = (
            f'{self._db_endpoint}/{self.options["database"]}/namespaces/{self.options["namespace"]}/truncate'
        )

        self.logger.debug(f'Requesting Reindexer API to truncate namespace, URL: {request_url}')

        response = self._http_request(
            request_url,
            'DELETE'
        )

        response_data = json.loads(response['data'].decode('utf-8'))

        self.logger.debug(f'Response received, status: {response["status"]}')
        self.logger.debug(f'Response headers: {response["headers"]}')
        self.logger.debug(f'Response data: {response_data}')

        if response['status'] == 200:
            self.logger.debug('Namespace truncated')

        elif response['status'] == 400 and response_data.get(
            'description', ''
        ) == f'Namespace \'{self.options["namespace"]}\' does not exist':
            self.logger.debug('Namespace does not exist')

        else:
            error_message = 'Failed to truncate namespace'
            self.logger.error(f'{error_message}')
            raise RuntimeError(f'{error_message}')

        return None

    def _rename_namespace(self) -> None:
        request_url = (
            f'{self._db_endpoint}/{self.options["database"]}/namespaces/{self.options["namespace"]}' +
            f'/rename/{self.options["namespace_renamed"]}'
        )

        self.logger.debug(f'Requesting Reindexer API to rename namespace, URL: {request_url}')

        response = self._http_request(request_url)

        response_data = json.loads(response['data'].decode('utf-8'))

        self.logger.debug(f'Response received, status: {response["status"]}')
        self.logger.debug(f'Response headers: {response["headers"]}')
        self.logger.debug(f'Response data: {response_data}')

        if response['status'] == 200:
            self.logger.debug('Namespace renamed')

        else:
            error_message = 'Failed to rename namespace'
            self.logger.error(f'{error_message}')
            raise RuntimeError(f'{error_message}')

        return None

    def _create_namespace(self) -> None:
        namespace_definition = {
            "name": self.options['namespace'],
            "storage": {
                "enabled": True,
                "drop_on_file_format_error": True,
                "create_if_missing": True
            },
            "indexes": [
                {
                    "name": "url",
                    "json_paths": [
                        "url"
                    ],
                    "field_type": "string",
                    "index_type": "hash",
                    "is_pk": True
                },
                {
                    "name": "title",
                    "json_paths": [
                        "title"
                    ],
                    "field_type": "string",
                    "index_type": "-"
                },
                {
                    "name": "content",
                    "json_paths": [
                        "content"
                    ],
                    "field_type": "string",
                    "index_type": "-"
                },
                {
                    "name": "indexed_content",
                    "json_paths": [
                        "title",
                        "content"
                    ],
                    "field_type": "composite",
                    "index_type": "text",
                    "config": self.options['fulltext_config']
                }
            ]
        }

        request_url = f'{self._db_endpoint}/{self.options["database"]}/namespaces'

        self.logger.debug(f'Requesting Reindexer API to create database, URL: {request_url}')

        response = self._http_request(
            request_url,
            'POST',
            {
                'Content-Type': 'application/json; charset=utf-8'
            },
            json.dumps(
                namespace_definition,
                ensure_ascii=False
            ).encode('utf-8')
        )

        response_data = json.loads(response['data'].decode('utf-8'))

        self.logger.debug(f'Response received, status: {response["status"]}')
        self.logger.debug(f'Response headers: {response["headers"]}')
        self.logger.debug(f'Response data: {response_data}')

        if response['status'] == 200:
            self.logger.debug('Namespace created')

        elif response['status'] == 400 and response_data.get(
            'description', ''
        ) == f'Namespace \'{self.options["namespace"]}\' already exists':
            self.logger.debug('Namespace already exists')

        else:
            error_message = 'Failed to create namespace'
            self.logger.error(f'{error_message}')
            raise RuntimeError(f'{error_message}')

        return None

    def _insert_items(self) -> None:
        if self.options['use_chapters']:
            self.logger.debug('Only files mentioned in chapters will be indexed')

            markdown_files_paths = self._get_chapters_paths()

        else:
            self.logger.debug('All files of the project will be indexed')

            markdown_files_paths = self.working_dir.rglob('*.md')

        requests_bodies = []
        request_body = b''
        body_size = 0

        for markdown_file_path in markdown_files_paths:
            self.logger.debug(f'Processing the file: {markdown_file_path}')

            with open(markdown_file_path, encoding='utf8') as markdown_file:
                markdown_content = markdown_file.read()

            if markdown_content:
                url = self._get_url(markdown_file_path)
                title = self._get_title(markdown_content)

                if self.options['format'] == 'html' or self.options['format'] == 'plaintext':
                    self.logger.debug(f'Converting source Markdown content to: {self.options["format"]}')

                    content = markdown(markdown_content)

                    if self.options['format'] == 'plaintext':
                        soup = BeautifulSoup(content, 'lxml')

                        for non_text_node in soup(['style', 'script']):
                            non_text_node.extract()

                        content = soup.get_text()

                        if self.options['escape_html']:
                            self.logger.debug('Escaping HTML syntax')

                            if title:
                                title = self._escape_html(title)

                            content = self._escape_html(content)

                else:
                    self.logger.debug('Leaving source Markdown content unchanged')

                    content = markdown_content

                self.logger.debug(f'Adding new item, URL: {url}, title: {title}')

                def _prepare_item(url: str, title: str, content: str) -> bytes:
                    return json.dumps(
                        {
                            'url': url,
                            'title': title,
                            'content': content
                        },
                        ensure_ascii=False
                    ).encode('utf-8')

                item = _prepare_item(url, title, content)

                self.logger.debug(
                    'Maximum data size of items that can be inserted with a single API request: ' +
                    f'{self.options["insert_max_bytes"]} bytes'
                )

                if self.options['insert_max_bytes'] < float('inf'):
                    item_size = len(item)

                    if item_size > self.options['insert_max_bytes']:
                        self.logger.warning(
                            f'Item size exceeds limit per request: {item_size} bytes, URL key: {url}'
                        )

                        encoded_content = content.encode('utf-8')
                        content_size = len(encoded_content)
                        remaining_item_size = item_size - content_size

                        if remaining_item_size >= self.options['insert_max_bytes']:
                            self.logger.warning(
                                'Item size excluding content also exceeds limit: ' +
                                f'{prepared_item_remaining_size} bytes, skipping'
                            )

                            continue

                        else:
                            trimmed_content_max_size = self.options['insert_max_bytes'] - remaining_item_size

                            self.logger.warning(
                                f'Content must be trimmed to maximum {trimmed_content_max_size} bytes'
                            )

                            trailing_byte_index = trimmed_content_max_size

                            while trailing_byte_index > 0 and not (
                                (encoded_content[trailing_byte_index] & 0xC0) != 0x80
                            ):
                                trailing_byte_index -= 1

                            trimmed_content = encoded_content[:trailing_byte_index].decode('utf-8')

                            if not trimmed_content:
                                self.logger.warning(
                                    'Content can only be trimmed to an empty string, skipping'
                                )

                                continue

                            item = _prepare_item(url, title, trimmed_content)
                            item_size = len(item)

                    if body_size + item_size > self.options['insert_max_bytes']:
                        self.logger.debug(
                            f'Size of items that are included into a single request: {body_size} bytes, ' +
                            f'current item size: {item_size} bytes. ' +
                            f'One more request will be used'
                        )

                        requests_bodies.append(request_body)
                        request_body = b''
                        body_size = 0

                    body_size += item_size

                request_body += item

            else:
                self.logger.debug('It seems that the file has no content, skipping')

        if request_body:
            requests_bodies.append(request_body)

        requests_count = len(requests_bodies)

        request_url = f'{self._db_endpoint}/{self.options["database"]}/namespaces/{self.options["namespace"]}/items'
        self.logger.debug(
            f'Performing {requests_count} request(s) to Reindexer API to insert new items, URL: {request_url}'
        )

        for index, request_body in enumerate(requests_bodies):
            self.logger.debug(f'Request {index + 1} of {requests_count}')

            response = self._http_request(
                request_url,
                'POST',
                {
                    'Content-Type': 'application/json; charset=utf-8'
                },
                request_body
            )

            response_data = json.loads(response['data'].decode('utf-8'))

            self.logger.debug(f'Response received, status: {response["status"]}')
            self.logger.debug(f'Response headers: {response["headers"]}')
            self.logger.debug(f'Response data: {response_data}')

            if response['status'] != 200:
                error_message = 'Failed to insert new content items into namespace'
                self.logger.error(f'{error_message}')
                raise RuntimeError(f'{error_message}')

            items_updated = response_data.get('updated', None)

            if items_updated:
                self.logger.debug(f'Items updated: {items_updated}')

        return None

    def apply(self):
        self.logger.info('Applying preprocessor')

        envvar = 'FOLIANT_REINDEXER'

        if not self.options['require_env'] or getenv(envvar) is not None:
            self.logger.debug(
                f'Allowed targets: {self.options["targets"]}, ' +
                f'current target: {self.context["target"]}'
            )

            if not self.options['targets'] or self.context['target'] in self.options['targets']:
                actions = self.options['actions']

                if not isinstance(self.options['actions'], list):
                    actions = [actions]

                for action in actions:
                    self.logger.debug(f'Applying action: {action}')

                    if action == 'drop_database':
                        self._drop_database()

                    elif action == 'create_database':
                        self._create_database()

                    elif action == 'drop_namespace':
                        self._drop_namespace()

                    elif action == 'truncate_namespace':
                        self._truncate_namespace()

                    elif action == 'rename_namespace':
                        self._rename_namespace()

                    elif action == 'create_namespace':
                        self._create_namespace()

                    elif action == 'insert_items':
                        self._insert_items()

                    else:
                        self.logger.debug('Unknown action, skipping')

        else:
            self.logger.debug(f'Environment variable {envvar} is not set, skipping')

        self.logger.info('Preprocessor applied')
