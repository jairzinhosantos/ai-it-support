import os
import logging
import asyncio
from azure.cosmos import CosmosClient, exceptions, PartitionKey
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureCosmosDBClient:
    """Class to interact with Azure Cosmos DB."""

    def __init__(self):
        env_vars = self.load_env_var()
        self.client = self.create_cosmos_client(env_vars)
        self.database = self.client.create_database_if_not_exists(id=env_vars["COSMOS_DB_DATABASE_NAME"])
        self.container_history = self.get_container(self.database, env_vars["COSMOS_DB_CONTAINER_HISTORY"])
        self.container_evals = self.get_container(self.database, env_vars["COSMOS_DB_CONTAINER_EVALS"])

    @staticmethod
    def load_env_var():
        load_dotenv()
        required_vars = [
            "COSMOS_DB_ENDPOINT",
            "COSMOS_DB_PRIMARY_KEY",
            "COSMOS_DB_DATABASE_NAME",
            "COSMOS_DB_CONTAINER_HISTORY",
            "COSMOS_DB_CONTAINER_EVALS"
        ]
        env_vars = {var: os.getenv(var) for var in required_vars}
        missing_vars = [var for var, value in env_vars.items() if not value]
        if missing_vars:
            logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
            raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")
        return env_vars

    @staticmethod
    def create_cosmos_client(env_vars):
        try:
            return CosmosClient(
                url=env_vars["COSMOS_DB_ENDPOINT"],
                credential=env_vars["COSMOS_DB_PRIMARY_KEY"],
            )
        except Exception as e:
            logger.error(f"Error creating Cosmos Client: {e}")
            raise

    @staticmethod
    def get_container(database, container_name):
        try:
            return database.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path='/id')
            )
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to create container '{container_name}': {e}")
            raise

    async def insert_items_async(self, container, session_id, items, field):
        """Asynchronous insertion of chat history or evaluations into Cosmos DB."""
        try:
            item = container.read_item(item=session_id, partition_key=session_id)
            if field not in item:
                item[field] = []
            item[field].extend(items)
        except exceptions.CosmosResourceNotFoundError:
            item = {"id": session_id, field: items}
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to upsert items for session ID '{session_id}': {e}")
            return
        await asyncio.to_thread(container.upsert_item, item)

    async def insert_evals_async(self, session_id, evals_data):
        """Insert evaluations data asynchronously into the evals container."""
        try:
            await self.insert_items_async(self.container_evals, session_id, evals_data, "evals")
            logger.info(f"Evaluations data inserted for session ID '{session_id}'.")
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to insert evaluations for session ID '{session_id}': {e}")

    async def get_chat_history_async(self, session_id):
        """Retrieve chat history asynchronously from the Cosmos DB container."""
        try:
            item = await asyncio.to_thread(self.container_history.read_item, item=session_id, partition_key=session_id)
            return item.get('chat_history', [])
        except exceptions.CosmosResourceNotFoundError:
            return []
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Error retrieving chat history for session ID '{session_id}': {e}")
            return []
