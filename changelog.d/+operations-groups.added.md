Operations independent of each other run together:
`OperationsUnit.run_group()` runs the operations of a `Factories`, a new
slot of several classes, concurrently with the same parameters, checking
the caller for every one before any runs, their failures raised together
in an `ExceptionGroup`, their results in `OperationsResults`, by class.
