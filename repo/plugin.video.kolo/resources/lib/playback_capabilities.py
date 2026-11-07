"""Conservative Kodi playback capability claims sent to Silo."""


CLIENT_DV8_BASE_LAYER_FALLBACK = "client_dv8_base_layer_fallback_v1"
CLIENT_MANAGED_DYNAMIC_RANGE = "client_managed_dynamic_range_v1"


def kodi_original_http_validated_claims(
    video_codecs, output_hdr_details, client_manages_dynamic_range=False
):
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

    claims = []
    if isinstance(output_hdr_details, dict) and (
        output_hdr_details.get("hdr10") is True
        or output_hdr_details.get("hlg") is True
    ):
        claims.append(CLIENT_DV8_BASE_LAYER_FALLBACK)

    # This is intentionally opt-in. Kodi installations differ in decoder,
    # renderer and display behaviour; only send the broad, original_http-
    # scoped managed-range claim when the user has verified Kodi's handling
    # on this device and explicitly enables the advanced setting.
    if client_manages_dynamic_range:
        claims.append(CLIENT_MANAGED_DYNAMIC_RANGE)

    return claims
