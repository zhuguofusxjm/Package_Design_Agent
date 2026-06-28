from app.skills.prompt_utils import render

def test_render_substitutes_named_keys():
    out = render("hello {name}", name="world")
    assert out == "hello world"

def test_render_leaves_literal_json_braces_alone():
    template = 'Output JSON like {"done": true, "summary": {"x": "y"}}. Round={round}.'
    out = render(template, round=3)
    assert '{"done": true, "summary": {"x": "y"}}' in out
    assert "Round=3" in out

def test_render_ignores_unknown_placeholders():
    out = render("{a} {b}", a="1")
    assert out == "1 {b}"

def test_render_handles_multiple_substitutions():
    out = render("{a}+{b}={c}", a="1", b="2", c="3")
    assert out == "1+2=3"
