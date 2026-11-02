import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from iap_main import validate_and_replace_pack_skus


class ValidatePackSkusTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sku_path = os.path.join(self.temp_dir.name, "RechargeSKU.csv")
        with open(self.sku_path, "w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file)
            writer.writerows([
                ["SkuId", "O", "PricePoint", "O", "SkuGoogle", "SkuApple"],
                ["SKU name", "Dollar Value", "Price Point ID", "Description", "Google ID", "Apple ID"],
                ["string", "O", "int", "O", "string", "string"],
                ["newplayer30", "$29.99", "102999", "New Player Pack", "", ""],
                ["progress30", "$29.99", "102999", "Progression Pack", "", ""],
                ["other29", "$29.99", "102999", "Other Pack", "", ""],
                ["motherbox5", "$4.99", "100499", "Motherbox Pack", "", ""],
            ])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_prefers_matching_sku_family_and_denomination_at_same_price(self):
        packs = [{
            "PackID": "1234001",
            "PackName": "Motherbox Pack",
            "Price": "$29.99",
            "SkuID": "motherbox30",
        }]

        adjustments = validate_and_replace_pack_skus(packs, self.temp_dir.name)

        self.assertEqual(packs[0]["SkuID"], "progress30")
        self.assertEqual(adjustments, [{
            "PackID": "1234001",
            "PackName": "Motherbox Pack",
            "Price": "$29.99",
            "OldSkuID": "motherbox30",
            "NewSkuID": "progress30",
        }])

    def test_keeps_existing_sku_unchanged(self):
        packs = [{"PackName": "Motherbox Pack", "Price": "$4.99", "SkuID": "motherbox5"}]

        adjustments = validate_and_replace_pack_skus(packs, self.temp_dir.name)

        self.assertEqual(packs[0]["SkuID"], "motherbox5")
        self.assertEqual(adjustments, [])

    def test_skips_sku_validation_for_free_pack(self):
        os.remove(self.sku_path)
        packs = [{"PackName": "Free Pack", "Price": "free", "SkuID": "missing-sku"}]

        adjustments = validate_and_replace_pack_skus(packs, self.temp_dir.name)

        self.assertEqual(packs[0]["SkuID"], "missing-sku")
        self.assertEqual(adjustments, [])

    def test_fails_when_no_sku_exists_at_the_pack_price(self):
        packs = [{"PackName": "Unknown Pack", "Price": "$8.99", "SkuID": "missing8"}]

        with self.assertRaisesRegex(Exception, "không có SKU nào cùng giá"):
            validate_and_replace_pack_skus(packs, self.temp_dir.name)


if __name__ == "__main__":
    unittest.main()