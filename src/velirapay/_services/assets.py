"""The /v1/assets endpoint."""

from __future__ import annotations

from .._page import Page
from .._params import AssetListParams
from .._resources.supported_asset import SupportedAsset
from ._base import Service


class AssetService(Service):
    """The /v1/assets endpoint."""

    __slots__ = ()

    def list(self, params: AssetListParams | None = None) -> Page[SupportedAsset]:
        """List the coins that can be paid in the API key's mode, with the lowest price each can be charged at, in one page."""
        return self._page("/v1/assets", params, SupportedAsset)
