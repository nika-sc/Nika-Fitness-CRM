"""Public docs/blog content provider for landing pages."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path
import re


DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
BLOG_DIR = DOCS_DIR / "blog"

_DOCS_FILES = {
    "about": ("ABOUT.md", "О проекте и установка"),
    "guide": ("USER_GUIDE.md", "Полное руководство"),
    "walkthrough": ("USER_WALKTHROUGH.md", "Сценарий рабочего дня"),
}


@dataclass
class PublicEntry:
    slug: str
    title: str
    summary: str
    published_on: str
    body_markdown: str


class PublicContentService:
    @staticmethod
    def read_docs_page(key: str) -> tuple[str, str] | None:
        """Return (heading, markdown_body) for a known docs page key."""
        meta = _DOCS_FILES.get(key)
        if not meta:
            return None
        filename, heading = meta
        path = DOCS_DIR / filename
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
        # Drop leading H1 — page template already shows heading
        lines = text.splitlines()
        if lines and lines[0].startswith("# "):
            lines = lines[1:]
            while lines and not lines[0].strip():
                lines = lines[1:]
        return heading, "\n".join(lines).strip()

    @staticmethod
    def blog_posts() -> list[PublicEntry]:
        return PublicContentService._read_entries(BLOG_DIR)

    @staticmethod
    def blog_post(slug: str) -> PublicEntry | None:
        for entry in PublicContentService.blog_posts():
            if entry.slug == slug:
                return entry
        return None

    @staticmethod
    def markdown_to_html(markdown_text: str) -> str:
        lines = markdown_text.splitlines()
        html_chunks: list[str] = []
        in_ul = False
        in_code = False
        code_lang = ""
        code_buf: list[str] = []
        table_buf: list[str] = []

        def close_ul() -> None:
            nonlocal in_ul
            if in_ul:
                html_chunks.append("</ul>")
                in_ul = False

        def flush_table() -> None:
            nonlocal table_buf
            if not table_buf:
                return
            rows = []
            for row in table_buf:
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                rows.append(cells)
            table_buf = []
            if len(rows) < 2:
                return
            # Skip separator row |---|---|
            body_rows = rows[1:]
            if body_rows and all(re.fullmatch(r":?-+:?", c or "") for c in body_rows[0]):
                body_rows = body_rows[1:]
            html_chunks.append('<div class="table-responsive"><table class="table">')
            html_chunks.append("<thead><tr>")
            for cell in rows[0]:
                html_chunks.append(f"<th>{PublicContentService._inline_markup(cell)}</th>")
            html_chunks.append("</tr></thead><tbody>")
            for row in body_rows:
                html_chunks.append("<tr>")
                for cell in row:
                    html_chunks.append(f"<td>{PublicContentService._inline_markup(cell)}</td>")
                html_chunks.append("</tr>")
            html_chunks.append("</tbody></table></div>")

        for raw in lines:
            line = raw.rstrip("\n")
            if in_code:
                if line.strip().startswith("```"):
                    escaped_code = escape("\n".join(code_buf))
                    lang_cls = f' class="language-{escape(code_lang)}"' if code_lang else ""
                    html_chunks.append(f"<pre><code{lang_cls}>{escaped_code}</code></pre>")
                    in_code = False
                    code_buf = []
                    code_lang = ""
                else:
                    code_buf.append(line)
                continue

            if line.strip().startswith("```"):
                close_ul()
                flush_table()
                in_code = True
                code_lang = line.strip()[3:].strip()
                code_buf = []
                continue

            if line.strip().startswith("|") and "|" in line.strip()[1:]:
                close_ul()
                table_buf.append(line)
                continue
            if table_buf:
                flush_table()

            line = line.rstrip()
            if not line:
                close_ul()
                continue
            if line.startswith("### "):
                close_ul()
                html_chunks.append(f"<h3>{PublicContentService._inline_markup(line[4:])}</h3>")
                continue
            if line.startswith("## "):
                close_ul()
                html_chunks.append(f"<h2>{PublicContentService._inline_markup(line[3:])}</h2>")
                continue
            if line.startswith("# "):
                close_ul()
                html_chunks.append(f"<h1>{PublicContentService._inline_markup(line[2:])}</h1>")
                continue
            if line.startswith("- "):
                if not in_ul:
                    html_chunks.append("<ul>")
                    in_ul = True
                html_chunks.append(f"<li>{PublicContentService._inline_markup(line[2:])}</li>")
                continue
            close_ul()
            html_chunks.append(f"<p>{PublicContentService._inline_markup(line)}</p>")

        close_ul()
        flush_table()
        if in_code:
            escaped_code = escape("\n".join(code_buf))
            html_chunks.append(f"<pre><code>{escaped_code}</code></pre>")
        return "\n".join(html_chunks)

    @staticmethod
    def _read_entries(folder: Path) -> list[PublicEntry]:
        if not folder.exists():
            return []
        entries: list[PublicEntry] = []
        for path in sorted(folder.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            meta, body = PublicContentService._split_frontmatter(text)
            title = meta.get("title") or path.stem
            slug = meta.get("slug") or path.stem
            summary = meta.get("summary") or ""
            published_on = meta.get("date") or date.today().isoformat()
            entries.append(
                PublicEntry(
                    slug=slug,
                    title=title,
                    summary=summary,
                    published_on=published_on,
                    body_markdown=body.strip(),
                )
            )
        entries.sort(key=lambda item: item.published_on, reverse=True)
        return entries

    @staticmethod
    def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
        if not text.startswith("---\n"):
            return {}, text
        try:
            _, fm, body = text.split("---\n", 2)
        except ValueError:
            return {}, text
        meta: dict[str, str] = {}
        for row in fm.splitlines():
            if ":" not in row:
                continue
            key, value = row.split(":", 1)
            meta[key.strip()] = value.strip()
        return meta, body

    @staticmethod
    def _inline_markup(text: str) -> str:
        escaped = escape(text)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"`([^`]+?)`", r"<code>\1</code>", escaped)

        def _link(match: re.Match[str]) -> str:
            label, href = match.group(1), match.group(2)
            external = href.startswith("http://") or href.startswith("https://") or href.startswith("mailto:")
            target = ' target="_blank" rel="noopener"' if external and not href.startswith("mailto:") else ""
            return f'<a href="{href}"{target}>{label}</a>'

        escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link, escaped)
        return escaped
