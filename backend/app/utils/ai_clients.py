# app/utils/ai_clients.py
from __future__ import annotations
import logging
from functools import lru_cache
from typing import Optional
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from app.config import config

logger = logging.getLogger(__name__)

__all__ = [
    "get_azure_openai_client",
    "get_azure_openai_deployment",
    "get_search_client",
]

# Azure OpenAI Client
@lru_cache(maxsize=1)
def get_azure_openai_client() -> Optional[AzureOpenAI]:
    api_key = getattr(config, "AZURE_OPENAI_KEY", None)
    endpoint = getattr(config, "AZURE_OPENAI_ENDPOINT", None)
    api_version = getattr(config, "AZURE_OPENAI_VERSION", "2024-02-01")

    if not api_key or not endpoint:
        logger.warning("Azure OpenAI config missing; client not created.")
        return None
    try:
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        logger.info(" Initialized Azure OpenAI client")
        return client
    except Exception:
        logger.exception(" Failed to initialize Azure OpenAI client.")
        return None


def get_azure_openai_deployment() -> Optional[str]:
    return getattr(config, "AZURE_OPENAI_DEPLOYMENT", None)


# Azure AI Search Client
@lru_cache(maxsize=1)
def get_search_client() -> Optional[SearchClient]:
    search_key = getattr(config, "AZURE_SEARCH_KEY", None)
    search_endpoint = getattr(config, "AZURE_SEARCH_ENDPOINT", None)
    index_name = getattr(config, "AZURE_SEARCH_INDEX")

    if not search_key or not search_endpoint:
        logger.warning("Azure Cognitive Search config missing; client not created.")
        return None
    try:
        client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(search_key),
        )
        logger.info(f" Initialized Azure Search client for index: {index_name}")
        return client
    except Exception:
        logger.exception(" Failed to initialize Azure Cognitive Search client.")
        return None
