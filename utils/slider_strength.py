from enum import Enum


class SliderStrength(Enum):
    AUTO = 0
    WEAKEST = 1
    MEDIUM = 2
    STRONGEST = 3

    def fromValue(value):
        for action in SliderStrength:
            if action.value == value:
                return action
        return None
