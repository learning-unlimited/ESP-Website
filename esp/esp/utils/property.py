""" Some assistance for the property based display system.
This will get more exciting when I figure out some more stuf. """

class FlatListItem:
    def __init__(self, k, v):
        self.key = k
        self.value = v

class PropertyDict(dict):
    def merge(self, other_dict):
        for key in other_dict:
            if key not in self.keys():
                self[key] = other_dict[key]
            else:
                val = other_dict[key]
                if isinstance(val, list):
                    self[key] += val
                elif isinstance(val, PropertyDict):
                    self[key] = PropertyDict(self[key]).merge(val)
                elif isinstance(val, dict):
                    self[key] = PropertyDict(self[key]).merge(PropertyDict(val))
                else:
                    self[key] = val
        return self

    def flatten(self):
        result = []
        for key in self.keys():
            new_item = FlatListItem(key, self[key])
            result.append(new_item)
        return result


