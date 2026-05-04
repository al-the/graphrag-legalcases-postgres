from __future__ import annotations

from fastapi_app.connectors.base import BaseConnector


class ConnectorRegistry:
    _connectors: dict[str, BaseConnector] = {}

    def __init__(self):
        self._load_defaults()

    def _load_defaults(self):
        from fastapi_app.connectors.hansard.connector import HansardConnector
        from fastapi_app.connectors.bursa.connector import BursaConnector
        from fastapi_app.connectors.dosm.connector import DOSMConnector
        from fastapi_app.connectors.oecd.connector import OECDConnector
        from fastapi_app.connectors.fatf.connector import FATFConnector

        for connector in [
            HansardConnector(),
            BursaConnector(),
            DOSMConnector(),
            OECDConnector(),
            FATFConnector(),
        ]:
            self._connectors[connector.source_key] = connector

    def get(self, source_key: str) -> BaseConnector | None:
        return self._connectors.get(source_key)

    def all(self) -> list[BaseConnector]:
        return list(self._connectors.values())
