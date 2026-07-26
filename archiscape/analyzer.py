import ast
import os
from pathlib import Path

STDLIB_MODULES = {
    "os", "sys", "re", "math", "json", "csv", "io", "collections",
    "itertools", "functools", "pathlib", "typing", "datetime",
    "uuid", "hashlib", "base64", "textwrap", "string", "random",
    "statistics", "decimal", "fractions", "numbers", "abc",
    "ast", "inspect", "dis", "tokenize", "parser",
    "asyncio", "threading", "multiprocessing", "concurrent",
    "socket", "http", "urllib", "email", "ssl",
    "xml", "html", "configparser", "argparse", "getopt",
    "logging", "warnings", "traceback", "pdb",
    "unittest", "doctest", "test",
    "subprocess", "shutil", "glob", "fnmatch", "tempfile",
    "pickle", "shelve", "dbm", "sqlite3",
    "zipfile", "tarfile", "gzip", "bz2", "lzma",
    "ctypes", "struct", "array", "mmap",
    "dataclasses", "enum", "types", "typing",
    "importlib", "pkgutil", "pkg_resources",
    "signal", "platform", "resource", "sysconfig",
    "ioctl", "fcntl", "termios",
    "copy", "pprint", "profile", "timeit",
    "atexit", "gc", "inspect", "trace",
    "stat", "filecmp", "fileinput", "linecache",
    "getpass", "curses", "tty", "pty",
    "webbrowser", "turtle", "tkinter",
    "sched", "calendar", "zoneinfo",
    "dis", "opcode", "symtable",
    "code", "codeop", "codecs",
    "contextlib", "contextvars",
    "weakref", "operator", "keyword",
}

DEPTH_LEVELS = {"module": 0, "class": 1, "function": 2}


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
        self.decorators = []
        self.attributes = []

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
            "docstring": self.docstring[:300] if self.docstring else None,
            "parent": self.parent.full_name if self.parent else None,
            "imports": self.imports,
            "decorators": self.decorators,
            "attributes": self.attributes,
            "children": [c.to_dict() for c in self.children],
        }


def classify_import(name):
    if name in STDLIB_MODULES or name.split(".")[0] in STDLIB_MODULES:
        return "stdlib"
    return "third_party"


EXCLUDE_DIRS = {
    "node_modules", "__pycache__", ".git", ".venv", "venv",
    "env", "dist", "build", ".egg-info", ".tox",
    "mypy_cache", ".pytest_cache", ".ruff_cache",
}


def _should_skip(rel_path):
    parts = rel_path.split(os.sep)
    return any(p in EXCLUDE_DIRS for p in parts)


class Analyzer:
    def __init__(self, path, depth="function"):
        self.path = Path(path).resolve()
        self.depth = DEPTH_LEVELS.get(depth, 2)
        self.entities = []
        self.file_entities = {}
        self.readme_text = None

    def scan(self):
        py_files = sorted(self.path.rglob("*.py"))
        for filepath in py_files:
            rel = os.path.relpath(filepath, self.path)
            if _should_skip(rel):
                continue
            self._analyze_file(filepath)

        readme = self._find_readme()
        if readme:
            try:
                with open(readme, encoding="utf-8") as f:
                    self.readme_text = f.read()[:3000]
            except Exception:
                pass

        return self._build_report()

    def _find_readme(self):
        for name in ("README.md", "README.rst", "README.txt", "README"):
            candidate = self.path / name
            if candidate.exists():
                return candidate
        return None

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
        name = rel_path.replace("/", ".").replace("\\", ".").replace(".py", "")
        if name.endswith(".__init__"):
            name = name[:-9]

        module_doc = ast.get_docstring(tree)
        mod_entity = CodeEntity(
            name=name,
            kind="module",
            filepath=str(filepath),
            lineno=1,
            docstring=module_doc,
        )

        self._extract_imports(tree, mod_entity)

        if self.depth >= 1:
            for node in ast.iter_child_nodes(tree):
                self._extract_entity(node, mod_entity, source, depth=1)

        self.entities.append(mod_entity)
        self.file_entities[rel_path] = mod_entity

    def _extract_imports(self, tree, entity):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    entity.imports.append({
                        "name": alias.name,
                        "alias": alias.asname,
                        "kind": classify_import(alias.name),
                    })
            elif isinstance(node, ast.ImportFrom):
                module_base = node.module or ""
                for alias in node.names:
                    full_name = f"{module_base}.{alias.name}" if module_base else alias.name
                    entity.imports.append({
                        "name": full_name,
                        "alias": alias.asname,
                        "kind": classify_import(module_base or alias.name),
                    })

    def _extract_entity(self, node, parent, source, depth=1):
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
                cls.decorators.append(ast.unparse(dec))
            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            cls.attributes.append(target.id)
                elif isinstance(item, ast.AnnAssign):
                    if isinstance(item.target, ast.Name):
                        cls.attributes.append(item.target.id)
                if self.depth >= 2 and isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._extract_entity(item, cls, source, depth + 1)
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
                func.decorators.append(ast.unparse(dec))
            parent.children.append(func)

    def _build_report(self):
        nodes = [ent.to_dict() for ent in self.entities]
        return {
            "project_root": str(self.path),
            "modules_count": len(self.entities),
            "entities": nodes,
            "readme": self.readme_text,
        }
