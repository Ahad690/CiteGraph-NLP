import respx

from citegraph.input.url_resolver import URLIdentifierResolver


def test_resolve_doi_from_url_text():
    resolver = URLIdentifierResolver()

    query = resolver.resolve_from_url_text("https://doi.org/10.1038/s41591-023-02702-z")

    assert query is not None
    assert query.query_type == "doi"
    assert query.value == "10.1038/s41591-023-02702-z"


@respx.mock
async def test_resolve_doi_from_page_metadata():
    resolver = URLIdentifierResolver()
    respx.get("https://www.nature.com/articles/s41591-023-02702-z").respond(
        status_code=200,
        text="""
        <html>
          <head>
            <meta name="citation_doi" content="10.1038/s41591-023-02702-z">
            <meta name="citation_title" content="A deep learning system for predicting time to progression">
          </head>
        </html>
        """,
    )

    query = await resolver.resolve("https://www.nature.com/articles/s41591-023-02702-z")

    assert query is not None
    assert query.query_type == "doi"
    assert query.value == "10.1038/s41591-023-02702-z"


@respx.mock
async def test_resolve_title_from_page_metadata_when_doi_missing():
    resolver = URLIdentifierResolver()
    respx.get("https://example.org/article-with-title-only").respond(
        status_code=200,
        text="""
        <html>
          <head>
            <meta name="citation_title" content="Predicting diabetic retinopathy progression with deep learning">
          </head>
        </html>
        """,
    )

    query = await resolver.resolve("https://example.org/article-with-title-only")

    assert query is not None
    assert query.query_type == "title"
    assert query.value == "Predicting diabetic retinopathy progression with deep learning"


def test_doi_extraction_strips_publisher_view_segments():
    """A DOI embedded mid-path is followed by a view segment (/full, /pdf,
    /abs) that the greedy DOI character class swallows, producing an
    unresolvable identifier like 10.3389/fcomp.2024.1387354/full."""
    resolver = URLIdentifierResolver()

    cases = {
        "https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2024.1387354/full":
            "10.3389/fcomp.2024.1387354",
        "https://onlinelibrary.wiley.com/doi/abs/10.1002/spy2.12345":
            "10.1002/spy2.12345",
        "https://pubs.acs.org/doi/pdf/10.1021/acs.jcim.0c00001":
            "10.1021/acs.jcim.0c00001",
        "https://www.tandfonline.com/doi/full/10.1080/21642583.2024.2321381":
            "10.1080/21642583.2024.2321381",
    }
    for url, expected in cases.items():
        query = resolver.resolve_from_url_text(url)
        assert query is not None, f"no identifier extracted from {url}"
        assert query.query_type == "doi"
        assert query.value == expected, f"{url} -> {query.value}"


def test_doi_with_legitimate_slashes_is_preserved():
    """Only trailing view segments are trimmed; the prefix/suffix core and any
    genuine extra slashes in a DOI must survive."""
    from citegraph.utils.ids import IdCanonicalizer

    for doi in (
        "10.1000/123/456",
        "10.1016/j.cell.2020.02.052",
        "10.1002/(sici)1099-1085(199908/09)13:12",
    ):
        assert IdCanonicalizer.strip_doi_view_suffix(doi) == doi
