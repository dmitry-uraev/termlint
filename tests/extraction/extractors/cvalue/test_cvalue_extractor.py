from termlint.extraction.extractors.cvalue import CValueExtractor


async def test_extract_returns_entities_in_heuristic_mode():
    extractor = CValueExtractor(
        use_ling_filter=False,
        min_length=2,
        max_length=2,
        min_freq=1,
        threshold=0.0,
    )

    text = "machine learning improves machine learning systems"
    results = [entity async for entity in extractor._extract(text)]

    assert results
    assert any(entity.text == "machine learning" for entity in results)


async def test_extract_respects_threshold():
    extractor = CValueExtractor(
        use_ling_filter=False,
        min_length=2,
        max_length=2,
        min_freq=1,
        threshold=10.0,
    )

    text = "machine learning improves machine learning systems"
    results = [entity async for entity in extractor._extract(text)]

    assert results == []
