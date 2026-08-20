import csv
import os
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from iap_main import export_text_assets, get_legendary_daily_shop_icon


class ExportTextAssetsTests(unittest.TestCase):
    def test_legendary_daily_shop_icons_repeat_using_character_data(self):
        token_icons = [
            get_legendary_daily_shop_icon('Token Shop', index, '13237', 'A')
            for index in range(1, 13)
        ]
        self.assertEqual(token_icons[:6], [
            'ui_store_EventCoinToken_1A_13237',
            'ui_store_EventCoinToken_1A_13237',
            'ui_store_EventCoinToken_1B_13237',
            'ui_store_EventCoinToken_1B_13237',
            'ui_store_EventCoinToken_1C_13237',
            'ui_store_EventCoinToken_1C_13237',
        ])
        self.assertEqual(token_icons[:6], token_icons[6:])

        badge_icons = [
            get_legendary_daily_shop_icon('Badge Shop', index, '13237', 'C')
            for index in range(1, 9)
        ]
        self.assertEqual(badge_icons[:4], [
            'ui_store_EventBadge_1',
            'ui_store_EventBadge_2C',
            'ui_store_EventBadge_3C',
            'ui_store_EventBadge_4C',
        ])
        self.assertEqual(badge_icons[:4], badge_icons[4:])

    def test_writes_shop_and_activity_text_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_text_assets(
                tmpdir,
                event_name='Test Sale',
                banner_suffix='testsale',
                popup_title='Popup Title',
                popup_subtitle='Popup Subtitle',
                popup_desc='Popup Desc',
                main_store_text='Main Store',
                substores=[
                    {'type': 'Daily', 'pack_name': 'Pack A', 'substore_name': 'Sub A', 'substore_desc': 'Desc A'},
                    {'type': 'Special', 'pack_name': 'Pack B', 'substore_name': 'Sub B', 'substore_desc': 'Desc B'},
                ],
            )

            shop_path = os.path.join(tmpdir, 'Language', 'SourceShopUI.csv')
            activity_path = os.path.join(tmpdir, 'Language', 'SourceActivityUI.csv')
            self.assertTrue(os.path.exists(shop_path))
            self.assertTrue(os.path.exists(activity_path))

            with open(shop_path, 'r', encoding='utf-8-sig', newline='') as f:
                rows = list(csv.reader(f))
            self.assertTrue(any(row[0] == 'Func_Testsale' for row in rows))
            self.assertTrue(any(row[0] == 'Func_Testsale_Daily' for row in rows))
            self.assertTrue(any(row[0] == 'StoreDesc_Testsale_Daily' for row in rows))

            with open(activity_path, 'r', encoding='utf-8-sig', newline='') as f:
                rows = list(csv.reader(f))
            self.assertTrue(any(row[0] == 'Popup_Testsale_Title' for row in rows))
            self.assertTrue(any(row[0] == 'Popup_Testsale_Subtitle' for row in rows))
            self.assertTrue(any(row[0] == 'Popup_Testsale_Desc' for row in rows))


if __name__ == '__main__':
    unittest.main()
