import re


class MarkdownCleaner:
    """Class for removing Markdown syntax from text"""

    def __init__(self, preserve_code_blocks=False, preserve_links_text=True):
        """
        Initialize the Markdown cleaner.

        Args:
            preserve_code_blocks: Whether to preserve code block contents (otherwise replace with [CODE])
            preserve_links_text: Whether to preserve link text (otherwise remove completely)
        """
        self.preserve_code_blocks = preserve_code_blocks
        self.preserve_links_text = preserve_links_text
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regular expressions for optimization"""
        self.patterns = [
            # Hugo shortcodes (should be first, before other processing)
            (re.compile(r'\{\{<[^>]+>\}\}', re.DOTALL), ' '),                              # {{< shortcode >}}
            (re.compile(r'\{\{%[^%]+%\}\}', re.DOTALL), ' '),                              # {{% shortcode %}}
            (re.compile(r'\{\{[\/]?[a-zA-Z_][a-zA-Z0-9_]*\s+[^}]*\}\}', re.DOTALL), ' '),  # general shortcode case

            # Code blocks (should be before inline code)
            (re.compile(r'```(\w*)\n(.*?)\n```', re.DOTALL), self._handle_code_block),
            (re.compile(r'~~~(\w*)\n(.*?)\n~~~', re.DOTALL), self._handle_code_block),

            # HTML tags
            (re.compile(r'<[^>]+>', re.DOTALL), ''),

            # Headers
            (re.compile(r'^#{1,6}\s+', re.MULTILINE), ' '),
            (re.compile(r'^(.+?)\n[=-]{2,}\s*$', re.MULTILINE), r'\1\n'),

            # Text formatting
            (re.compile(r'\*\*(.*?)\*\*', re.DOTALL), r'\1'),              # bold **text**
            (re.compile(r'__(.*?)__', re.DOTALL), r'\1'),                  # bold __text__
            (re.compile(r'\*(.*?)\*', re.DOTALL), r'\1'),                  # italic *text*
            (re.compile(r'(?<!\w)_([^\n]*?)_(?!\w)', re.DOTALL), r'\1'),   # italic _text_
            (re.compile(r'~~(.*?)~~', re.DOTALL), r'\1'),                  # strikethrough
            (re.compile(r'`(.*?)`', re.DOTALL), r'\1'),                    # inline code

            # Links and images
            (re.compile(r'!\[(.*?)\]\([^\)]+\)', re.DOTALL), r'\1' if self.preserve_links_text else ' '),
            (re.compile(r'\[(.*?)\]\([^\)]+\)', re.DOTALL), r'\1' if self.preserve_links_text else ' '),

            # Automatic links
            (re.compile(r'<([^>]+@[^>]+)>'), r'\1'),             # email
            (re.compile(r'<((?:https?|ftp)://[^>]+)>'), r'\1'),  # URL

            # Lists
            (re.compile(r'^[\*\-\+]\s+', re.MULTILINE), ' '),
            (re.compile(r'^\[[ xX]\]\s+', re.MULTILINE), ' '),   # checklists

            # Blockquotes
            (re.compile(r'^>\s+', re.MULTILINE), ' '),
            (re.compile(r'^>{3,}\s*$', re.MULTILINE), ' '),

            # Horizontal rules
            (re.compile(r'^[\-\*\_]{3,}\s*$', re.MULTILINE), ' '),

            # Tables
            (re.compile(r'^\|[\s\-:|]+\|$', re.MULTILINE), ' '),
            (re.compile(r'^\||\|\s\-+$', re.MULTILINE), ' '),

            # Footnotes
            (re.compile(r'\[\^(\d+)\]\:?', re.MULTILINE), ' '),
            (re.compile(r'\[\^(\d+)\]', re.MULTILINE), ' '),

            # Escaped characters
            (re.compile(r'\\([\\`*_{}\[\]()#+\-.!])'), r'\1'),

            # HTML comments
            (re.compile(r'<!--.*?-->', re.DOTALL), ' '),

            # Extra spaces and empty lines
            (re.compile(r'[ \t]+', re.DOTALL), ' '),
            (re.compile(r'\n\s*\n', re.DOTALL), '\n\n'),
            (re.compile(r'^\s+|\s+$', re.MULTILINE), ' '),

            (re.compile(r'\?\?\?|\!\!\!|\?\?\?\+', re.DOTALL), ' '),
            (re.compile(r'\<anchor\>|\<\/anchor\>', re.DOTALL), ' '),
            (re.compile(r'\$\{[^\s]\}', re.DOTALL), ' '),
            (re.compile(r'\.png|\.svg|\.jpeg|\.jpg', re.DOTALL), ' '),
        ]

    def _handle_code_block(self, match):
        """Handle code block processing"""
        if self.preserve_code_blocks:
            return match.group(2)  # preserve content
        else:
            return '[CODE BLOCK]'

    def clean(self, text):
        """
        Clean text from Markdown syntax.

        Args:
            text: Original Markdown text

        Returns:
            str: Text without Markdown formatting
        """
        if not text:
            return ''

        result = text

        for pattern, replacement in self.patterns:
            if callable(replacement):
                result = pattern.sub(replacement, result)
            else:
                result = pattern.sub(replacement, result)

        # Final cleanup: remove empty lines at beginning and end
        result = result.strip()

        return result

    def clean_smart(self, text):
        """
        Smart cleaning: removes Markdown but preserves structure.
        """
        if not text:
            return ''

        # First remove all markers
        result = self.clean(text)

        # Restore some punctuation
        result = result.replace(' ,', ',')
        result = result.replace(' .', '.')
        result = result.replace(' !', '!')
        result = result.replace(' ?', '?')

        return result


# Create a global instance for simple use
_default_cleaner = None


def clean_markdown(text, preserve_code_blocks=False, preserve_links_text=True):
    """
    Quick Markdown text cleaning.

    Args:
        text: Markdown text
        preserve_code_blocks: Whether to preserve code
        preserve_links_text: Whether to preserve link text

    Returns:
        str: Cleaned text
    """
    global _default_cleaner
    if (_default_cleaner is None  # noqa: W503
            or _default_cleaner.preserve_code_blocks != preserve_code_blocks  # noqa: W503
            or _default_cleaner.preserve_links_text != preserve_links_text):  # noqa: W503
        _default_cleaner = MarkdownCleaner(preserve_code_blocks, preserve_links_text)
    return _default_cleaner.clean(text)
