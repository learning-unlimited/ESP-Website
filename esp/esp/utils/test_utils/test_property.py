import unittest
from esp.esp.utils.property import PropertyDict, FlatListItem


class PropertyDictTest(unittest.TestCase):

    def test_merge_adds_new_key_when_missing(self):
        props = PropertyDict({'a': 1})
        props.merge({'b': 2})
        self.assertIn('b', props)
        self.assertEqual(props['b'], 2)

    def test_merge_extends_existing_list(self):
        props = PropertyDict({'a': [1]})
        props.merge({'a': [2]})
        self.assertEqual(props['a'], [1, 2])

    def test_merge_overrides_scalar_value(self):
        props = PropertyDict({'a': 1})
        props.merge({'a': 5})
        self.assertEqual(props['a'], 5)

    def test_merge_nested_dict(self):
        props = PropertyDict({'a': {'x': 1}})
        props.merge({'a': {'y': 2}})
        self.assertIn('y', props['a'])
        self.assertEqual(props['a']['y'], 2)

    def test_flatten_returns_flat_list_items(self):
        props = PropertyDict({'a': 1})
        flat_items = props.flatten()
        self.assertEqual(len(flat_items), 1)
        item = flat_items[0]
        self.assertIsInstance(item, FlatListItem)
        self.assertEqual(item.key, 'a')
        self.assertEqual(item.value, 1)


if __name__ == "__main__":
    unittest.main()