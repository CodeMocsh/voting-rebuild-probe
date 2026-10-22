import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "specification" / "option_naming"))

import bound
from seams import RecordOptionNamesInput


class RecordOptionNamesTest(unittest.TestCase):
    def setUp(self):
        self.seams = bound.seams()

    def names(self, given):
        self.seams.record_option_names(given)
        return {code: row.name for code, row in self.seams.option_store.read().items()}

    def test_none_inputs_seed_defaults(self):
        self.assertEqual(self.names(RecordOptionNamesInput()), {"a": "Cats", "b": "Dogs"})

    def test_empty_input_seeds_empty_name(self):
        self.assertEqual(
            self.names(RecordOptionNamesInput(option_a="")), {"a": "", "b": "Dogs"}
        )

    def test_set_inputs_seed_their_values(self):
        self.assertEqual(
            self.names(RecordOptionNamesInput(option_a="Tea", option_b="Coffee")),
            {"a": "Tea", "b": "Coffee"},
        )

    def test_reset_empties_the_store(self):
        self.names(RecordOptionNamesInput())
        self.seams.reset()
        self.assertEqual(self.seams.option_store.read(), {})


if __name__ == "__main__":
    unittest.main()
