`BaseSlot` holds no class any more: a slot of one class extends
`BaseClassSlot`, which has `cls`, one of several `BaseClassesSlot`.
`SlotsOwner.slots_iter()` and `slots_walk()` give the slots of one class
only, typed `BaseClassSlot`.
