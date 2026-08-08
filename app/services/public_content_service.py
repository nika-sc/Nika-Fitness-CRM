"""Public docs/blog/updates content provider for landing pages."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path
import re


DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
BLOG_DIR = DOCS_DIR / "blog"
UPDATES_DIR = DOCS_DIR / "updates"


@dataclass
class PublicEntry:
    slug: str
    title: str
    summary: str
    published_on: str
    body_markdown: str


class PublicContentService:
    @staticmethod
    def docs_sections() -> list[dict]:
        base = 'https://github.com/nika-sc/Nika_Fitness_CRM/blob/master/'
        return [
            {
                'title': 'Полное руководство пользователя',
                'path': 'docs/USER_GUIDE.md',
                'url': f'{base}docs/USER_GUIDE.md',
                'button': 'Открыть USER_GUIDE',
                'summary': 'Разделы по ролям, ресепшену, расписанию, ЛК клиента и отчётам.',
            },
            {
                'title': 'Пошаговый сценарий рабочего дня',
                'path': 'docs/USER_WALKTHROUGH.md',
                'url': f'{base}docs/USER_WALKTHROUGH.md',
                'button': 'Открыть WALKTHROUGH',
                'summary': 'Маршрут администратора и ресепшена: от входа до финальной сверки дня.',
            },
            {
                'title': 'Деплой и эксплуатация',
                'path': 'docs/DEPLOY.md',
                'url': f'{base}docs/DEPLOY.md',
                'button': 'Открыть DEPLOY',
                'summary': 'Облако, Linux (Docker/VPS) и Windows: установка, reverse proxy, бэкапы.',
            },
            {
                'title': 'Open Source checklist',
                'path': 'docs/OPEN_SOURCE_CHECKLIST.md',
                'url': f'{base}docs/OPEN_SOURCE_CHECKLIST.md',
                'button': 'Открыть CHECKLIST',
                'summary': 'Проверки перед открытием репозитория, публикацией и первым релизом.',
            },
        ]

    @staticmethod
    def blog_posts() -> list[PublicEntry]:
        return PublicContentService._read_entries(BLOG_DIR)

    @staticmethod
    def updates() -> list[PublicEntry]:
        return PublicContentService._read_entries(UPDATES_DIR)

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

        def close_ul() -> None:
            nonlocal in_ul
            if in_ul:
                html_chunks.append("</ul>")
                in_ul = False

        for raw in lines:
            line = raw.rstrip()
            if not line:
                close_ul()
                continue
            if line.startswith("### "):
                close_ul()
                html_chunks.append(f"<h3>{escape(line[4:])}</h3>")
                continue
            if line.startswith("## "):
                close_ul()
                html_chunks.append(f"<h2>{escape(line[3:])}</h2>")
                continue
            if line.startswith("# "):
                close_ul()
                html_chunks.append(f"<h1>{escape(line[2:])}</h1>")
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
        escaped = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2" target="_blank" rel="noopener">\1</a>',
            escaped,
        )
        return escaped
