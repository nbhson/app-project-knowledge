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
    _PY_LANGUAGE = Language(tree_sitter_python.language())
except Exception:
    HAS_TREESITTER = False
    _PY_LANGUAGE = None


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
        entities: list[CodeEntity] = []
        relationships: list[CodeRelationship] = []

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

    def _parse_with_treesitter(self, file_path: str, content: str):
        from tree_sitter import Parser

        parser = Parser(_PY_LANGUAGE)
        tree = parser.parse(bytes(content, "utf8"))
        root = tree.root_node
        entities: list[CodeEntity] = []
        relationships: list[CodeRelationship] = []
        errors: list[str] = []

        # extract imports
        imports = []

        # walk
        def walk(node, depth=0):
            if node.type == "import_statement":
                txt = content[node.start_byte : node.end_byte]
                imports.append(txt.strip())
                # create DEPENDS_ON later
            elif node.type == "import_from_statement":
                txt = content[node.start_byte : node.end_byte]
                imports.append(txt.strip())
            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                name = (
                    content[name_node.start_byte : name_node.end_byte] if name_node else "Unknown"
                )
                # superclasses
                supers = []
                super_node = node.child_by_field_name("superclasses")
                if super_node:
                    sup_txt = content[super_node.start_byte : super_node.end_byte]
                    supers = re.findall(r"\w+", sup_txt)
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
            elif node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                name = (
                    content[name_node.start_byte : name_node.end_byte] if name_node else "Unknown"
                )
                # determine if method (inside class) heuristic: depth check via parent type
                # tree-sitter parent check not trivial, use simple: if inside class node we already handled
                # approximate as FUNCTION, later analyzer can reclassify
                params_node = node.child_by_field_name("parameters")
                params = (
                    content[params_node.start_byte : params_node.end_byte] if params_node else "()"
                )
                sig = f"{name}{params}"
                ent = CodeEntity(
                    id=f"{file_path}::FUNC::{name}:{node.start_point[0]}",
                    kind="FUNCTION",
                    name=name,
                    file_path=file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=sig,
                )
                entities.append(ent)
            elif node.type == "decorated_definition":
                # will be handled via children
                pass

            for child in node.children:
                walk(child, depth + 1)

        walk(root)

        # build import relationships
        for imp in imports:
            # parse module
            m = re.search(r"from\s+(\S+)\s+import|import\s+(\S+)", imp)
            if m:
                mod = m.group(1) or m.group(2)
                mod = mod.split(",")[0].strip().split(".")[0]
                relationships.append(CodeRelationship(file_path, mod, "DEPENDS_ON"))

        # dedup relationships using set
        return entities, relationships, errors

    def _parse_with_ast(self, file_path: str, content: str):
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
                supers = [
                    b.attr if isinstance(b, ast.Attribute) else getattr(b, "id", str(b))
                    for b in node.bases
                ]
                # build entity
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
                        sig_m = f"{item.name}{ast.unparse(item.args) if hasattr(ast, 'unparse') else '(...)'}"
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
                        # CALLS detection: find Call nodes inside method
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
                sig = f"{node.name}{ast.unparse(node.args) if hasattr(ast, 'unparse') else '(...)'}"
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

    def _parse_with_regex(self, file_path: str, content: str):
        entities: list[CodeEntity] = []
        relationships: list[CodeRelationship] = []
        errors: list[str] = []
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
            m_func = re.match(r"\s*def\s+(\w+)\s*\(", line)
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
                mod = (m_imp.group(1) or m_imp.group(2)).split(".")[0].split(",")[0]
                relationships.append(CodeRelationship(file_path, mod, "DEPENDS_ON"))
        return entities, relationships, errors


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
            # generic: treat as document
            entities, relationships, errors = [], [], []
            # still try regex for class/func in other languages simple
            py_ent, py_rel, _ = PythonParser()._parse_with_regex(file_path, content)
            entities.extend(py_ent)
            relationships.extend(py_rel)

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
