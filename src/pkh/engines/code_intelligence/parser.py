"""Code parser - tree-sitter + regex fallback."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any

from pkh.utils.logging import get_logger

logger = get_logger(__name__)

# Try tree-sitter
try:
    import tree_sitter_python  # type: ignore
    from tree_sitter import Language  # type: ignore

    HAS_TREESITTER = True
    _raw_language = tree_sitter_python.language()
    # tree_sitter_python.language() returns PyCapsule in 0.20-0.25,
    # Language wrapper required; newer versions may return Language directly
    if isinstance(_raw_language, Language):
        _PY_LANGUAGE: Any = _raw_language
    else:
        _PY_LANGUAGE = Language(_raw_language)
except Exception:
    HAS_TREESITTER = False
    _PY_LANGUAGE = None


def _ast_base_to_str(node: ast.expr) -> str:
    """Return full dotted name for ast base (handles module.Class)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        cur: Any = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        else:
            # fallback: try unparse
            try:
                return ast.unparse(node)
            except Exception:
                return ".".join(reversed(parts))
        return ".".join(reversed(parts))
    if isinstance(node, ast.Subscript):
        # generic like List[int] -> keep base
        return _ast_base_to_str(node.value)
    try:
        return ast.unparse(node)  # type: ignore[attr-defined]
    except Exception:
        return getattr(node, "id", str(node))


@dataclass
class CodeEntity:
    id: str
    kind: str  # CLASS, FUNCTION, METHOD, etc
    name: str
    file_path: str
    line_start: int
    line_end: int
    signature: str = ""
    documentation: str = ""
    parents: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeRelationship:
    from_entity: str
    to_entity: str
    type: str  # DEPENDS_ON, CALLS, etc
    confidence: float = 1.0


@dataclass
class CodeKnowledgeOutput:
    entities: list[CodeEntity]
    relationships: list[CodeRelationship]
    symbol_table: dict[str, list[str]]
    errors: list[str]
    duration_seconds: float = 0.0


class PythonParser:
    """Parse Python files using tree-sitter or ast fallback."""

    def parse_file(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[CodeRelationship], list[str]]:
        errors: list[str] = []

        if HAS_TREESITTER:
            try:
                return self._parse_with_treesitter(file_path, content)
            except Exception as e:
                errors.append(f"tree-sitter failed for {file_path}: {e}")
                logger.warning(errors[-1])

        # fallback to ast + regex
        try:
            return self._parse_with_ast(file_path, content)
        except Exception as e:
            errors.append(f"ast parse failed for {file_path}: {e}")
            # regex fallback
            return self._parse_with_regex(file_path, content)

    def _parse_with_treesitter(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[CodeRelationship], list[str]]:
        from tree_sitter import Parser

        # New API: construct Parser then assign language via property
        # to avoid deprecated Language(language()) / Parser(language) patterns.
        parser = Parser()
        # tree-sitter 0.26 uses property assignment
        try:
            parser.language = _PY_LANGUAGE  # type: ignore[attr-defined]
        except Exception:
            # fallback for older bindings that require ctor arg
            parser = Parser(_PY_LANGUAGE)  # type: ignore[call-arg]

        tree = parser.parse(bytes(content, "utf8"))
        if tree is None:
            return [], [], [f"tree-sitter parse returned None for {file_path}"]
        root = tree.root_node
        entities: list[CodeEntity] = []
        relationships: list[CodeRelationship] = []
        errors: list[str] = []

        # extract imports
        imports: list[str] = []

        def walk(node, inside_class: bool = False) -> None:
            ntype = node.type
            if ntype == "import_statement":
                txt = content[node.start_byte : node.end_byte]
                imports.append(txt.strip())
            elif ntype == "import_from_statement":
                txt = content[node.start_byte : node.end_byte]
                imports.append(txt.strip())
            elif ntype == "class_definition":
                name_node = node.child_by_field_name("name")
                name = (
                    content[name_node.start_byte : name_node.end_byte] if name_node else "Unknown"
                )
                supers: list[str] = []
                super_node = node.child_by_field_name("superclasses")
                if super_node:
                    sup_txt = content[super_node.start_byte : super_node.end_byte]
                    # keep full dotted names e.g. module.Class
                    inner = sup_txt.strip()
                    if inner.startswith("(") and inner.endswith(")"):
                        inner = inner[1:-1]
                    # split by comma, keep dotted names
                    for part in inner.split(","):
                        part = part.strip()
                        if not part:
                            continue
                        m = re.search(r"[\w\.]+", part)
                        if m:
                            supers.append(m.group(0))
                sig = content[node.start_byte : node.end_byte].split(":")[0][:200]
                ent = CodeEntity(
                    id=f"{file_path}::CLASS::{name}",
                    kind="CLASS",
                    name=name,
                    file_path=file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=sig,
                    metadata={"superclasses": supers},
                )
                entities.append(ent)
                for sup in supers:
                    relationships.append(CodeRelationship(ent.id, sup, "EXTENDS"))
            elif ntype in ("function_definition", "async_function_definition"):
                name_node = node.child_by_field_name("name")
                name = (
                    content[name_node.start_byte : name_node.end_byte] if name_node else "Unknown"
                )
                # METHOD if ancestor is class (propagated via inside_class)
                kind = "METHOD" if inside_class else "FUNCTION"
                params_node = node.child_by_field_name("parameters")
                params = (
                    content[params_node.start_byte : params_node.end_byte] if params_node else "()"
                )
                sig = f"{name}{params}"
                ent = CodeEntity(
                    id=f"{file_path}::FUNC::{name}:{node.start_point[0]}",
                    kind=kind,
                    name=name,
                    file_path=file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=sig,
                )
                entities.append(ent)
            elif ntype == "decorated_definition":
                # unwrap: the actual definition is in field "definition"
                # walk will handle the inner definition via children loop,
                # but we must propagate inside_class so METHOD detection works
                # (parent of function_definition is decorated_definition, not class)
                pass

            # recurse: propagate inside_class for children of class_definition
            next_inside = inside_class or ntype == "class_definition"
            # block under class also propagates; already covered by above
            for child in node.children:
                walk(child, next_inside)

        walk(root)

        # build import relationships - handle `import a, b` split
        seen: set[tuple[str, str, str]] = set()
        for imp in imports:
            imp = imp.strip()
            if imp.startswith("import "):
                rest = imp[len("import ") :].strip()
                # handle possible parentheses: import (a, b)
                rest = rest.strip("() ")
                for part in rest.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    # strip 'as alias'
                    mod = part.split()[0]
                    mod = mod.split(".")[0].strip()
                    if mod:
                        key = (file_path, mod, "DEPENDS_ON")
                        if key not in seen:
                            seen.add(key)
                            relationships.append(CodeRelationship(file_path, mod, "DEPENDS_ON"))
            elif imp.startswith("from "):
                m = re.search(r"from\s+(\S+)\s+import", imp)
                if m:
                    mod = m.group(1).split(".")[0].strip()
                    # skip relative imports like "from . import x" where mod == "."
                    mod = mod.lstrip(".")
                    if mod:
                        key = (file_path, mod, "DEPENDS_ON")
                        if key not in seen:
                            seen.add(key)
                            relationships.append(CodeRelationship(file_path, mod, "DEPENDS_ON"))

        return entities, relationships, errors

    def _parse_with_ast(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[CodeRelationship], list[str]]:
        tree = ast.parse(content)
        entities: list[CodeEntity] = []
        relationships: list[CodeRelationship] = []
        errors: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    relationships.append(
                        CodeRelationship(file_path, alias.name.split(".")[0], "DEPENDS_ON")
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    relationships.append(
                        CodeRelationship(file_path, node.module.split(".")[0], "DEPENDS_ON")
                    )

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                supers = [_ast_base_to_str(b) for b in node.bases]
                doc = ast.get_docstring(node) or ""
                sig = f"class {node.name}({', '.join(supers)})" if supers else f"class {node.name}"
                ent = CodeEntity(
                    id=f"{file_path}::CLASS::{node.name}",
                    kind="CLASS",
                    name=node.name,
                    file_path=file_path,
                    line_start=getattr(node, "lineno", 1),
                    line_end=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                    signature=sig,
                    documentation=doc,
                    metadata={"superclasses": supers},
                )
                entities.append(ent)
                for sup in supers:
                    relationships.append(CodeRelationship(ent.id, sup, "EXTENDS"))
                # methods inside class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        doc_m = ast.get_docstring(item) or ""
                        try:
                            args_txt = ast.unparse(item.args)  # type: ignore[attr-defined]
                        except Exception:
                            args_txt = "(...)"
                        sig_m = f"{item.name}{args_txt}"
                        ent_m = CodeEntity(
                            id=f"{file_path}::METHOD::{node.name}.{item.name}",
                            kind="METHOD",
                            name=f"{node.name}.{item.name}",
                            file_path=file_path,
                            line_start=item.lineno,
                            line_end=getattr(item, "end_lineno", item.lineno),
                            signature=sig_m,
                            documentation=doc_m,
                            parents=[ent.id],
                        )
                        entities.append(ent_m)
                        for sub in ast.walk(item):
                            if isinstance(sub, ast.Call):
                                try:
                                    callee = (
                                        sub.func.attr
                                        if isinstance(sub.func, ast.Attribute)
                                        else getattr(sub.func, "id", "")
                                    )
                                    if callee:
                                        relationships.append(
                                            CodeRelationship(ent_m.id, callee, "CALLS", 0.8)
                                        )
                                except Exception:
                                    pass
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or ""
                try:
                    args_txt = ast.unparse(node.args)  # type: ignore[attr-defined]
                except Exception:
                    args_txt = "(...)"
                sig = f"{node.name}{args_txt}"
                ent = CodeEntity(
                    id=f"{file_path}::FUNC::{node.name}:{node.lineno}",
                    kind="FUNCTION",
                    name=node.name,
                    file_path=file_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    signature=sig,
                    documentation=doc,
                )
                entities.append(ent)
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        try:
                            callee = (
                                sub.func.attr
                                if isinstance(sub.func, ast.Attribute)
                                else getattr(sub.func, "id", "")
                            )
                            if callee:
                                relationships.append(CodeRelationship(ent.id, callee, "CALLS", 0.8))
                        except Exception:
                            pass

        return entities, relationships, errors

    def _parse_with_regex(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[CodeRelationship], list[str]]:
        entities: list[CodeEntity] = []
        relationships: list[CodeRelationship] = []
        errors: list[str] = []
        seen: set[tuple[str, str]] = set()
        for i, line in enumerate(content.splitlines(), 1):
            m_cls = re.match(r"\s*class\s+(\w+)(?:\(([^)]*)\))?", line)
            if m_cls:
                name = m_cls.group(1)
                ent = CodeEntity(
                    id=f"{file_path}::CLASS::{name}",
                    kind="CLASS",
                    name=name,
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=line.strip()[:200],
                )
                entities.append(ent)
            # handle async def as well
            m_func = re.match(r"\s*(?:async\s+)?def\s+(\w+)\s*\(", line)
            if m_func:
                name = m_func.group(1)
                ent = CodeEntity(
                    id=f"{file_path}::FUNC::{name}:{i}",
                    kind="FUNCTION",
                    name=name,
                    file_path=file_path,
                    line_start=i,
                    line_end=i,
                    signature=line.strip()[:200],
                )
                entities.append(ent)
            m_imp = re.match(r"\s*(?:from\s+(\S+)\s+import|import\s+(\S+))", line)
            if m_imp:
                raw = m_imp.group(1) or m_imp.group(2)
                if raw:
                    # for `import a, b` the regex captures only `a,` with \S+
                    # so we need to parse full line to get all modules
                    if m_imp.group(2):  # import statement
                        # extract everything after `import`
                        rest = line.split("import", 1)[1].strip()
                        for part in rest.split(","):
                            part = part.strip().split()[0]
                            mod = part.split(".")[0]
                            if mod and (file_path, mod) not in seen:
                                seen.add((file_path, mod))
                                relationships.append(CodeRelationship(file_path, mod, "DEPENDS_ON"))
                    else:
                        mod = raw.split(".")[0].split(",")[0]
                        if mod and (file_path, mod) not in seen:
                            seen.add((file_path, mod))
                            relationships.append(CodeRelationship(file_path, mod, "DEPENDS_ON"))
        return entities, relationships, errors

    # Public alias for regex fallback (avoid calling private from CodeParser)
    def parse_with_regex(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[CodeRelationship], list[str]]:
        """Public wrapper for regex parsing (generic language fallback)."""
        return self._parse_with_regex(file_path, content)


class CodeParser:
    """High-level parser orchestrator."""

    def __init__(self):
        self.py_parser = PythonParser()

    def parse(self, file_path: str, content: str) -> CodeKnowledgeOutput:
        import time

        start = time.time()
        if file_path.endswith(".py"):
            entities, relationships, errors = self.py_parser.parse_file(file_path, content)
        else:
            # generic: treat as document, use public regex helper
            entities, relationships, errors = self.py_parser.parse_with_regex(file_path, content)

        # build symbol table
        symbol_table: dict[str, list[str]] = {file_path: [e.name for e in entities]}
        return CodeKnowledgeOutput(
            entities=entities,
            relationships=relationships,
            symbol_table=symbol_table,
            errors=errors,
            duration_seconds=time.time() - start,
        )

    def parse_many(self, items: list) -> CodeKnowledgeOutput:
        """Parse many RawItems."""
        all_entities: list[CodeEntity] = []
        all_rels: list[CodeRelationship] = []
        symbol_table: dict[str, list[str]] = {}
        errors: list[str] = []
        import time

        start = time.time()
        for it in items:
            out = self.parse(it.item_id, it.content)
            all_entities.extend(out.entities)
            all_rels.extend(out.relationships)
            symbol_table.update(out.symbol_table)
            errors.extend(out.errors)
        return CodeKnowledgeOutput(
            entities=all_entities,
            relationships=all_rels,
            symbol_table=symbol_table,
            errors=errors,
            duration_seconds=time.time() - start,
        )
