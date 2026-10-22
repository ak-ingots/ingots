# The components

The third unit of the defaults is `components`: the {doc}`components
<../concepts/components>` of the project on the command line. Every addon
running a server would otherwise add a command of its own to run it; this
unit runs any of them, together, in one process.

```console
$ app components list
Components:
http.server: HttpServer, shutdown order 2
grpc.server: GrpcServer, shutdown order 2
storage.redis: Redis, shutdown order 8
------------
$ app components run-forever --component http.server --component grpc.server
```

- `components list` prints every component of the project with its
  path, its class and its shutdown order; nothing is created.
- `components run-forever --component PATH` configures the given
  components, servers typically, which start listening in `_configure()`,
  then runs until stopped. A path that is not a component fails the run.
- Stopping the run shuts the project down, and the project shuts its
  components down, in their order, whatever command configured them.
