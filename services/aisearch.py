import os
import logging
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from azure.search.documents.models import (
    VectorizableTextQuery,
    QueryType,
    QueryCaptionType,
    QueryAnswerType,
)
from config.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureAISearchClient:
    """Class to interact with Azure AI Search service."""

    def __init__(self):
        try:
            # Set parameters
            config = Config().config
            self.search_type = config["ai_search"]["search_type"]
            self.k_nearest_neighbors = config["ai_search"]["k_nearest_neighbors"]
            self.fields = config["ai_search"]["fields"]
            self.top = config["ai_search"]["top"]
            logger.info("Configuration loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    @staticmethod
    def load_env_var():
        """Loads necessary environment variables for Azure AI Search."""
        try:
            load_dotenv()
            required_vars = [
                    "AZURE_AI_SEARCH_ENDPOINT",
                    "AZURE_AI_SEARCH_KEY",
                    "AZURE_AI_SEARCH_INDEX_NAME",
                    "SEMANTIC_CONFIGURATION_NAME"
                ]
            env_vars = {var: os.getenv(var) for var in required_vars}
            missing_vars = [var for var, value in env_vars.items() if not value]
            if missing_vars:
                logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
                raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")
            logger.info("Azure AISearch environment variables loaded successfully.")
            return env_vars
        except Exception as e:
            logger.error(f"Error loading environment variables: {e}")
            raise
    
    @staticmethod
    def create_search_client(env_vars):
        """Creates and returns an Azure SearchClient instance."""
        try:
            credential = AzureKeyCredential(env_vars["AZURE_AI_SEARCH_KEY"]) if len(env_vars["AZURE_AI_SEARCH_KEY"]) > 0 else DefaultAzureCredential()
            client = SearchClient(
                        env_vars["AZURE_AI_SEARCH_ENDPOINT"], 
                        env_vars["AZURE_AI_SEARCH_INDEX_NAME"], 
                        credential=credential,
                    )
            logger.info("AI Search client created successfully.")
            return client
        except Exception as e:
            logger.error(f"Error creating Azure AI Search client: {e}")
            raise

    def search(self, client, query, env_vars):
        """Performs a search query using Azure AI Search."""
        try:
            vector_query = VectorizableTextQuery(
                text=query,
                k_nearest_neighbors=self.k_nearest_neighbors,
                fields=self.fields,
                exhaustive=True,
            )

            search_kwargs = {
                "search_text": None,
                "vector_queries": [vector_query],
                "top": self.top,
            }

            if self.search_type == "hybrid":
                search_kwargs["search_text"] = query
            elif self.search_type == "hybrid_semantic":
                search_kwargs.update({
                    "search_text": query,
                    "query_type": QueryType.SEMANTIC,
                    "semantic_configuration_name": env_vars["SEMANTIC_CONFIGURATION_NAME"],
                    "query_caption": QueryCaptionType.EXTRACTIVE,
                    "query_answer": QueryAnswerType.EXTRACTIVE,
                })

            response = client.search(**search_kwargs)
            return response
            
        except Exception as e:
            logger.error(f"Error getting Search from Azure AISearch: {e}")
            raise

    def run(self, query):
        """Executes the search process and returns the results."""
        try:
            env_vars = self.load_env_var()
            client = self.create_search_client(env_vars)
            search_results = self.search(client, query, env_vars)

            response = [
                    {"score": result["@search.score"], "content": result["chunk"]}
                    for result in search_results
            ]
            
            return response
        except Exception as e:
            logger.error(f"Error running Azure AI Search process: {e}")
            return {"error": str(e)}