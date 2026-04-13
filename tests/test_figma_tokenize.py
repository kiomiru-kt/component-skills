import figma_tokenize


def test_classes_are_importable():
    assert hasattr(figma_tokenize, "FigmaClient")
    assert hasattr(figma_tokenize, "VariableResolver")
    assert hasattr(figma_tokenize, "NodeScanner")
    assert hasattr(figma_tokenize, "TokenNamer")
    assert hasattr(figma_tokenize, "TokenBuilder")
