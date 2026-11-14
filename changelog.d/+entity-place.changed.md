An entity is created by its owner, the slot or the factory of its
attribute, `create_entity()` of the slot: its place first, then its
`__init__`, which takes nothing now, the place known in it. An entity knows
its `parents`, weak references from the project to the owner of its slot,
`project` the first and `parent` the last, its `name`, that of the slot,
its `full_name`, the dotted path from the project, built once, and
`find_parent(kind)`, the nearest parent of a kind. An `__init__` taking the
project, `super().__init__(project)`, moves to `__init__(self)`, and an
entity made out of the slots, `Entity(project)`, to
`create_entity(cls, parent)`, at the name of its class by default. A kind
of slot gives its entities more before their `__init__` by the hook
`_prepare_entity()`. No entity is created for a project gone. A component
is named in the messages by its full name.
