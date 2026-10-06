import unittest
from foliant.preprocessors.reindexer_utils.markdown_cleaner import MarkdownCleaner, clean_markdown


class TestMarkdownCleaner(unittest.TestCase):
    def setUp(self):
        self.cleaner = MarkdownCleaner()

    def test_clean_headers(self):
        result = self.cleaner.clean("# H1\n## H2\n### H3")
        self.assertEqual(result.strip(), "H1\n H2\n H3")

    def test_clean_bold_italic(self):
        text = "**bold** __bold__ *italic* _italic_ ~~strikethrough~~"
        result = self.cleaner.clean(text)
        self.assertEqual(result, "bold bold italic italic strikethrough")

    def test_clean_links_preserve(self):
        cleaner = MarkdownCleaner(preserve_links_text=True)
        result = cleaner.clean("[link](url)")
        self.assertEqual(result.strip(), "link")

    def test_clean_links_remove(self):
        cleaner = MarkdownCleaner(preserve_links_text=False)
        result = cleaner.clean("[link](url)")
        self.assertEqual(result.strip(), "")

    def test_clean_code_blocks_preserve(self):
        cleaner = MarkdownCleaner(preserve_code_blocks=True)
        result = cleaner.clean("```\ncode\n```")
        self.assertEqual(result.strip(), "code")

    def test_clean_code_blocks_preserve_2(self):
        cleaner = MarkdownCleaner(preserve_code_blocks=True)
        result = cleaner.clean("```\ncode_block\n```")
        self.assertEqual(result.strip(), "code_block")

    def test_clean_code_blocks_replace(self):
        cleaner = MarkdownCleaner(preserve_code_blocks=False)
        result = cleaner.clean("```\ncode\n```")
        self.assertEqual(result.strip(), "[CODE BLOCK]")

    def test_clean_inline_code(self):
        result = self.cleaner.clean("`inline code`")
        self.assertEqual(result.strip(), "inline code")

    def test_clean_inline_code_2(self):
        result = self.cleaner.clean("`inline_code`")
        self.assertEqual(result.strip(), "inline_code")

    def test_clean_lists(self):
        result = self.cleaner.clean("- item1\n- item2\n  - nested")
        self.assertIn("item1", result)
        self.assertIn("item2", result)
        self.assertIn("nested", result)

    def test_clean_checklists(self):
        result = self.cleaner.clean("- [ ] task1\n- [x] task2")
        self.assertIn("task1", result)
        self.assertIn("task2", result)

    def test_clean_blockquotes(self):
        result = self.cleaner.clean("> quote1\n> quote2")
        self.assertIn("quote1", result)
        self.assertIn("quote2", result)

    def test_clean_tables(self):
        result = self.cleaner.clean("| a | b |\n|---|---|\n| 1 | 2 |")
        self.assertIsInstance(result, str)

    def test_clean_html(self):
        result = self.cleaner.clean("<div>text</div> <span>span</span>")
        self.assertEqual(result.strip(), "text span")

    def test_clean_hugo_shortcodes(self):
        result = self.cleaner.clean("{{< shortcode >}} content {{< /shortcode >}}")
        self.assertEqual(result.strip(), "content")

    def test_clean_footnotes(self):
        result = self.cleaner.clean("text[^1]\n[^1]: footnote")
        self.assertIn("text", result)

    def test_clean_empty(self):
        result = self.cleaner.clean("")
        self.assertEqual(result, "")
        result = self.cleaner.clean(None)
        self.assertEqual(result, "")

    def test_clean_smart(self):
        result = self.cleaner.clean_smart("Hello , world ! How are you ?")
        self.assertEqual(result, "Hello, world! How are you?")

    def test_complex_markdown(self):
        text = """# Title
**bold** and *italic*
- list item
```code```"""
        result = self.cleaner.clean(text)
        self.assertIn("Title", result)
        self.assertIn("bold", result)
        self.assertIn("italic", result)
        self.assertIn("list item", result)
        self.assertIn("code", result)

    def test_clean_function(self):
        result = clean_markdown("# Test **bold**")
        self.assertEqual(result.strip(), "Test bold")

    def test_clean_extra_whitespace(self):
        result = self.cleaner.clean("   Multiple    spaces   between   words   ")
        self.assertEqual(result.strip(), "Multiple spaces between words")

    def test_clean_images_preserve(self):
        cleaner = MarkdownCleaner(preserve_links_text=True)
        result = cleaner.clean("![alt text](image.png)")
        self.assertEqual(result.strip(), "alt text")

    def test_clean_images_remove(self):
        cleaner = MarkdownCleaner(preserve_links_text=False)
        result = cleaner.clean("![alt text](image.png)")
        self.assertEqual(result.strip(), "")


if __name__ == '__main__':
    unittest.main()
