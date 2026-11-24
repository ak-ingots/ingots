A slot declared again in a subclass is checked for its kind alone when the
class is created, a `Slot` replaced by a `Slot`, a `Factory` by a
`Factory`: the class it holds is for mypy to check against the type of the
slot of the base, which an annotation may widen, `notifier: Slot[BaseNotifier]
= Slot(MailNotifier)` letting a subclass hold a sibling of the default. A slot
the subclass inherits from one of bases holding different slots must still
hold a subclass of what each holds, the new hook `_joins()` of a kind of
slot telling it: the order of the bases picks none silently.
