"""Kodi/Silo playback capability negotiation helpers."""


CLIENT_DV8_BASE_LAYER_FALLBACK = "client_dv8_base_layer_fallback_v1"
CLIENT_MANAGED_DYNAMIC_RANGE = "client_managed_dynamic_range_v1"


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return 0


def is_kodi_managed_dv8_source(source_version, video_codecs=None):
    """Return true only for a proven, single-layer DV Profile 8 Main 10 file.

    Kodi's own player will make the cross-platform decoder choice. KOLO only
    opts this exact file into Kodi-managed range handling when the Silo detail
    response proves an HEVC Main 10 video stream and a standards-compatible,
    present base layer with no enhancement layer. Unknown/legacy metadata
    deliberately fails closed.
    """
    if not isinstance(source_version, dict):
        return False

    codecs = {
        str(codec or "").strip().lower()
        for codec in (video_codecs or ())
    }
    codecs.add(str(source_version.get("codec_video") or "").strip().lower())
    tracks = source_version.get("video_tracks") or []
    if not tracks or not isinstance(tracks[0], dict):
        return False

    track = tracks[0]
    track_codec = str(track.get("codec") or "").strip().lower()
    if not ({"hevc", "h265", "hev1", "hvc1"} & (codecs | {track_codec})):
        return False

    if _as_int(track.get("dv_profile")) != 8:
        return False
    if _as_int(track.get("dv_bl_compat_id")) not in (1, 2, 4):
        return False
    if not (
        track.get("dv_config_present") is True
        and track.get("dv_bl_compat_id_present") is True
        and track.get("dv_bl_present") is True
    ):
        return False

    enhancement_layer = str(
        track.get("dv_enhancement_layer") or ""
    ).strip().lower()
    if enhancement_layer != "none" or track.get("dv_el_present") is True:
        return False

    profile = "".join(
        character for character in str(track.get("profile") or "").lower()
        if character.isalnum()
    )
    if profile != "main10" or _as_int(track.get("bit_depth")) != 10:
        return False

    return True


def kodi_original_http_validated_claims(
    video_codecs, output_hdr_details, source_version=None
):
    """Return original-HTTP claims supported by output and source evidence.

    Kodi's display HDR label does not expose native Dolby Vision profile/level
    support. It can still support Silo's narrow Profile 8 base-layer route
    when the display reports HDR10 or HLG. For an SDR output, KOLO can also
    delegate HDR-to-SDR presentation to Kodi, but only for a file whose
    Silo metadata proves a single-layer DV8 Main 10 base layer. Kodi's player
    then decides whether its platform decoder/rendering path can play it.
    """
    codecs = {
        str(codec or "").strip().lower()
        for codec in (video_codecs or ())
    }
    if "hevc" not in codecs:
        return []

    claims = []
    if isinstance(output_hdr_details, dict) and (
        output_hdr_details.get("hdr10") is True
        or output_hdr_details.get("hlg") is True
    ):
        claims.append(CLIENT_DV8_BASE_LAYER_FALLBACK)

    if is_kodi_managed_dv8_source(source_version, codecs):
        claims.append(CLIENT_MANAGED_DYNAMIC_RANGE)

    return claims
