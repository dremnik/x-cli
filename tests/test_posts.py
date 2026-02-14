from xcli.cmd.posts import _render_post_markdown, _render_post_text


def test_render_post_markdown_prefers_article_text_and_title() -> None:
    post = {
        "id": "2013045749580259680",
        "author_name": "Heinrich",
        "author_username": "arscontexta",
        "created_at": "2026-01-19T00:28:01.000Z",
        "text": "https://t.co/example",
        "article": {
            "title": "obsidian + claude code 101",
            "plain_text": "First paragraph\n \nSecond paragraph",
            "entities": {
                "code": [
                    {
                        "language": "markdown",
                        "code": "# Example",
                    }
                ]
            },
        },
        "public_metrics": {
            "like_count": 10,
            "reply_count": 2,
        },
    }

    rendered = _render_post_markdown(post, url="https://x.com/arscontexta/status/2013045749580259680")

    assert rendered.startswith("---\n")
    assert 'author_name: "Heinrich"' in rendered
    assert 'author_username: "arscontexta"' in rendered
    assert 'url: "https://x.com/arscontexta/status/2013045749580259680"' in rendered
    assert "metrics:" in rendered
    assert "  like_count: 10" in rendered
    assert "  reply_count: 2" in rendered
    assert "# obsidian + claude code 101" in rendered
    assert "First paragraph\n```markdown\n# Example\n```\nSecond paragraph" in rendered


def test_render_post_text_uses_note_tweet_before_short_text() -> None:
    post = {
        "author_username": "arscontexta",
        "created_at": "2026-01-19T00:28:01.000Z",
        "text": "https://t.co/example",
        "note_tweet": {"text": "Long form note text"},
    }

    rendered = _render_post_text(post, url="https://x.com/arscontexta/status/2013045749580259680")

    assert "author: @arscontexta" in rendered
    assert "Long form note text" in rendered
    assert "https://t.co/example" not in rendered


def test_render_post_markdown_preserves_plain_text_lines() -> None:
    post = {
        "id": "123",
        "author_name": "Example",
        "author_username": "example",
        "created_at": "2026-01-01T00:00:00.000Z",
        "article": {
            "title": "Example",
            "plain_text": (
                "a research vault might emphasize:\n"
                "source tracking and citations\n"
                "literature notes\n"
                "claim verification"
            ),
        },
    }

    rendered = _render_post_markdown(post, url="https://x.com/example/status/123")

    assert "a research vault might emphasize:" in rendered
    assert "source tracking and citations" in rendered
    assert "literature notes" in rendered
    assert "claim verification" in rendered
    assert "- source tracking and citations" not in rendered
    assert "## literature notes" not in rendered


def test_render_post_markdown_does_not_promote_headings() -> None:
    post = {
        "id": "123",
        "author_name": "Example",
        "author_username": "example",
        "created_at": "2026-01-01T00:00:00.000Z",
        "article": {
            "title": "Example",
            "plain_text": (
                "the pattern is:\n"
                "first point\n"
                "second point\n"
                "what this could be\n"
                "a work vault might emphasize:\n"
                "capture first\n"
                "structure later"
            ),
        },
    }

    rendered = _render_post_markdown(post, url="https://x.com/example/status/123")

    assert "first point" in rendered
    assert "second point" in rendered
    assert "what this could be" in rendered
    assert "## what this could be" not in rendered


def test_render_post_markdown_rehydrates_urls_and_lists_attachments_for_normal_post() -> None:
    post = {
        "id": "2021974597256843341",
        "author_name": "aditya",
        "author_username": "adxtyahq",
        "created_at": "2026-02-12T15:48:05.000Z",
        "text": "Read this https://t.co/abc",
        "entities": {
            "urls": [
                {
                    "start": 10,
                    "end": 23,
                    "url": "https://t.co/abc",
                    "expanded_url": "https://example.com/full",
                    "display_url": "example.com/full",
                }
            ]
        },
        "raw": {
            "data": {
                "attachments": {"media_keys": ["3_123"]},
            },
            "includes": {
                "media": [
                    {
                        "media_key": "3_123",
                        "type": "photo",
                        "url": "https://pbs.twimg.com/media/example.png",
                    }
                ]
            },
        },
    }

    rendered = _render_post_markdown(post, url="https://x.com/adxtyahq/status/2021974597256843341")

    assert "Read this https://example.com/full" in rendered
    assert "## Attachments" in rendered
    assert "- photo `3_123`: [source](https://pbs.twimg.com/media/example.png)" in rendered
