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
    kodi_original_http_validated_claims,
)


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

    def test_hdr10_plus_is_also_reported_as_hdr10_by_kodi_parser(self):
        claims = kodi_original_http_validated_claims(
            ["hevc"],
            {"hdr10": True, "hdr10_plus": True},
        )
        self.assertEqual([CLIENT_DV8_BASE_LAYER_FALLBACK], claims)

    def test_dolby_vision_without_hdr10_or_hlg_does_not_enable_fallback(self):
        claims = kodi_original_http_validated_claims(
            ["hevc"],
            {"hdr10": False, "hdr10_plus": False, "hlg": False,
             "dolby_vision_profiles": []},
        )
        self.assertEqual([], claims)

    def test_unknown_output_capabilities_do_not_enable_fallback(self):
        self.assertEqual([], kodi_original_http_validated_claims(["hevc"], None))
        self.assertEqual([], kodi_original_http_validated_claims(["hevc"], {}))

    def test_missing_hevc_support_does_not_enable_fallback(self):
        self.assertEqual(
            [],
            kodi_original_http_validated_claims(
                ["h264", "av1"], {"hdr10": True}
            ),
        )

    def test_codec_matching_is_case_and_whitespace_insensitive(self):
        self.assertEqual(
            [CLIENT_DV8_BASE_LAYER_FALLBACK],
            kodi_original_http_validated_claims(
                [" HEVC "], {"hdr10": True}
            ),
        )


if __name__ == "__main__":
    unittest.main()
