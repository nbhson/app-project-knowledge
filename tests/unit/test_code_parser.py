from pkh.engines.code_intelligence.parser import CodeParser


def test_parse_python_class():
    parser = CodeParser()
    content = """
class PaymentService:
    def charge(self, amount: float) -> bool:
        return True
"""
    out = parser.parse("test.py", content)
    assert len(out.entities) >= 1
    names = [e.name for e in out.entities]
    assert any("PaymentService" in n for n in names)


def test_parse_imports():
    parser = CodeParser()
    content = "import os\nfrom typing import List\nclass Foo: pass"
    out = parser.parse("foo.py", content)
    rel_types = [r.type for r in out.relationships]
    assert "DEPENDS_ON" in rel_types


def test_parse_many():
    parser = CodeParser()
    from pkh.engines.ingestion.models import RawItem

    items = [
        RawItem(
            item_id="a.py",
            source_type="GIT",
            title="a.py",
            content="class A: pass",
            content_type="python",
        ),
        RawItem(
            item_id="b.py",
            source_type="GIT",
            title="b.py",
            content="def foo(): pass",
            content_type="python",
        ),
    ]
    out = parser.parse_many(items)
    assert len(out.entities) >= 2
