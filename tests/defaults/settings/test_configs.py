import datetime
import decimal
import logging
import typing as t

from ingots.defaults.settings.configs import (
    BaseConfig,
    BoolConfig,
    DateConfig,
    DateTimeConfig,
    DecimalConfig,
    EnumConfig,
    FloatConfig,
    IntConfig,
    LogLevelConfig,
    SecureStrConfig,
    StrConfig,
    TimeConfig,
    TupleConfig,
)

from tests import TestCase

from .settings_fixtures import Mode

NOON = datetime.time(12, 30)
DAY = datetime.date(2026, 10, 19)
MOMENT = datetime.datetime(2026, 10, 19, 12, 30)


class ConfigTestCase(TestCase):
    """Each config converts what it converts and rejects the rest."""

    def assert_converts(
        self, config: BaseConfig[t.Any], *cases: tuple[object, object]
    ) -> None:
        for data, value in cases:
            with self.subTest(data=data):
                result = config.deserialize(data)
                self.assertEqual(result, value)
                self.assertIs(type(result), type(value))

    def assert_rejects(
        self, config: BaseConfig[t.Any], error: type[Exception], *datas: object
    ) -> None:
        for data in datas:
            with self.subTest(data=data), self.assertRaises(error):
                config.deserialize(data)

    def test_bool(self) -> None:
        config = BoolConfig(False)
        self.assert_converts(
            config,
            *[(True, True), (1, True), (0, False), ("Yes", True), ("on", True)],
            *[("1", True), ("FALSE", False), ("no", False), ("off", False)],
            ("0", False),
        )
        self.assert_rejects(config, ValueError, "", "nope", "2")
        self.assert_rejects(config, TypeError, 2, None, 1.0)

    def test_int(self) -> None:
        config = IntConfig(0)
        self.assert_converts(config, (5, 5), ("-5", -5), (5.0, 5))
        self.assert_rejects(config, ValueError, "5.5", "five", 5.5)
        self.assert_rejects(config, TypeError, True, None, [5])

    def test_float(self) -> None:
        config = FloatConfig(0.0)
        self.assert_converts(config, (0.5, 0.5), (2, 2.0), ("1e3", 1000.0))
        self.assert_rejects(config, ValueError, "half")
        self.assert_rejects(config, TypeError, False, None)

    def test_an_int_is_a_float(self) -> None:
        self.assertEqual(FloatConfig(1).default, 1)

    def test_decimal(self) -> None:
        config = DecimalConfig(decimal.Decimal(0))
        self.assert_converts(
            config,
            (decimal.Decimal("1.5"), decimal.Decimal("1.5")),
            ("0.10", decimal.Decimal("0.10")),
            (3, decimal.Decimal(3)),
            (0.1, decimal.Decimal("0.1")),
        )
        self.assert_rejects(config, ValueError, "ten")
        self.assert_rejects(config, TypeError, True, None)

    def test_str(self) -> None:
        config = StrConfig("")
        self.assert_converts(config, ("text", "text"))
        self.assert_rejects(config, TypeError, 5, None)

    def test_date(self) -> None:
        config = DateConfig(DAY)
        self.assert_converts(config, (DAY, DAY), ("2026-10-19", DAY))
        self.assert_rejects(config, ValueError, "19.10.2026")
        self.assert_rejects(config, TypeError, MOMENT, 20261019)

    def test_time(self) -> None:
        config = TimeConfig(NOON)
        self.assert_converts(config, (NOON, NOON), ("12:30", NOON))
        self.assert_rejects(config, ValueError, "noon")
        self.assert_rejects(config, TypeError, 1230)

    def test_datetime(self) -> None:
        config = DateTimeConfig(MOMENT)
        self.assert_converts(config, (MOMENT, MOMENT), ("2026-10-19T12:30", MOMENT))
        self.assert_rejects(config, ValueError, "today")
        self.assert_rejects(config, TypeError, DAY.toordinal())

    def test_enum(self) -> None:
        config = EnumConfig(Mode.SAFE)
        self.assert_converts(config, (Mode.FAST, Mode.FAST), ("FAST", Mode.FAST))
        self.assert_rejects(config, ValueError, "fast", "SLOW")
        self.assert_rejects(config, TypeError, 1)

    def test_log_level(self) -> None:
        config = LogLevelConfig(logging.INFO)
        self.assert_converts(
            config, ("debug", logging.DEBUG), ("WARNING", logging.WARNING), ("15", 15)
        )
        self.assert_rejects(config, ValueError, "loud")

    def test_tuple(self) -> None:
        config = TupleConfig(("localhost", 8080))
        self.assert_converts(
            config,
            (("example.org", 80), ("example.org", 80)),
            ('["example.org", 80]', ("example.org", 80)),
            (["example.org", 80], ("example.org", 80)),
        )
        self.assert_rejects(config, ValueError, "[oops")
        self.assert_rejects(
            config, TypeError, '["example.org"]', '[80, "example.org"]', 80
        )


class ValidateTestCase(TestCase):
    """Each config takes a value of its type only."""

    def test_a_value_of_another_type_does_not_fit(self) -> None:
        configs: list[tuple[BaseConfig[t.Any], object]] = [
            (BoolConfig(False), 1),
            (IntConfig(0), True),
            (FloatConfig(0.0), "1.0"),
            (DecimalConfig(decimal.Decimal(0)), 1),
            (StrConfig(""), 1),
            (DateConfig(DAY), MOMENT),
            (TimeConfig(NOON), MOMENT),
            (DateTimeConfig(MOMENT), DAY),
            (EnumConfig(Mode.SAFE), "SAFE"),
            (TupleConfig(("localhost", 8080)), ["localhost", 8080]),
        ]
        for config, value in configs:
            with self.subTest(config=config), self.assertRaises(TypeError):
                config.validate(value)


class ConfigDefinitionTestCase(TestCase):
    def test_a_default_must_fit(self) -> None:
        with self.assertRaisesRegex(TypeError, r"^IntConfig: 'x' is not an int$"):
            IntConfig("x")  # type: ignore[arg-type]

    def test_a_config_is_named_after_its_attribute(self) -> None:
        class Holder:
            PORT = IntConfig(1)

        self.assertEqual(Holder.PORT.name, "PORT")
        self.assertEqual(repr(Holder.PORT), "IntConfig(1)")

    def test_errors_name_the_config(self) -> None:
        class Holder:
            PORT = IntConfig(1)

        with self.assertRaisesRegex(ValueError, r"^PORT: 'x' is not an int$"):
            Holder.PORT.deserialize("x")
        with self.assertRaisesRegex(TypeError, r"^PORT: cannot convert NoneType"):
            Holder.PORT.deserialize(None)


class SecureStrConfigTestCase(TestCase):
    def test_the_secret_is_never_shown(self) -> None:
        config = SecureStrConfig("secret")
        self.assertEqual(repr(config), "SecureStrConfig('***')")
        self.assertEqual(config.format_value("secret"), "***")
        with self.assertRaises(TypeError) as raised:
            config.deserialize(12345)
        self.assertNotIn("12345", str(raised.exception))
