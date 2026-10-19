"""The environment as a source of overrides."""

__all__ = ("EnvLoader",)

import os
import typing as t

from .base import BaseLoader, Overrides

if t.TYPE_CHECKING:
    from ingots.defaults.project import Project


class EnvLoader(BaseLoader):
    """
    Loads the environment variables named with the project's prefix:
    ``APP_HTTP_PORT`` sets ``HTTP_PORT`` when ``env_configs_prefix`` is
    ``"APP"``. Names are compared in upper case.
    """

    project: "Project"

    async def load(self) -> list[Overrides]:
        prefix = f"{self._get_prefix()}_".upper()
        data = {
            name.upper().removeprefix(prefix): value
            for name, value in os.environ.items()
            if name.upper().startswith(prefix)
        }
        return [Overrides(f"the environment ({prefix}*)", data)]

    def _get_prefix(self) -> str:
        try:
            return self.project.env_configs_prefix
        except AttributeError:
            raise RuntimeError(
                f"{type(self.project).__qualname__}.env_configs_prefix is not set"
            ) from None
