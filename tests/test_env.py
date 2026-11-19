from pathlib import Path

from mutagent.env import describe_environment, stub

MODULES = Path(__file__).parent.parent / "bench" / "modules"


def test_single_file_module():
    e = describe_environment(MODULES / "ratelimiter" / "src" / "ratelimiter.py")
    assert "import ratelimiter" in e and "standard library" in e


def test_package_module_gets_import_path_deps_and_sibling_stubs():
    e = describe_environment(MODULES / "vioreg_score" / "src" / "vioreg" / "score.py")
    assert "from vioreg import score" in e and "never as a bare" in e
    assert "numpy" in e and "scipy" in e
    assert "def load_tum(" in e and "class Trajectory" in e  # sibling signatures, no bodies
    assert "np.loadtxt" not in e


def test_stub_keeps_signatures_and_first_doc_line_only():
    out = stub('def f(a: int, b=2) -> str:\n    """Does f.\n\n    More."""\n    return "x"\n')
    assert out == "def f(a: int, b=2) -> str  # Does f."
