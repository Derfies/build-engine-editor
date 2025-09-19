class Texture:

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if not isinstance(self, other.__class__):
            return False
        return self.value == other.value
