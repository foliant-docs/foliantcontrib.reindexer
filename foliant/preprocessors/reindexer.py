"""
Preprocessor for Foliant documentation authoring tool.

Calls Reindexer HTTP REST API to generate a search index
based on Markdown content.
"""

import re
import json
import time
import frontmatter
from os import getenv
from pathlib import Path
from urllib import request
from urllib.error import HTTPError
from markdown import markdown
from bs4 import BeautifulSoup
from .reindexer_utils.markdown_cleaner import clean_markdown

from foliant.preprocessors.base import BasePreprocessor
from foliant.preprocessors import unescapecode


class Preprocessor(BasePreprocessor):
    defaults = {
        'reindexer_url': 'http://127.0.0.1:9088/',
        'insert_max_bytes': 0,
        'database': '',
        'namespace': '',
        'doc_type': '',
        'namespace_renamed': '',
        'namespace_type': '',
        'fulltext_config': {},
        'actions': [
            'insert_items'
        ],
        'use_chapters': True,
        'format': 'plaintext',
        'use_strip_markdown': True,
        'preserve_code_blocks': True,
        'preserve_links_text': True,
        'escape_html': True,
        'url_transform': [
            {'\/?index\.md$': '/'},  # noqa: W605
            {'\.md$': '/'},  # noqa: W605
            {'^([^\/]+)': '/\g<1>'}  # noqa: W605
        ],
        'base_url': '',
        'require_env': False,
        'targets': [],
        'split_by_headers': False,
        'split_headers_level': 2
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.options['insert_max_bytes'] < 1024:
            self.options['insert_max_bytes'] = float('inf')

        self._db_endpoint = f'{self.options["reindexer_url"].rstrip("/")}/api/v1/db'
        self.doc_type_env = getenv('REINDEXER_DOC_TYPE')

        self.logger = self.logger.getChild('reindexer')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')

    def _get_url(self, markdown_file_path: str, anchor: str = '') -> str:
        url = str(markdown_file_path.relative_to(self.working_dir))
        if self.options['base_url']:
            url = self.options['base_url'] + url
        url_transformation_rules = self.options['url_transform']

        if not isinstance(url_transformation_rules, list):
            url_transformation_rules = [url_transformation_rules]

        for url_transformation_rule in url_transformation_rules:
            for pattern, replacement in url_transformation_rule.items():
                url = re.sub(pattern, replacement, url)

        if anchor:
            url = f'{url}#{anchor}'

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

    def _split_markdown_by_headers(self, markdown_content: str) -> list:
        """
        Divides the Markdown document into sections according to the headings of the specified level.

        Returns a list of dictionaries with the keys: 'title', 'content', 'anchor', 'level'
        """
        lines = markdown_content.split('\n')
        sections = []

        header_pattern = re.compile(r'^(\#{1,6})\s+(.+?)(?:\s+\{\#(\S+)\})?\s*$')
        target_level = self.options['split_headers_level']

        current_section = {
            'title': '',
            'content': [],
            'anchor': '',
            'level': 1
        }

        def create_anchor(title: str) -> str:
            anchor = re.sub(r'[^\w\u0400-\u04FF\-]', '-', title.lower())
            anchor = re.sub(r'-+', '-', anchor).strip('-')
            return anchor

        def finalize_section():
            if current_section and len(current_section['content']):
                sections.append({
                    'title': current_section['title'],
                    'content': '\n'.join(current_section['content']).strip(),
                    'anchor': current_section['anchor'],
                    'level': current_section['level']
                })

        for line in lines:
            header_match = header_pattern.match(line)

            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                custom_anchor = header_match.group(3)
                anchor = custom_anchor or create_anchor(title)

                if level == 1:
                    current_section = {
                        'title': title,
                        'anchor': '',
                        'content': [],
                        'level': 1
                    }
                    finalize_section()
                if level == target_level:
                    finalize_section()
                    current_section = {
                        'title': title,
                        'content': [],
                        'anchor': anchor,
                        'level': level
                    }
                else:
                    current_section['content'].append(line)
            else:
                current_section['content'].append(line)

        finalize_section()

        return sections

    def _process_content(self, markdown_content: str, file_path: Path) -> list:
        """
        Processes the contents of the file, dividing it into sections if necessary.
        Returns a list of items to index.
        """
        elements = []

        if self.options['split_by_headers']:
            self.logger.debug(f'Splitting document by headers (level {self.options["split_headers_level"]})')
            sections = self._split_markdown_by_headers(markdown_content)
            self.logger.debug(f'Document split into {len(sections)} sections')

            for section in sections:
                elements.append({
                    'url': self._get_url(file_path, section['anchor']),
                    'title': section['title'],
                    'content': section['content'],
                    'metadata': {
                        'original_title': section.get('original_title', ''),
                        'section_level': section.get('level', 0),
                        'source_file': str(file_path),
                        'is_section': True
                    }
                })

        else:
            elements.append({
                'url': self._get_url(file_path),
                'title': self._get_title(markdown_content) or Path(file_path).stem,
                'content': markdown_content,
                'metadata': {
                    'source_file': str(file_path),
                    'is_section': False
                }
            })

        return elements

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
            self.logger.error(error_message)
            raise RuntimeError(error_message)

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
            self.logger.error(error_message)
            raise RuntimeError(error_message)

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
            self.logger.error(error_message)
            raise RuntimeError(error_message)

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
            self.logger.error(error_message)
            raise RuntimeError(error_message)

        return None

    def _rename_namespace(self) -> None:
        request_url = (
            f'{self._db_endpoint}/{self.options["database"]}/namespaces/{self.options["namespace"]}'
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
            self.logger.error(error_message)
            raise RuntimeError(error_message)

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
                    "name": "doc_type",
                    "json_paths": [
                        "doc_type"
                    ],
                    "field_type": "string",
                    "index_type": "-"
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
                        "content",
                        "doc_type",
                        "url"
                    ],
                    "field_type": "composite",
                    "index_type": "text",
                    "config": self.options['fulltext_config']
                }
            ]
        }

        request_url = f'{self._db_endpoint}/{self.options["database"]}/namespaces'

        max_retries = self.options.get('create_namespace_retries', 3)
        retry_delay_ms = self.options.get('create_namespace_retry_delay_ms', 1000)

        for attempt in range(max_retries):
            self.logger.debug(f'Creating namespace, attempt {attempt + 1}/{max_retries}')

            response = self._http_request(
                request_url,
                'POST',
                {'Content-Type': 'application/json; charset=utf-8'},
                json.dumps(namespace_definition, ensure_ascii=False).encode('utf-8')
            )

            response_data = json.loads(response['data'].decode('utf-8'))

            if response['status'] == 200:
                self.logger.debug('Namespace created')
                return None

            if response['status'] == 500 and attempt < max_retries - 1:
                self.logger.warning(f'Got 500 error, retrying in {retry_delay_ms} ms...')
                time.sleep(retry_delay_ms / 1000.0)
            elif response['status'] == 400 and response_data.get(
                'description', ''
            ) == f'Namespace \'{self.options["namespace"]}\' already exists':
                self.logger.debug('Namespace already exists')
                return None
            else:
                error_message = f'Failed to create namespace: {response_data}'
                self.logger.error(error_message)
                raise RuntimeError(error_message)

    def _check_build_req(self, file_path):
        """Check if file contains not_build: true in frontmatter"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)

            # Check for not_build: true
            if post.metadata.get('not_build') is True:
                return False, "contains not_build: true - build skipped"
            return True, "passed validation"
        except Exception as e:
            return False, f"Error reading file: {e}"

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

            is_build_req, message = self._check_build_req(markdown_file_path)
            if not is_build_req:
                self.logger.debug(f'File {markdown_file_path} {message}')
                continue

            with open(markdown_file_path, encoding='utf8') as markdown_file:
                markdown_content = markdown_file.read()

            if markdown_content:
                if self.config.get('escape_code', False):
                    self.logger.debug(
                        'Since escape_code mode is on, applying the unescape to the file content'
                    )
                    markdown_content = unescapecode.Preprocessor(
                        self.context,
                        self.logger,
                        self.quiet,
                        self.debug
                    ).unescape(markdown_content)

                # We get the elements (sections) for indexing
                elements = self._process_content(markdown_content, markdown_file_path)

                for element in elements:
                    url = element['url']
                    title = element['title']
                    content = element['content']
                    doc_type = "untyped"
                    if not self.options['doc_type'] and self.doc_type_env:
                        doc_type = self.doc_type_env
                    elif self.options['doc_type'] != '':
                        doc_type = self.options['doc_type']
                    elif self.context.get('config', {}).get('title'):
                        doc_type = self.context['config']['title']

                    # HTML/plaintext
                    if self.options['format'] == 'html' or self.options['format'] == 'plaintext':
                        html_content = markdown(content)

                        if self.options['format'] == 'plaintext':
                            if self.options.get('use_strip_markdown', True):
                                content = clean_markdown(
                                    content,
                                    preserve_code_blocks=self.options.get('preserve_code_blocks', True),
                                    preserve_links_text=self.options.get('preserve_links_text', True)
                                )

                                title = clean_markdown(
                                    title,
                                    preserve_code_blocks=self.options.get('preserve_code_blocks', True),
                                    preserve_links_text=self.options.get('preserve_links_text', True)
                                )
                            else:
                                soup = BeautifulSoup(html_content, 'lxml')
                                soup = BeautifulSoup(content, 'lxml')

                                for non_text_node in soup(['style', 'script']):
                                    non_text_node.extract()

                                content = soup.get_text()

                                if self.options['escape_html']:
                                    if title:
                                        title = self._escape_html(title)

                                    content = self._escape_html(content)
                        else:
                            content = html_content

                    self.logger.debug(f'Adding new item, URL: {url}, title: {title}')

                    def _prepare_item(url: str, title: str, content: str, doc_type: str) -> bytes:
                        return json.dumps(
                            {
                                'url': url,
                                'title': title,
                                'content': content,
                                'doc_type': doc_type
                            },
                            ensure_ascii=False
                        ).encode('utf-8')

                    item = _prepare_item(url, title, content, doc_type)

                    if self.options['insert_max_bytes'] < float('inf'):
                        item_size = len(item)

                        if item_size > self.options['insert_max_bytes']:
                            self.logger.warning(
                                f'Item size exceeds limit per request: {item_size} bytes, URL: {url}'
                            )
                            continue

                        if body_size + item_size > self.options['insert_max_bytes']:
                            self.logger.debug(
                                f'Size of items in this request: {body_size} bytes. '
                                f'Creating new request.'
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
                self.logger.error(error_message)
                raise RuntimeError(error_message)

            items_updated = response_data.get('updated', None)

            if items_updated:
                self.logger.debug(f'Items updated: {items_updated}')

        return None

    def apply(self):
        self.logger.info('Applying preprocessor')

        envvar = 'FOLIANT_REINDEXER'

        if not self.options['require_env'] or getenv(envvar) is not None:
            self.logger.debug(
                f'Allowed targets: {self.options["targets"]}, '
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
