"""Conservative Kodi playback capability claims sent to Silo."""


CLIENT_DV8_BASE_LAYER_FALLBACK = "client_dv8_base_layer_fallback_v1"


def kodi_original_http_validated_claims(video_codecs, output_hdr_details):
    """Return only original-HTTP claims supported by Kodi's reported facts.

    Kodi's System.SupportedHDRTypes label reports display formats, not native
    Dolby Vision profile/level support. Do not derive native DV profile claims
    from it. Silo has a separate, narrower Profile 8 base-layer route: an
    ordinary HEVC decoder can present a compatible HDR10 or HLG base layer
    when the active output explicitly reports that range.

    Silo independently checks that the media is Profile 8, single-layer, has a
    proven compatible base layer, and fits the source's HEVC decoder
    constraints before using this claim.
    """
    codecs = {
        str(codec or "").strip().lower()
        for codec in (video_codecs or ())
    }
    if "hevc" not in codecs:
        return []

    if not isinstance(output_hdr_details, dict):
        return []
    if not (
        output_hdr_details.get("hdr10") is True
        or output_hdr_details.get("hlg") is True
    ):
        return []

    return [CLIENT_DV8_BASE_LAYER_FALLBACK]
