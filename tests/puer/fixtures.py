"""
Two addons and an application composing them, as in the ADR 0004 concepts:
``pkg1`` has a tree three levels deep, ``pkg2`` something else entirely, both
extend a shared ``common`` entity, the application joins them and customizes
pkg1's entity at the bottom.
"""

from ingots.puer import Entity, Project, Unit, Slot

# a default every addon may extend, like settings


class Common(Entity):
    pass


class CommonProject(Project):
    common = Slot(Common)


# pkg1


class Pkg1Common(Common):
    PKG1 = "pkg1"


class Pkg1Entity(Entity):
    project: "Pkg1Project"

    def method(self) -> str:
        return f"pkg1({self.project.common.PKG1})"


class Pkg1SubUnit(Unit):
    entity = Slot(Pkg1Entity)


class Pkg1Unit(Unit):
    sub_unit = Slot(Pkg1SubUnit)


class Pkg1Project(CommonProject):
    common = Slot(Pkg1Common)
    pkg1_unit = Slot(Pkg1Unit)


# pkg2


class Pkg2Common(Common):
    PKG2 = "pkg2"


class Pkg2Unit(Unit):
    project: "Pkg2Project"

    def method(self) -> str:
        return f"pkg2({self.project.common.PKG2})"


class Pkg2Project(CommonProject):
    common = Slot(Pkg2Common)
    pkg2_unit = Slot(Pkg2Unit)


# the application


class AppCommon(Pkg1Common, Pkg2Common):
    APP = "app"


class AppEntity(Pkg1Entity):
    project: "AppProject"

    def method(self) -> str:
        return f"{super().method()} + {self.project.pkg2_unit.method()}"


class AppSubUnit(Pkg1SubUnit):
    entity = Slot(AppEntity)


class AppUnit(Pkg1Unit):
    sub_unit = Slot(AppSubUnit)


class AppProject(Pkg1Project, Pkg2Project):
    common = Slot(AppCommon)
    pkg1_unit = Slot(AppUnit)
