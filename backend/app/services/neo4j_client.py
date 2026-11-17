import os
from neo4j import GraphDatabase, Driver
from app.core.config import settings
from app.schemas.graph import GraphHealthResponse

try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass


class Neo4jClientManager:
    def __init__(self):
        self._driver: Driver | None = None

    def initialize(self) -> None:
        if not settings.neo4j_uri:
            return
        if not self._driver:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
                max_connection_lifetime=300,
                connection_timeout=8.0,
            )

    def get_driver(self) -> Driver:
        if not self._driver:
            self.initialize()
        if not self._driver:
            raise RuntimeError("Neo4j driver is not initialized. Check NEO4J_URI configuration.")
        return self._driver

    def close(self) -> None:
        if self._driver:
            try:
                self._driver.close()
            except Exception:
                pass
            self._driver = None

    def verify_connectivity(self) -> GraphHealthResponse:
        uri_configured = bool(settings.neo4j_uri)
        if not uri_configured:
            return GraphHealthResponse(
                connected=False,
                uri_configured=False,
                database=settings.neo4j_database,
                message="Neo4j URI is not configured in backend/.env",
            )
        try:
            driver = self.get_driver()
            driver.verify_connectivity()
            return GraphHealthResponse(
                connected=True,
                uri_configured=True,
                database=settings.neo4j_database,
                message="Successfully connected to Neo4j instance.",
            )
        except Exception as e:
            return GraphHealthResponse(
                connected=False,
                uri_configured=True,
                database=settings.neo4j_database,
                message=f"Connection failed: {str(e)}",
            )


neo4j_driver = Neo4jClientManager()