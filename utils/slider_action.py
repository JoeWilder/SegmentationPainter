from enum import Enum

class SliderAction(Enum):
    AUTO = 0
    WEAKEST = 1
    MEDIUM = 2
    STRONGEST = 3

    def fromValue(value):
        for action in SliderAction:
            if action.value == value:
                return action
        return None