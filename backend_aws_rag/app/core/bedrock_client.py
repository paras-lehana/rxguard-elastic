"""
AWS client factory — thread-safe, lazy-initialized singletons.

Provides 3 clients:
  • bedrock-agent          — KB management (list data sources, etc.)
  • bedrock-agent-runtime  — RAG search (retrieve_and_generate)
  • kendra                 — Document operations (BatchPutDocument, etc.)

Usage:
    from app.core.bedrock_client import get_bedrock_clients
    clients = get_bedrock_clients()
    clients.agent_runtime.retrieve_and_generate(...)
    clients.kendra.batch_put_document(...)
"""

import logging
from functools import lru_cache

import boto3

from app.config import get_settings

logger = logging.getLogger(__name__)


class BedrockClients:
    """
    Lazy-initialized boto3 client container.
    
    Three clients:
      • bedrock-agent          — KB metadata operations
      • bedrock-agent-runtime  — RAG search (retrieve_and_generate)
      • kendra                 — Document CRUD (the actual Kendra index)
    """

    def __init__(self):
        self._settings = get_settings()
        self._agent_client = None
        self._agent_runtime_client = None
        self._kendra_client = None

    def _create_session(self) -> boto3.Session:
        """Create a boto3 session with explicit credentials."""
        return boto3.Session(
            aws_access_key_id=self._settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self._settings.AWS_SECRET_ACCESS_KEY,
            region_name=self._settings.AWS_REGION,
        )

    @property
    def agent(self):
        """
        bedrock-agent client for Knowledge Base management:
          - list_data_sources()
          - list_knowledge_base_documents()
          - get_knowledge_base()
        """
        if self._agent_client is None:
            session = self._create_session()
            self._agent_client = session.client("bedrock-agent")
            logger.info("Initialized bedrock-agent client (region=%s)", self._settings.AWS_REGION)
        return self._agent_client

    @property
    def agent_runtime(self):
        """
        bedrock-agent-runtime client for RAG:
          - retrieve_and_generate()
          - retrieve()
        """
        if self._agent_runtime_client is None:
            session = self._create_session()
            self._agent_runtime_client = session.client("bedrock-agent-runtime")
            logger.info("Initialized bedrock-agent-runtime client (region=%s)", self._settings.AWS_REGION)
        return self._agent_runtime_client

    @property
    def kendra(self):
        """
        kendra client for direct document operations:
          - batch_put_document()
          - batch_delete_document()
          - list_documents()  (via query/describe_index)
        """
        if self._kendra_client is None:
            session = self._create_session()
            self._kendra_client = session.client("kendra")
            logger.info("Initialized kendra client (region=%s)", self._settings.AWS_REGION)
        return self._kendra_client


@lru_cache()
def get_bedrock_clients() -> BedrockClients:
    """Singleton client factory — cached after first call."""
    return BedrockClients()
