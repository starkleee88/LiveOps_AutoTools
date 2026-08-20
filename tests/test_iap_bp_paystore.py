import os
import csv
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from iap_main import sync_bp_paystore_entry


class SyncBpPaystoreEntryTests(unittest.TestCase):
    def test_adds_bp_row_to_paystore_sub_and_growth_pack_main(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paystore_sub_path = os.path.join(tmpdir, "PayStoreSub.csv")
            paystore_main_path = os.path.join(tmpdir, "PayStoreMain.csv")

            with open(paystore_sub_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["SubStoreID", "O", "LocalKey", "OpenStyle", "OpenParam", "Order", "Functype", "ProductType", "Open", "Priority"])
                writer.writerow(["9101", "Newcomer Pack", "Func_xinshoulibao", "2", "203", "1", "2", "", "1", ""])

            with open(paystore_main_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["StoreID", "StoreName", "OpenStyle", "OpenParam", "LocalKey", "FuncID", "NeedShow", "Priority", "SubStore", "SubStore"])
                writer.writerow(["1", "Character Growth Packs", "2", "415", "PayStore_MainName_9", "9900", "", "4", "", ""])

            sync_bp_paystore_entry(tmpdir, "9904", "Doctor Fate", "13108")

            with open(paystore_sub_path, "r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))
            self.assertTrue(any(row[0] == "9904" and row[1] == "Hero BP-Doctor Fate" for row in rows[1:]))
            self.assertTrue(any(row[0] == "9904" and row[2] == "CharacterName_13108" for row in rows[1:]))

            with open(paystore_main_path, "r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))
            growth_row = next(row for row in rows[1:] if row[1] == "Character Growth Packs")
            self.assertIn("9904", growth_row)


if __name__ == "__main__":
    unittest.main()
