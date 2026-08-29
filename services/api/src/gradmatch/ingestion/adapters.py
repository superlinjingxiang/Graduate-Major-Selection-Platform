from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol

import httpx
from django.utils import timezone


@dataclass(frozen=True)
class FetchContext:
    source_key: str
    base_url: str
    rate_limit_per_minute: int


@dataclass(frozen=True)
class FetchResult:
    body: bytes
    source_url: str
    content_type: str
    fetched_at: datetime


@dataclass(frozen=True)
class ParsedItem:
    external_id: str
    title: str


class SourceAdapter(Protocol):
    key: str

    def fetch(self, context: FetchContext) -> FetchResult: ...

    def parse(self, result: FetchResult) -> Iterable[ParsedItem]: ...


class DuplicateAdapterKeyError(ValueError):
    pass


class UnknownAdapterKeyError(KeyError):
    pass


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        if adapter.key in self._adapters:
            raise DuplicateAdapterKeyError(f"An adapter is already registered for '{adapter.key}'.")
        self._adapters[adapter.key] = adapter

    def get(self, key: str) -> SourceAdapter:
        try:
            return self._adapters[key]
        except KeyError as error:
            raise UnknownAdapterKeyError(f"No adapter is registered for '{key}'.") from error


class HttpxFetcher:
    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch(self, context: FetchContext) -> FetchResult:
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = client.get(context.base_url)
            response.raise_for_status()
        content_type = response.headers.get("content-type", "text/html").split(";", maxsplit=1)[0]
        return FetchResult(
            body=response.content,
            source_url=str(response.url),
            content_type=content_type,
            fetched_at=timezone.now(),
        )


class PlaywrightFetcher:
    def fetch(self, context: FetchContext) -> FetchResult:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(context.base_url, wait_until="networkidle")
                return FetchResult(
                    body=page.content().encode("utf-8"),
                    source_url=page.url,
                    content_type="text/html",
                    fetched_at=timezone.now(),
                )
            finally:
                browser.close()


class SmokeFixtureAdapter:
    key = "smoke-fixture"
    fixture_path = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "sample-source.html"

    def fetch(self, context: FetchContext) -> FetchResult:
        return FetchResult(
            body=self.fixture_path.read_bytes(),
            source_url=context.base_url,
            content_type="text/html",
            fetched_at=timezone.now(),
        )

    def parse(self, result: FetchResult) -> Iterable[ParsedItem]:
        parser = _FixtureArticleParser()
        parser.feed(result.body.decode("utf-8"))
        return tuple(parser.items)


class _FixtureArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[ParsedItem] = []
        self._current_id: str | None = None
        self._title_fragments: list[str] = []
        self._inside_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "article":
            self._current_id = dict(attrs).get("data-record-id")
            self._title_fragments = []
        elif tag == "h2" and self._current_id is not None:
            self._inside_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2":
            self._inside_title = False
        elif tag == "article" and self._current_id is not None:
            self.items.append(
                ParsedItem(
                    external_id=self._current_id, title="".join(self._title_fragments).strip()
                )
            )
            self._current_id = None
            self._title_fragments = []

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self._title_fragments.append(data)


default_adapter_registry = AdapterRegistry()
default_adapter_registry.register(SmokeFixtureAdapter())
