import ast
import os
from pathlib import Path
from collections import defaultdict

EXCLUDE_DIRS = {"node_modules", "__pycache__", ".git", ".venv", "venv", "env",
                "dist", "build", ".egg-info", "eggs", ".tox", "mypy_cache",
                ".pytest_cache", ".ruff_cache", "__pypackages__"}
EXCLUDE_FILES = {"__init__.py"}

def _should_exclude(path, root):
    rel = os.path.relpath(path, root)
    parts = rel.split(os.sep)
    return any(p in EXCLUDE_DIRS for p in parts) or os.path.basename(path) in EXCLUDE_FILES


class CodeEntity:
    def __init__(self, name, kind, filepath, lineno, docstring=None, parent=None):
        self.name = name
        self.kind = kind
        self.filepath = filepath
        self.lineno = lineno
        self.docstring = docstring
        self.parent = parent
        self.children = []
        self.imports = []
        self.calls = []
        self.decorators = []

    @property
    def full_name(self):
        if self.parent:
            return f"{self.parent.full_name}.{self.name}"
        return self.name

    @property
    def module_path(self):
        rel = os.path.relpath(self.filepath)
        return str(rel).replace("/", ".").replace("\\", ".").replace(".py", "")

    def to_dict(self):
        return {
            "name": self.name,
            "full_name": self.full_name,
            "kind": self.kind,
            "filepath": self.filepath,
            "lineno": self.lineno,
            "docstring": (self.docstring[:200] if self.docstring else None),
            "parent": self.parent.full_name if self.parent else None,
            "imports": self.imports,
            "calls": self.calls,
            "decorators": self.decorators,
            "children": [c.to_dict() for c in self.children],
        }


class Analyzer:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.entities = []
        self.file_entities = {}
        self.module_docstrings = {}

    def scan(self):
        py_files = sorted(self.path.rglob("*.py"))
        for filepath in py_files:
            if _should_exclude(str(filepath), self.path):
                continue
            self._analyze_file(filepath)
        return self._build_report()

    def _analyze_file(self, filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                source = f.read()
        except Exception:
            return
        try:
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError:
            return

        rel_path = os.path.relpath(filepath, self.path)
        module_doc = ast.get_docstring(tree)
        if module_doc:
            self.module_docstrings[rel_path] = module_doc[:300]

        mod_entity = CodeEntity(
            name=rel_path.replace("/", ".").replace(".py", ""),
            kind="module",
            filepath=str(filepath),
            lineno=1,
            docstring=module_doc,
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod_entity.imports.append({
                        "name": alias.name,
                        "alias": alias.asname,
                        "kind": "external" if "." not in alias.name else "internal",
                    })
            elif isinstance(node, ast.ImportFrom):
                module_base = node.module or ""
                for alias in node.names:
                    full_name = f"{module_base}.{alias.name}" if module_base else alias.name
                    mod_entity.imports.append({
                        "name": full_name,
                        "alias": alias.asname,
                        "kind": "external" if module_base and "." not in module_base else "internal",
                    })

        for node in ast.iter_child_nodes(tree):
            self._extract_entity(node, mod_entity, source)

        self.entities.append(mod_entity)
        self.file_entities[rel_path] = mod_entity

    def _extract_entity(self, node, parent, source):
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node)
            cls = CodeEntity(
                name=node.name,
                kind="class",
                filepath=parent.filepath,
                lineno=node.lineno,
                docstring=doc,
                parent=parent,
            )
            for dec in node.decorator_list:
                cls.decorators.append(ast.unparse(dec) if hasattr(ast, "unparse") else "")
            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                    self._extract_entity(item, cls, source)
                elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                    pass
            parent.children.append(cls)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node)
            func = CodeEntity(
                name=node.name,
                kind="function",
                filepath=parent.filepath,
                lineno=node.lineno,
                docstring=doc,
                parent=parent,
            )
            for dec in node.decorator_list:
                func.decorators.append(ast.unparse(dec) if hasattr(ast, "unparse") else "")
            parent.children.append(func)

    def _extract_calls(self, node, entity, source):
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                try:
                    func_str = ast.unparse(child.func) if hasattr(ast, "unparse") else ""
                    if func_str and not func_str.startswith("_"):
                        entity.calls.append(func_str)
                except Exception:
                    pass

    def _build_report(self):
        nodes = []
        for ent in self.entities:
            nodes.append(ent.to_dict())
        return {
            "project_root": str(self.path),
            "modules_count": len(self.entities),
            "module_docstrings": self.module_docstrings,
            "entities": nodes,
        }
