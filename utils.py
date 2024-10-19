import re
from pathlib import Path
from itertools import takewhile

class Markdown:

    @staticmethod
    def extract_content_from_markdown(markdown_text: str, title: str) -> str:
        content = ''
        found = False
        found_title_level = 0
        for line in markdown_text.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                line_title = re.sub('#\\s*', '', line)
                current_title_level = len(list(takewhile(lambda c: c == '#', line)))
                if line_title == title:
                    found = True
                    found_title_level = current_title_level
                    continue
                elif found and current_title_level <= found_title_level:
                    break
            if found:
                content += line + '\n'
        return content.strip()

    @staticmethod
    def extract_content_from_markdown_file(file_path: Path, title: str) -> str:
        with open(file_path, 'r') as file:
            markdown_text = file.read()
        return Markdown.extract_content_from_markdown(markdown_text, title)
