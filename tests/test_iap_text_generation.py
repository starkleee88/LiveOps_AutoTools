import csv
import os
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from iap_main import export_text_assets, get_legendary_daily_shop_icon, get_holiday_pack_icon_name


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

    def test_type_specific_indexing_for_multiple_substores_of_same_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_text_assets(
                tmpdir,
                event_name='Test Sale',
                banner_suffix='testsale',
                substores=[
                    {'type': 'Daily', 'pack_name': 'Pack A', 'substore_name': 'Sub A', 'substore_desc': 'Desc A'},
                    {'type': 'Special', 'pack_name': 'Pack B', 'substore_name': 'Sub B', 'substore_desc': 'Desc B'},
                    {'type': 'Daily', 'pack_name': 'Pack C', 'substore_name': 'Sub C', 'substore_desc': 'Desc C'},
                ],
            )

            shop_path = os.path.join(tmpdir, 'Language', 'SourceShopUI.csv')
            self.assertTrue(os.path.exists(shop_path))

            with open(shop_path, 'r', encoding='utf-8-sig', newline='') as f:
                rows = list(csv.reader(f))

            # First Daily: index 1 -> no suffix
            self.assertTrue(any(row[0] == 'Func_Testsale_Daily' and row[3] == 'Sub A' for row in rows))
            self.assertTrue(any(row[0] == 'Testsale_Daily_Pack' and row[3] == 'Pack A' for row in rows))
            self.assertTrue(any(row[0] == 'StoreDesc_Testsale_Daily' and row[3] == 'Desc A' for row in rows))

            # First Special: index 1 -> no suffix
            self.assertTrue(any(row[0] == 'Func_Testsale_Special' and row[3] == 'Sub B' for row in rows))
            self.assertTrue(any(row[0] == 'Testsale_Special_Pack' and row[3] == 'Pack B' for row in rows))
            self.assertTrue(any(row[0] == 'StoreDesc_Testsale_Special' and row[3] == 'Desc B' for row in rows))

            # Second Daily: index 2 -> _2 suffix
            self.assertTrue(any(row[0] == 'Func_Testsale_Daily_2' and row[3] == 'Sub C' for row in rows))
            self.assertTrue(any(row[0] == 'Testsale_Daily_Pack_2' and row[3] == 'Pack C' for row in rows))
            self.assertTrue(any(row[0] == 'StoreDesc_Testsale_Daily_2' and row[3] == 'Desc C' for row in rows))

    def test_holiday_pack_icon_naming_rules(self):
        # Memorial Day example
        icon1 = get_holiday_pack_icon_name('memorialday2026deal', 'Memorial Day', 'Memorial Day Sale Specials', 'Wonder Woman Memorial Day', 1958001)
        self.assertEqual(icon1, 'ui_store_memorialday2026_special_WonderWoman')

        icon2 = get_holiday_pack_icon_name('memorialday2026deal', 'Memorial Day', 'Memorial Day Sale Specials', 'Wonder Woman Fragment Memorial Day', 1958002)
        self.assertEqual(icon2, 'ui_store_memorialday2026_special_WonderWoman_Fragment')

        # Easter example
        icon3 = get_holiday_pack_icon_name('easter2026deal_02', 'Easter', 'Easter Sales Step-Up', 'ET + LET Easter', 9545002)
        self.assertEqual(icon3, 'ui_store_easter2026_daily_ET_LET')

        # Pride Day example
        icon4 = get_holiday_pack_icon_name('prideday2026deal', 'Pride', 'Pride Day StepUp Gold', 'Pride Gold I', 9561001)
        self.assertEqual(icon4, 'ui_store_prideday2026_daily_Gold_I')

        # Valentine example (with valentine abbreviation)
        icon5 = get_holiday_pack_icon_name('valentine2026deal_1', 'Valentine', 'Special Offers Valentine - Poison Team Characters', 'Special Offers Valentine - Poison Team Characters', 9535001)
        self.assertEqual(icon5, 'ui_store_valentine2026_special_PoisonTeam_Characters')


if __name__ == '__main__':
    unittest.main()
