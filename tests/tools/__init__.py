# Makes 'tests.tools' a proper Python package so that individual test modules
# resolve to unique dotted paths (e.g. tests.tools.gmail.test_integration)

__all__: list[str] = [] 