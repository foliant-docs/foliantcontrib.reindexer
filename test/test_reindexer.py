import logging
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch, MagicMock

from foliant_test.preprocessor import PreprocessorTestFramework

logging.disable(logging.CRITICAL)


class TestReindexerBasic(TestCase):
    def setUp(self):
        self.ptf = PreprocessorTestFramework('reindexer')
        self.ptf.context['project_path'] = Path('.')
        self.ptf.options = {
            'reindexer_url': 'http://localhost:9088/',
            'database': 'test_db',
            'namespace': 'test_namespace',
            'actions': ['insert_items'],
            'use_chapters': True,
            'format': 'plaintext'
        }

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_insert_items(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 1}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        input_map = {
            'index.md': '# Test Page\n\nContent',
            'chapter1.md': '# Chapter 1\n\nContent'
        }
        self.ptf.config['chapters'] = ['index.md', 'chapter1.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_split_by_headers(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 2}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['split_by_headers'] = True
        self.ptf.options['split_headers_level'] = 2

        input_map = {
            'index.md': '# Main\n\n## Section 1\nContent 1\n\n## Section 2\nContent 2'
        }
        self.ptf.config['chapters'] = ['index.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_drop_database(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"description": "Database dropped"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['actions'] = ['drop_database']
        input_map = {'index.md': '# Test'}
        self.ptf.config['chapters'] = ['index.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_create_database(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"created": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['actions'] = ['create_database']
        input_map = {'index.md': '# Test'}
        self.ptf.config['chapters'] = ['index.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_drop_namespace(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"description": "Namespace dropped"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['actions'] = ['drop_namespace']
        input_map = {'index.md': '# Test'}
        self.ptf.config['chapters'] = ['index.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_truncate_namespace(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"truncated": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['actions'] = ['truncate_namespace']
        input_map = {'index.md': '# Test'}
        self.ptf.config['chapters'] = ['index.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_create_namespace(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"created": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['actions'] = ['create_namespace']
        input_map = {'index.md': '# Test'}
        self.ptf.config['chapters'] = ['index.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_not_build_frontmatter(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 0}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        input_map = {
            'index.md': '---\nnot_build: true\n---\n# Skipped',
            'chapter1.md': '# Chapter 1\nContent'
        }
        self.ptf.config['chapters'] = ['index.md', 'chapter1.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_use_chapters_false(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 3}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['use_chapters'] = False
        input_map = {
            'index.md': '# Index',
            'docs/page1.md': '# Page 1',
            'docs/page2.md': '# Page 2'
        }

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_html_format(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 1}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['format'] = 'html'
        input_map = {'index.md': '# Test\n\n**Bold**'}
        self.ptf.config['chapters'] = ['index.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_insert_max_bytes_limit(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 2}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['insert_max_bytes'] = 500
        large_content = "# Large\n\n" + "x" * 1000

        input_map = {
            'index.md': large_content,
            'chapter1.md': '# Chapter 1\n\n' + "y" * 500
        }
        self.ptf.config['chapters'] = ['index.md', 'chapter1.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_doc_type_from_options(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 1}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['doc_type'] = 'custom_doc_type'
        input_map = {'index.md': '# Test'}
        self.ptf.config['chapters'] = ['index.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_url_transform(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 1}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['url_transform'] = [{'\.md$': '.html'}]   # noqa: W605
        self.ptf.options['base_url'] = 'https://example.com/'

        input_map = {'docs/index.md': '# Test'}
        self.ptf.config['chapters'] = ['docs/index.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_target_filtering(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 1}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['targets'] = ['pdf']
        self.ptf.context['target'] = 'pdf'
        input_map = {'index.md': '# Test'}
        self.ptf.config['chapters'] = ['index.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_target_mismatch(self, mock_urlopen):
        self.ptf.options['targets'] = ['pdf']
        self.ptf.context['target'] = 'html'
        input_map = {'index.md': '# Test'}

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )
        mock_urlopen.assert_not_called()

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_require_env_var_set(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 1}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.options['require_env'] = True
        input_map = {'index.md': '# Test'}
        self.ptf.config['chapters'] = ['index.md']

        with patch('foliant.preprocessors.reindexer.getenv') as mock_getenv:
            mock_getenv.return_value = 'true'
            self.ptf.test_preprocessor(
                input_mapping=input_map,
                expected_mapping=input_map,
            )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_require_env_var_not_set(self, mock_urlopen):
        self.ptf.options['require_env'] = True
        input_map = {'index.md': '# Test'}

        with patch('foliant.preprocessors.reindexer.getenv') as mock_getenv:
            mock_getenv.return_value = None
            self.ptf.test_preprocessor(
                input_mapping=input_map,
                expected_mapping=input_map,
            )
        mock_urlopen.assert_not_called()

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_empty_file_skipped(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 1}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        input_map = {
            'index.md': '',
            'chapter1.md': '# Chapter 1\nContent'
        }
        self.ptf.config['chapters'] = ['index.md', 'chapter1.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_nested_chapters(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 3}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.ptf.config['chapters'] = [
            'index.md',
            {'Getting Started': ['install.md', 'quickstart.md']},
            {'Advanced': {'Config': 'config.md'}}
        ]

        input_map = {
            'index.md': '# Index',
            'install.md': '# Install',
            'quickstart.md': '# Quickstart',
            'config.md': '# Config'
        }

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )

    @patch('foliant.preprocessors.reindexer.request.urlopen')
    def test_unicode_content(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"updated": 1}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        input_map = {
            'index.md': '# Русский заголовок\n\nСодержимое на русском\n\n## Заголовок\n\nТекст'
        }
        self.ptf.config['chapters'] = ['index.md']

        self.ptf.test_preprocessor(
            input_mapping=input_map,
            expected_mapping=input_map,
        )
