from pkh.governance.audit import AuditLog


def test_audit_log(tmp_path):
    path = str(tmp_path / "audit.jsonl")
    audit = AuditLog(path=path)
    audit.log("ingest", actor="test", resource="git://repo")
    audit.log("query", actor="test", resource="how does X work?")
    entries = audit.list(limit=10)
    assert len(entries) == 2
    assert audit.verify_chain() is True
