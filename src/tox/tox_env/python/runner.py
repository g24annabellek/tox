"""
A tox run environment that handles the Python language.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Union, cast

from packaging.requirements import Requirement

from tox.tox_env.errors import Skip

from ..runner import RunToxEnv
from .api import Dep, NoInterpreter, Python


class PythonRun(Python, RunToxEnv, ABC):
    def register_config(self) -> None:
        super().register_config()
        outer_self = self

        class _Dep(Dep):
            def __init__(self, raw: Any) -> None:
                if not raw.startswith("-r"):
                    val: Union[Path, Requirement] = Requirement(raw)
                else:
                    path = Path(raw[2:])
                    val = path if path.is_absolute() else cast(Path, outer_self.core["toxinidir"]) / path
                super().__init__(val)

        self.conf.add_config(
            keys="deps",
            of_type=List[_Dep],
            default=[],
            desc="Name of the python dependencies as specified by PEP-440",
        )
        self.core.add_config(
            keys=["skip_missing_interpreters"],
            default=True,
            of_type=bool,
            desc="skip running missing interpreters",
        )

    def no_base_python_found(self, base_pythons: List[str]) -> NoReturn:
        if self.core["skip_missing_interpreters"]:
            raise Skip
        raise NoInterpreter(base_pythons)

    def setup(self) -> None:
        """setup the tox environment"""
        super().setup()
        self.install_deps()

        if self.package_env is not None:
            package_deps = self.package_env.get_package_dependencies(self.conf["extras"])
            self.cached_install([Dep(p) for p in package_deps], PythonRun.__name__, "package_deps")
        self.install_package()

    def install_deps(self) -> None:
        self.cached_install(self.conf["deps"], PythonRun.__name__, "deps")

    def install_package(self) -> None:
        if self.package_env is not None:
            package: List[Dep] = [Dep(p) for p in self.package_env.perform_packaging()]
        else:
            package = [Dep(d) for d in self.get_pkg_no_env()] if self.has_package else []
        if package:
            self.install_python_packages(package, **self.install_package_args())  # type: ignore[no-untyped-call]

    def get_pkg_no_env(self) -> List[Path]:
        # by default in Python just forward the root folder to the installer
        return [cast(Path, self.core["tox_root"])]

    @abstractmethod
    def install_package_args(self) -> Dict[str, Any]:
        raise NotImplementedError
