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
