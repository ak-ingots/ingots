`ingots.testing`: `ProjectFixture` and `ProjectTestCase`, the project of a
test case created and configured for each test in its event loop, by its own
configs, not by the environment, and shut down after it; the config
`IS_CONFIGURE_LOGGING`, off leaving the logging of the process to its owner.
