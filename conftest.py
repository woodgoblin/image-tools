"""
Configuration for pytest to enable human-readable test names.

This uses the technique from https://medium.com/@dsmd90/python-displayname-analog-from-java-6a1d1ad3c468
to display test docstrings as test names in reports.
"""


def pytest_collection_modifyitems(items):
    """Modify test items to use docstrings as human-readable test names."""
    for item in items:
        docstring = item.function.__doc__
        if docstring:
            summary = next(
                (
                    line.strip()
                    for line in docstring.strip().splitlines()
                    if line.strip()
                ),
                None,
            )
            if summary:
                if hasattr(item, "callspec"):
                    # For parameterized tests, preserve parameter id from the original nodeid
                    start = item.nodeid.find("[")
                    parameter_part = item.nodeid[start:] if start != -1 else ""
                    item._nodeid = summary + parameter_part
                else:
                    item._nodeid = summary
