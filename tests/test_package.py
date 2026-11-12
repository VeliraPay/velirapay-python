from __future__ import annotations

import builtins
import tomllib
import unittest
from pathlib import Path

import velirapay


class PackageTest(unittest.TestCase):
    def test_the_version_matches_the_project(self) -> None:
        project = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(project["project"]["version"], velirapay.__version__)
        self.assertEqual(velirapay.__version__, velirapay.VeliraPayClient.VERSION)
        self.assertEqual(velirapay.__version__, velirapay.VERSION)

    def test_everything_exported_exists_and_no_builtin_is_shadowed(self) -> None:
        for name in velirapay.__all__:
            with self.subTest(name):
                self.assertTrue(hasattr(velirapay, name))
                self.assertFalse(hasattr(builtins, name), f"{name} would hide the builtin of the same name")

    def test_every_error_is_a_velirapay_error(self) -> None:
        errors = [
            value for value in vars(velirapay).values() if isinstance(value, type) and issubclass(value, Exception)
        ]

        self.assertEqual(14, len(errors))

        for error in errors:
            with self.subTest(error.__name__):
                self.assertTrue(issubclass(error, velirapay.VeliraPayError))

    def test_the_package_says_it_is_typed(self) -> None:
        self.assertTrue((Path(velirapay.__file__).parent / "py.typed").is_file())


if __name__ == "__main__":
    unittest.main()
