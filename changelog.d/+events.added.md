The events, `ingots.defaults.events`, `project.events` of the defaults: an
event is a fact of a domain, a frozen dataclass, its subscribers the
operations of a `Factories` in the unit of its domain, `ev_<name>`.
`publish(subscribers, event, metadata)`, not awaited, runs them in the
background by `run_each_in_group`, for the caller of the publisher; inside
`hold()`, when the outermost hold ends, raising or not, its scope dropping
them by `discard()`, as the facade of the transactions of an addon does on
a rollback. The project waits for the subscribers running when it shuts
down, before its components, `join()`.
