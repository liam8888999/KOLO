import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "repo", "plugin.video.kolo")))

from resources.lib.playback_capabilities import (
    CLIENT_DV8_BASE_LAYER_FALLBACK,
    CLIENT_MANAGED_DYNAMIC_RANGE,
    dolby_vision_source_info,
    is_kodi_managed_dv8_source,
    kodi_original_http_validated_claims,
)


def source(profile, codec="hevc", bit_depth=10, video_profile="Main 10",
           compat_id=1, config=True, compat_present=True, base=True,
           enhancement="none", el_present=False):
    return {"codec_video": codec, "video_tracks": [{
        "codec": codec, "profile": video_profile, "bit_depth": bit_depth,
        "dv_profile": profile, "dv_bl_compat_id": compat_id,
        "dv_config_present": config, "dv_bl_compat_id_present": compat_present,
        "dv_bl_present": base, "dv_el_present": el_present,
        "dv_enhancement_layer": enhancement,
    }]}


class DolbyVisionMetadataTests(unittest.TestCase):
    def test_profile_8_1_hdr10_base_layer_is_proven(self):
        info = dolby_vision_source_info(source(8, compat_id=1))
        self.assertEqual(info["profile"], 8)
        self.assertEqual(info["base_layer_range"], "hdr10")
        self.assertTrue(info["kodi_base_layer_candidate"])
        self.assertTrue(is_kodi_managed_dv8_source(source(8, compat_id=1)))

    def test_profile_8_2_sdr_base_layer_is_identified(self):
        info = dolby_vision_source_info(source(8, compat_id=2))
        self.assertEqual(info["base_layer_range"], "sdr")
        self.assertTrue(info["kodi_base_layer_candidate"])

    def test_profile_8_4_hlg_base_layer_is_identified(self):
        info = dolby_vision_source_info(source(8, compat_id=4))
        self.assertEqual(info["base_layer_range"], "hlg")
        self.assertTrue(info["kodi_base_layer_candidate"])

    def test_unknown_profile_8_compatibility_id_fails_closed(self):
        info = dolby_vision_source_info(source(8, compat_id=6))
        self.assertIsNone(info["base_layer_range"])
        self.assertFalse(info["kodi_base_layer_candidate"])

    def test_profile_8_requires_complete_provenance(self):
        for kwargs in ({"config": False}, {"compat_present": False}, {"base": False},
                       {"enhancement": "unknown"}, {"el_present": True},
                       {"video_profile": "Main"}, {"bit_depth": 8},
                       {"codec": "h264", "video_profile": "High", "bit_depth": 8}):
            with self.subTest(kwargs=kwargs):
                self.assertFalse(is_kodi_managed_dv8_source(source(8, **kwargs)))

    def test_profile_7_is_identified_but_not_client_base_layer_fallback(self):
        item = source(7, compat_id=6, enhancement="fel", el_present=True)
        info = dolby_vision_source_info(item)
        self.assertEqual(info["strategy"], "kodi_native_dolby_vision_attempt_with_silo_recovery")
        self.assertFalse(info["kodi_base_layer_candidate"])
        self.assertEqual([], kodi_original_http_validated_claims(["hevc"], {"hdr10": True}, item))

    def test_profile_5_does_not_claim_hdr10_base_layer(self):
        info = dolby_vision_source_info(source(5, compat_id=0))
        self.assertEqual(info["strategy"], "kodi_native_dolby_vision_attempt_with_silo_recovery")
        self.assertFalse(info["kodi_base_layer_candidate"])

    def test_legacy_and_other_profiles_are_reported_without_false_claims(self):
        cases = ((4, "hevc", 10, "Main 10"), (9, "h264", 8, "High"),
                 (10, "av1", 10, "Main 10"), (20, "hevc", 10, "Main 10"),
                 (0, "hevc", 10, "Main 10"))
        for profile, codec, depth, video_profile in cases:
            with self.subTest(profile=profile):
                info = dolby_vision_source_info(source(profile, codec, depth, video_profile, 0))
                self.assertEqual(info["profile"], profile)
                self.assertFalse(info["kodi_base_layer_candidate"])

    def test_unknown_future_profile_is_reported_for_server_negotiation(self):
        info = dolby_vision_source_info(source(21))
        self.assertEqual(info["profile"], 21)
        self.assertEqual(info["strategy"], "silo_profile_aware_adaptation")

    def test_claims_are_profile_and_output_specific(self):
        p81 = kodi_original_http_validated_claims(["hevc"], {"hdr10": True}, source(8, compat_id=1))
        self.assertIn(CLIENT_MANAGED_DYNAMIC_RANGE, p81)
        self.assertIn(CLIENT_DV8_BASE_LAYER_FALLBACK, p81)
        p84 = kodi_original_http_validated_claims(["hevc"], {"hdr10": True}, source(8, compat_id=4))
        self.assertIn(CLIENT_MANAGED_DYNAMIC_RANGE, p84)
        self.assertNotIn(CLIENT_DV8_BASE_LAYER_FALLBACK, p84)

    def test_sdr_base_layer_does_not_claim_hdr10_fallback(self):
        claims = kodi_original_http_validated_claims(["hevc"], {"hdr10": True}, source(8, compat_id=2))
        self.assertIn(CLIENT_MANAGED_DYNAMIC_RANGE, claims)
        self.assertNotIn(CLIENT_DV8_BASE_LAYER_FALLBACK, claims)

    def test_hlg_base_layer_claim_requires_hlg_output(self):
        claims = kodi_original_http_validated_claims(["hevc"], {"hlg": True}, source(8, compat_id=4))
        self.assertIn(CLIENT_DV8_BASE_LAYER_FALLBACK, claims)


    def test_all_recognised_profiles_get_native_attempt_claim(self):
        cases = (
            (0, "hevc", 10, "Main 10"),
            (4, "hevc", 10, "Main 10"),
            (5, "hevc", 10, "Main 10"),
            (7, "hevc", 10, "Main 10"),
            (8, "hevc", 10, "Main 10"),
            (9, "h264", 8, "High"),
            (10, "av1", 10, "Main 10"),
            (20, "hevc", 10, "Main 10"),
        )
        for profile, codec, depth, video_profile in cases:
            with self.subTest(profile=profile):
                item = source(profile, codec, depth, video_profile, compat_id=0)
                claims = kodi_original_http_validated_claims(
                    ["h264", "hevc", "av1"], {"hdr10": False}, item
                )
                self.assertIn(CLIENT_MANAGED_DYNAMIC_RANGE, claims)

    def test_missing_codec_or_unknown_output_fails_closed(self):
        self.assertEqual([], kodi_original_http_validated_claims(["av1"], None, source(8)))
        self.assertEqual([], kodi_original_http_validated_claims(["hevc"], None, source(8, compat_id=6)))


if __name__ == "__main__":
    unittest.main()
