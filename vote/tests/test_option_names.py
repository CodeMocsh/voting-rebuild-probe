import unittest

from vote.option_names import read_option_names


class ReadOptionNamesTest(unittest.TestCase):
    def test_unset_variables_give_cats_and_dogs(self):
        names = read_option_names({})
        self.assertEqual((names.option_a, names.option_b), ("Cats", "Dogs"))

    def test_set_variables_give_their_values(self):
        names = read_option_names({"OPTION_A": "Tea", "OPTION_B": "Coffee"})
        self.assertEqual((names.option_a, names.option_b), ("Tea", "Coffee"))

    def test_one_set_variable_leaves_the_other_default(self):
        names = read_option_names({"OPTION_B": "Coffee"})
        self.assertEqual((names.option_a, names.option_b), ("Cats", "Coffee"))

    def test_empty_variable_gives_empty_name(self):
        names = read_option_names({"OPTION_A": ""})
        self.assertEqual((names.option_a, names.option_b), ("", "Dogs"))

    def test_names_stay_fixed_when_environ_changes_after_read(self):
        environ = {"OPTION_A": "Tea", "OPTION_B": "Coffee"}
        names = read_option_names(environ)
        environ["OPTION_A"] = "Milk"
        del environ["OPTION_B"]
        self.assertEqual((names.option_a, names.option_b), ("Tea", "Coffee"))


if __name__ == "__main__":
    unittest.main()
