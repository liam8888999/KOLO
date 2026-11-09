"""Kodi/Silo playback capability negotiation helpers.

Dolby Vision profile detection is deliberately broader than direct-play claims.
KOLO identifies the source profile so it can explain and recover from failed
playback, but only advertises a base-layer route when the source metadata proves
that exact route.
"""

import re


CLIENT_DV8_BASE_LAYER_FALLBACK = "client_dv8_base_layer_fallback_v1"
CLIENT_MANAGED_DYNAMIC_RANGE = "client_managed_dynamic_range_v1"

DOLBY_VISION_PROFILES = {
    0: "legacy AVC-based profile",
    4: "legacy dual-layer HEVC (profile-specific conversion required)",
    5: "single-layer HEVC (no compatible HDR10 base layer)",
    7: "dual-layer HEVC (requires profile-aware conversion)",
    8: "single-layer HEVC (base-layer compatibility depends on the BL ID)",
    9: "AVC",
    10: "AV1",
    20: "MV-HEVC / 3D",
}

DV8_BASE_LAYER_RANGES = {
    1: "hdr10",
    2: "sdr",
    4: "hlg",
}


def _as_int(value):
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _normalise_codec(value):
    codec = str(value or "").strip().lower()
    aliases = {
        "h265": "hevc",
        "hev1": "hevc",
        "hvc1": "hevc",
        "avc": "h264",
        "avc1": "h264",
        "avc3": "h264",
        "dav1": "av1",
    }
    return aliases.get(codec, codec)


def _first_video_track(source_version):
    tracks = source_version.get("video_tracks") or []
    if isinstance(tracks, list):
        for track in tracks:
            if isinstance(track, dict) and (
                track.get("dv_profile") is not None
                or track.get("dolby_vision")
                or "dovi" in str(track.get("video_range_type") or "").lower()
            ):
                return track
        if tracks and isinstance(tracks[0], dict):
            return tracks[0]
    return source_version


def _profile_from_text(value):
    match = re.search(
        r"\bprofile\s*(\d{1,2})(?:\.\d+)?",
        str(value or ""),
        re.I,
    )
    if not match:
        return None
    return _as_int(match.group(1))


def dolby_vision_source_info(source_version, video_codecs=None):
    """Describe a Dolby Vision source without claiming decoder support.

    This recognises legacy and modern profiles, including unknown future
    profile IDs. Detection is informational; it does not imply that Kodi can
    decode or output the detected profile.
    """
    if not isinstance(source_version, dict):
        return None

    track = _first_video_track(source_version)
    if not isinstance(track, dict):
        return None

    profile = _as_int(track.get("dv_profile"))
    if profile is None:
        profile = _profile_from_text(
            track.get("dolby_vision")
            or track.get("video_range_type")
            or source_version.get("dolby_vision")
        )

    dv_marker = bool(
        track.get("dolby_vision")
        or track.get("dv_profile") is not None
        or "dovi" in str(track.get("video_range_type") or "").lower()
        or source_version.get("dolby_vision")
    )
    if profile is None and not dv_marker:
        return None

    # Never infer a source codec from the client's supported-codec list:
    # that list is a set of broad compatibility declarations, not source
    # metadata, and an arbitrary fallback could misclassify AVC/AV1 as HEVC.
    codec = _normalise_codec(
        track.get("codec") or source_version.get("codec_video")
    )
    bit_depth = _as_int(track.get("bit_depth"))
    compat_id = _as_int(track.get("dv_bl_compat_id"))
    base_layer_range = DV8_BASE_LAYER_RANGES.get(compat_id) if profile == 8 else None

    config_present = track.get("dv_config_present") is True
    compat_present = track.get("dv_bl_compat_id_present") is True
    base_present = track.get("dv_bl_present") is True
    enhancement_layer = str(
        track.get("dv_enhancement_layer") or ""
    ).strip().lower()
    enhancement_absent = (
        enhancement_layer == "none"
        and track.get("dv_el_present") is not True
    )
    base_layer_proven = bool(
        profile == 8
        and compat_id in DV8_BASE_LAYER_RANGES
        and config_present
        and compat_present
        and base_present
        and enhancement_absent
    )

    video_profile = "".join(
        character for character in str(track.get("profile") or "").lower()
        if character.isalnum()
    )
    kodi_base_layer_candidate = bool(
        base_layer_proven
        and codec == "hevc"
        and bit_depth == 10
        and video_profile == "main10"
    )

    if kodi_base_layer_candidate:
        strategy = "kodi_native_dolby_vision_attempt_with_silo_recovery"
    elif profile == 7:
        strategy = "kodi_native_dolby_vision_attempt_with_silo_recovery"
    elif profile == 5:
        strategy = "kodi_native_dolby_vision_attempt_with_silo_recovery"
    elif profile is not None:
        strategy = "kodi_native_dolby_vision_attempt_with_silo_recovery"
    else:
        strategy = "silo_profile_aware_adaptation"

    return {
        "profile": profile,
        "profile_description": DOLBY_VISION_PROFILES.get(
            profile, "unknown or future Dolby Vision profile"
        ),
        "codec": codec or None,
        "bit_depth": bit_depth,
        "base_layer_compatibility_id": compat_id,
        "base_layer_range": base_layer_range,
        "base_layer_proven": base_layer_proven,
        "kodi_base_layer_candidate": kodi_base_layer_candidate,
        "enhancement_layer": enhancement_layer or "unknown",
        "strategy": strategy,
    }


def is_kodi_managed_dv8_source(source_version, video_codecs=None):
    """Return true only for a provenance-proven single-layer DV8 Main 10 file."""
    info = dolby_vision_source_info(source_version, video_codecs)
    return bool(info and info.get("kodi_base_layer_candidate"))


def kodi_original_http_validated_claims(
    video_codecs, output_hdr_details, source_version=None
):
    """Return only file- and output-specific claims supported by evidence.

    Kodi's display HDR label does not expose native Dolby Vision profile
    support. It cannot justify a broad native-DV claim. The narrowly scoped
    managed-dynamic-range claim is limited to a proven single-layer Profile 8
    Main 10 base layer; the base-layer fallback additionally requires the
    active output range to match that base layer.
    """
    codecs = {_normalise_codec(codec) for codec in (video_codecs or ())}
    info = dolby_vision_source_info(source_version, codecs)
    if not info:
        return []

    source_codec = _normalise_codec(info.get("codec"))
    if not source_codec or source_codec not in codecs:
        return []

    # This claim tells Silo that Kodi's native player is allowed to receive
    # the original HDR/Dolby Vision stream and resolve its presentation. It is
    # intentionally profile-agnostic: Kodi attempts the original and reports
    # decoder/startup failure, at which point KOLO requests a Silo fallback.
    claims = [CLIENT_MANAGED_DYNAMIC_RANGE]

    # The narrower base-layer claim remains specific to a proven DV8 stream
    # whose compatibility range matches the active display output.
    if info.get("kodi_base_layer_candidate"):
        output = output_hdr_details if isinstance(output_hdr_details, dict) else {}
        base_range = info.get("base_layer_range")
        if (
            (base_range == "hdr10" and output.get("hdr10") is True)
            or (base_range == "hlg" and output.get("hlg") is True)
        ):
            claims.insert(0, CLIENT_DV8_BASE_LAYER_FALLBACK)

    return claims
