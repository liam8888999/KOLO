"""Tests for conservative Kodi-to-Silo playback capability claims."""

import sys
import unittest
from pathlib import Path


PLUGIN_LIB = (
    Path(__file__).resolve().parents[1]
    / "repo"
    / "plugin.video.kolo"
    / "resources"
    / "lib"
)
sys.path.insert(0, str(PLUGIN_LIB))

from playback_capabilities import (  # noqa: E402
    CLIENT_DV8_BASE_LAYER_FALLBACK,
    CLIENT_MANAGED_DYNAMIC_RANGE,
    is_kodi_managed_dv8_source,
    kodi_original_http_validated_claims,
)


def safe_dv8_version():
    return {
        "codec_video": "hevc",
        "video_tracks": [{
            "codec": "hevc",
            "profile": "Main 10",
            "bit_depth": 10,
            "dv_profile": 8,
            "dv_bl_compat_id": 1,
            "dv_config_present": True,
            "dv_bl_compat_id_present": True,
            "dv_bl_present": True,
            "dv_el_present": False,
            "dv_enhancement_layer": "none",
            "hdr10_plus": True,
        }],
    }


class KodiOriginalHTTPClaimsTests(unittest.TestCase):
    def test_hdr10_and_hevc_enable_profile8_base_layer_claim(self):
        claims = kodi_original_http_validated_claims(
            ["h264", "hevc", "av1"],
            {"hdr10": True, "hdr10_plus": False, "hlg": False,
             "dolby_vision_profiles": []},
        )
        self.assertEqual([CLIENT_DV8_BASE_LAYER_FALLBACK], claims)

    def test_hlg_and_hevc_enable_profile8_base_layer_claim(self):
        claims = kodi_original_http_validated_claims(
            ["hevc"],
            {"hdr10": False, "hlg": True},
        )
        self.assertEqual([CLIENT_DV8_BASE_LAYER_FALLBACK], claims)

    def test_dolby_vision_without_hdr10_or_hlg_does_not_enable_output_claim(self):
        claims = kodi_original_http_validated_claims(
            ["hevc"],
            {"hdr10": False, "hdr10_plus": False, "hlg": False,
             "dolby_vision_profiles": []},
        )
        self.assertEqual([], claims)

    def test_unknown_output_capabilities_do_not_enable_base_layer_claim(self):
        self.assertEqual([], kodi_original_http_validated_claims(["hevc"], None))
        self.assertEqual([], kodi_original_http_validated_claims(["hevc"], {}))

    def test_missing_hevc_support_does_not_enable_claims(self):
        self.assertEqual(
            [],
            kodi_original_http_validated_claims(
                ["h264", "av1"], {"hdr10": True}, safe_dv8_version()
            ),
        )

    def test_codec_matching_is_case_and_whitespace_insensitive(self):
        self.assertEqual(
            [CLIENT_DV8_BASE_LAYER_FALLBACK],
            kodi_original_http_validated_claims(
                [" HEVC "], {"hdr10": True}
            ),
        )

    def test_proven_single_layer_dv8_main10_is_managed_automatically(self):
        version = safe_dv8_version()
        self.assertTrue(is_kodi_managed_dv8_source(version, ["hevc"]))
        self.assertEqual(
            [CLIENT_MANAGED_DYNAMIC_RANGE],
            kodi_original_http_validated_claims(["hevc"], None, version),
        )

    def test_dv8_managed_claim_can_coexist_with_hdr_output_claim(self):
        self.assertEqual(
            [CLIENT_DV8_BASE_LAYER_FALLBACK, CLIENT_MANAGED_DYNAMIC_RANGE],
            kodi_original_http_validated_claims(
                ["hevc"], {"hdr10": True}, safe_dv8_version()
            ),
        )

    def test_dv5_never_receives_managed_dynamic_range_claim(self):
        version = safe_dv8_version()
        version["video_tracks"][0]["dv_profile"] = 5
        self.assertFalse(is_kodi_managed_dv8_source(version, ["hevc"]))
        self.assertEqual(
            [],
            kodi_original_http_validated_claims(["hevc"], None, version),
        )

    def test_dv8_requires_proven_base_layer_and_no_enhancement_layer(self):
        for key, value in (
            ("dv_config_present", False),
            ("dv_bl_compat_id_present", False),
            ("dv_bl_present", False),
            ("dv_el_present", True),
            ("dv_enhancement_layer", "unknown"),
        ):
            version = safe_dv8_version()
            version["video_tracks"][0][key] = value
            self.assertFalse(
                is_kodi_managed_dv8_source(version, ["hevc"]),
                "unsafe source unexpectedly accepted for %s" % key,
            )

    def test_dv8_requires_supported_base_layer_compatibility_id(self):
        for compat_id in (0, 3, 5, 6, 7):
            version = safe_dv8_version()
            version["video_tracks"][0]["dv_bl_compat_id"] = compat_id
            self.assertFalse(is_kodi_managed_dv8_source(version, ["hevc"]))

    def test_dv8_requires_hevc_main10_ten_bit(self):
        for key, value in (("profile", "Main"), ("bit_depth", 8), ("codec", "h264")):
            version = safe_dv8_version()
            version["video_tracks"][0][key] = value
            self.assertFalse(is_kodi_managed_dv8_source(version, ["hevc"]))


if __name__ == "__main__":
    unittest.main()
