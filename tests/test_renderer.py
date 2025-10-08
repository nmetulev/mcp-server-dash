from renderer import FieldSpec, get_path, render_section, render_table


def test_get_path_found_and_missing():
    data = {"a": {"b": {"c": 123}}}
    assert get_path(data, "a.b.c") == 123
    assert get_path(data, "a.x") is None
    assert get_path({}, "a") is None


def test_render_section_basic_and_empty():
    data = {"title": "Hello", "meta": {"count": 2}}
    specs = [
        FieldSpec("Title", "title", "📄"),
        FieldSpec("Count", "meta.count", "#"),
    ]
    out = render_section("Header", specs, data)
    assert out.startswith("Header\n")
    assert "📄 Title: Hello" in out
    assert "# Count: 2" in out

    # When nothing renders, expect empty string
    empty = render_section("Header", [FieldSpec("X", "missing")], data)
    assert empty == ""


def test_render_table_formats_rows():
    data = {"mime": "text/plain", "size": 10}
    specs = [
        FieldSpec("MIME", "mime", "🔧"),
        FieldSpec("Size", "size"),
    ]
    table = render_table(specs, data)
    assert table.startswith("| Field | Value |")
    assert "| 🔧 MIME | text/plain |" in table
    assert "| Size | 10 |" in table
