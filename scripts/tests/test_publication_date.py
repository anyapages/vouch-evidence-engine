"""The publication date is derived, never read off the archive label.

`meta.published` in the committed dataset holds the archive snapshot date. NTPF
makes an archive public on the second Friday of the following month, so anything
that tells a clinician how current a number is must derive the date rather than
print the label. These pin the derivation, including the December rollover and
the months where the 1st is itself a Friday.
"""
import calendar
import datetime
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location("ntpf", ROOT / "scripts" / "ntpf.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class PublicationDate(unittest.TestCase):
    def setUp(self):
        self.n = load()

    def test_archive_july_publishes_second_friday_of_august(self):
        self.assertEqual(self.n.publication_date("2026-07-30"), datetime.date(2026, 8, 14))

    def test_publication_is_never_the_archive_label(self):
        self.assertNotEqual(self.n.publication_date("2026-07-30"), datetime.date(2026, 7, 30))

    def test_december_rolls_into_january(self):
        self.assertEqual(self.n.publication_date("2026-12-31"), datetime.date(2027, 1, 8))

    def test_accepts_a_date_object(self):
        self.assertEqual(
            self.n.publication_date(datetime.date(2026, 7, 30)), datetime.date(2026, 8, 14)
        )

    def test_always_a_friday_and_in_the_second_week(self):
        for year in (2026, 2027):
            for month in range(1, 13):
                d = self.n.second_friday(year, month)
                self.assertEqual(d.weekday(), 4, f"{year}-{month} is not a Friday")
                self.assertIn(d.day, range(8, 15), f"{year}-{month} not in the second week")

    def test_months_where_the_first_is_a_friday(self):
        # The off-by-seven trap: if the 1st is a Friday the second Friday is the 8th.
        for year in (2026, 2027, 2028):
            for month in range(1, 13):
                if calendar.monthrange(year, month)[0] == 4:
                    self.assertEqual(self.n.second_friday(year, month).day, 8)


if __name__ == "__main__":
    unittest.main()
