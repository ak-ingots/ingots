"""Files as a source of overrides."""

__all__ = ("BaseFormat", "FileLoader", "IniFormat", "JsonFormat")

import abc
import configparser
import json
import typing as t

from ingots.puer import Entity, Slot, Unit

from .base import BaseLoader, Overrides

if t.TYPE_CHECKING:
    from pathlib import Path

    from ingots.defaults.project import Project


class BaseFormat(Entity):
    """A file format of the overrides, chosen by the file extension."""

    EXTENSIONS: t.ClassVar[frozenset[str]] = frozenset()

    @abc.abstractmethod
    def parse(self, text: str) -> dict[str, object]:
        """
        The overrides in the text of a file.

        :raises ValueError: the text is not in the format.
        """
        raise NotImplementedError(f"{type(self).__qualname__}.parse")


class IniFormat(BaseFormat):
    """
    An INI file: the options of every section, the unnamed one included, in
    the case they are written in. Every value is a string.
    """

    EXTENSIONS = frozenset({".ini"})

    @t.override
    def parse(self, text: str) -> dict[str, object]:
        parser = configparser.ConfigParser(allow_unnamed_section=True)
        parser.optionxform = str  # type: ignore[assignment,method-assign]
        try:
            parser.read_string(text)
        except configparser.Error as error:
            raise ValueError(str(error)) from None
        return {
            name: value
            for section in parser.sections()
            for name, value in parser.items(section)
        }


class JsonFormat(BaseFormat):
    """A JSON file: an object of config names to JSON values."""

    EXTENSIONS = frozenset({".json"})

    @t.override
    def parse(self, text: str) -> dict[str, object]:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError(f"not a JSON object but {type(data).__qualname__}")
        return data


class FileLoader(Unit, BaseLoader):
    """
    Loads the ``--configs-file PATH`` options of the project, in their order,
    each file in the format its extension chooses among the formats of the
    slots: ``yaml_format = Slot(YamlFormat)`` in a subclass adds one. Loads
    nothing when the project is not run from the command line. An extension
    belongs to one format: a subclass whose formats share one fails.
    """

    project: "Project"
    ini_format = Slot(IniFormat)
    json_format = Slot(JsonFormat)

    @t.override
    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        check_format_extensions(cls)

    @t.override
    async def load(self) -> list[Overrides]:
        try:
            args = self.project.cli_args
        except RuntimeError:  # not run from the command line
            return []
        return [self._load_file(path) for path in args.configs_files]

    def _load_file(self, path: "Path") -> Overrides:
        source = f"the file {str(path)!r}"
        file_format = self._find_format(path)
        if file_format is None:
            return Overrides(source, {}, (f"{source}: no format for {path.suffix!r}",))
        try:
            data = file_format.parse(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            return Overrides(source, {}, (f"{source}: {error}",))
        return Overrides(source, data)

    def _find_format(self, path: "Path") -> BaseFormat | None:
        extension = path.suffix.lower()
        for name, slot in self.slots_iter(_FORMAT):
            if extension in slot.cls.EXTENSIONS:
                return self.slots_find_entity(name, _FORMAT)
        return None


def check_format_extensions(cls: type[FileLoader]) -> None:
    """
    Internal, run when the class is created: an extension belongs to one
    format slot of the file loader, so no format shadows another.
    """
    owners: dict[str, str] = {}
    for name, slot in cls.slots_iter(_FORMAT):
        for extension in slot.cls.EXTENSIONS:
            owner = owners.setdefault(extension, name)
            if owner != name:
                raise TypeError(
                    f"{cls.__qualname__}: {extension!r} is an extension of "
                    f"both {owner} and {name}"
                )


# the kind of the format slots; mypy takes no abstract class for type[...]
# (type-abstract), and the kind is only matched with issubclass()
_FORMAT: type[BaseFormat] = BaseFormat  # type: ignore[type-abstract]
