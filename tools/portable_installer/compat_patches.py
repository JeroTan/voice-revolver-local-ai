"""
Compatibility patches for installer-created Python environments.

These patches capture local stable-environment fixes that are not represented by
package version locks alone.
"""

from __future__ import annotations

import sysconfig
from pathlib import Path


HYDRA_CONF_REPLACEMENTS = {
    "override_dirname: OverrideDirname = OverrideDirname()": "override_dirname: OverrideDirname = field(default_factory=OverrideDirname)",
    "config: JobConfig = JobConfig()": "config: JobConfig = field(default_factory=JobConfig)",
    "run: RunDir = RunDir()": "run: RunDir = field(default_factory=RunDir)",
    "sweep: SweepDir = SweepDir()": "sweep: SweepDir = field(default_factory=SweepDir)",
    "help: HelpConf = HelpConf()": "help: HelpConf = field(default_factory=HelpConf)",
    "hydra_help: HydraHelpConf = HydraHelpConf()": "hydra_help: HydraHelpConf = field(default_factory=HydraHelpConf)",
    "overrides: OverridesConf = OverridesConf()": "overrides: OverridesConf = field(default_factory=OverridesConf)",
    "job: JobConf = JobConf()": "job: JobConf = field(default_factory=JobConf)",
    "runtime: RuntimeConf = RuntimeConf()": "runtime: RuntimeConf = field(default_factory=RuntimeConf)",
}


def patch_hydra_dataclass_defaults() -> bool:
    hydra_conf = Path(sysconfig.get_paths()["purelib"]) / "hydra" / "conf" / "__init__.py"
    if not hydra_conf.exists():
        return False

    text = hydra_conf.read_text(encoding="utf-8")
    original = text
    for old, new in HYDRA_CONF_REPLACEMENTS.items():
        text = text.replace(old, new)

    if text != original:
        hydra_conf.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    changed = patch_hydra_dataclass_defaults()
    print(f"hydra_dataclass_patch={'applied' if changed else 'already_ok'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
