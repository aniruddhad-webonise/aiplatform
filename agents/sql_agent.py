from typing import Optional, Dict, Any
import httpx
from log import logger

class SQLAgent:
    def __init__(self, config):
        self.config = config

    async def process_request(self, query: str, additional_params: Optional[Dict[str, Any]] = None) -> str:
        """Process a request using the SQL agent."""
        try:
            # Get schema prefix from additional params
            schema_prefix = additional_params.get("schema_prefix", "affinity_gaming")
            
            # Create request payload
            request = TextToSQLRequest(
                question=query,
                schema=self.config["additional_params"]["schema_config"],
                table_mappings=self.config["additional_params"]["table_mappings"],
                column_mappings=self.config["additional_params"]["column_mappings"],
                metric_mappings=self.config["additional_params"]["metric_mappings"],
                data_type_rules=self.config["additional_params"]["data_type_rules"],
                schema_prefix=schema_prefix
            )
            
            # Call the API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config['api_url']}/generate-sql",
                    json=request.dict()
                )
                response.raise_for_status()
                result = response.json()
                
                if not result.get("success", False):
                    raise ValueError(f"API error: {result.get('error', 'Unknown error')}")
                
                # Return the query as is - no postprocessing needed
                return result["query"]
                
        except Exception as e:
            logger.error(f"Error in SQL agent: {str(e)}")
            raise 