from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain
from langchain.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv
import os
import logging
import re

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Text-to-SQL Service")

class TextToSQLRequest(BaseModel):
    question: str
    schema: dict
    table_mappings: dict = None
    column_mappings: dict = None
    metric_mappings: dict = None
    data_type_rules: dict = None

class TextToSQLResponse(BaseModel):
    query: str
    explanation: str = "Generated SQL query based on the question."

def get_system_prompt(schema: dict, table_mappings: dict = None,
                     column_mappings: dict = None,
                     metric_mappings: dict = None,
                     data_type_rules: dict = None,
                     schema_prefix: str = None) -> str:
    """Generate system prompt with schema and mapping information."""
    prompt = """You are a SQL expert that converts natural language questions into SQL queries.
Follow these rules strictly:
1. Only generate SELECT queries
2. Use proper table and column names from the schema
3. Include appropriate WHERE clauses
4. Use proper SQL syntax for PostgreSQL
5. Handle date/time operations appropriately
6. Use proper aggregation functions when needed
7. Format the query for readability
8. Use correct data types in WHERE clauses based on the schema information
9. Use exact table and column names as specified in the mappings
10. Never use hardcoded values - use the mappings provided
11. ALWAYS use fully qualified table names (schema.table_name)
12. Use proper data types in WHERE clauses (e.g., integers for month/year, text for names)
13. ALWAYS use the table mappings to convert natural language table names to actual table names
14. ALWAYS use the column mappings to convert natural language column names to actual column names
15. NEVER use unqualified table names
16. NEVER use unmapped column names
17. For month/year, ALWAYS use separate integer columns (month = 1, year = 2025)
18. For text values, ALWAYS use quotes
19. For numeric values, NEVER use quotes
20. NEVER use table aliases
21. NEVER use column aliases unless explicitly required
22. ALWAYS use the exact column names from the schema
23. ALWAYS use the schema prefix before every table name otherwise query will fail
24. NEVER use table names without the schema prefix - very important
25. NEVER use table aliases (AS clause)

Schema Information:
"""
    
    # Add schema information with schema prefix
    for table_name, columns in schema.items():
        # Ensure table name has schema prefix
        if not table_name.startswith(f'{schema_prefix}.'):
            table_name = f'{schema_prefix}.{table_name}'
        prompt += f"\nTable: {table_name}\nColumns:\n"
        for col in columns:
            prompt += f"- {col['column_name']} ({col['data_type']}, {'nullable' if col['is_nullable'] else 'not nullable'})\n"
    
    # Add table mappings if provided
    if table_mappings:
        prompt += "\nTable Mappings (use these exact names in queries):\n"
        for natural_name, actual_name in table_mappings.items():
            # Ensure actual_name has schema prefix
            if not actual_name.startswith(f'{schema_prefix}.'):
                actual_name = f'{schema_prefix}.{actual_name}'
            prompt += f"- {natural_name} -> {actual_name}\n"
    
    # Add column mappings if provided
    if column_mappings:
        prompt += "\nColumn Mappings (use these exact names in queries):\n"
        for table, mappings in column_mappings.items():
            # Ensure table has schema prefix
            if not table.startswith(f'{schema_prefix}.'):
                table = f'{schema_prefix}.{table}'
            prompt += f"\nFor table {table}:\n"
            for natural_name, actual_name in mappings.items():
                prompt += f"- {natural_name} -> {actual_name}\n"
    
    # Add metric mappings if provided
    if metric_mappings:
        prompt += "\nMetric Mappings (use these exact values in queries):\n"
        for natural_name, actual_name in metric_mappings.items():
            prompt += f"- {natural_name} -> '{actual_name}'\n"
    
    # Add data type rules if provided
    if data_type_rules:
        prompt += "\nData Type Rules (use these data types in queries):\n"
        for data_type, columns in data_type_rules.items():
            prompt += f"\n{data_type.title()} columns:\n"
            for column in columns:
                prompt += f"- {column}\n"
    
    return prompt

def fix_table_and_column_names(query: str, table_mappings: dict, column_mappings: dict) -> str:
    """Fix table and column names in the query."""
    # First fix column names - handle both natural and actual names
    for table, mappings in column_mappings.items():
        for natural_name, actual_name in mappings.items():
            # Replace column names in any context
            query = re.sub(
                rf'\b{natural_name}\b',  # Word boundary to match whole words only
                actual_name,
                query,
                flags=re.IGNORECASE
            )
    
    # Then fix table names
    for natural_name, actual_name in table_mappings.items():
        # Extract the table name without schema prefix for matching
        table_name = natural_name
        if '.' in actual_name:
            schema, table = actual_name.split('.', 1)
            # Match either the natural name or the table name without schema
            pattern = rf'(FROM|JOIN)\s+({natural_name}|{table})\b'
            replacement = f"\\1 {actual_name}"
        else:
            pattern = rf'(FROM|JOIN)\s+{natural_name}\b'
            replacement = f"\\1 {actual_name}"
            
        query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
    
    return query

@app.post("/generate-sql", response_model=TextToSQLResponse)
async def generate_sql(request: TextToSQLRequest):
    """Generate SQL query from natural language question."""
    try:
        # Get schema prefix from config
        schema_prefix = request.schema.get('schema_prefix', 'affinity_gaming')
        
        # Get system prompt with schema and mappings
        system_prompt = get_system_prompt(
            request.schema,
            request.table_mappings,
            request.column_mappings,
            request.metric_mappings,
            request.data_type_rules,
            schema_prefix
        )
        
        # Initialize LangChain components
        llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Get database URL from environment variable
        db_url = os.getenv("ZCG_AFFINITY_G_DB_URL")
        if not db_url:
            raise ValueError("Database URL not found in environment variables")
            
        # Create database connection
        db = SQLDatabase.from_uri(db_url)
        
        # Create the SQL chain
        chain = create_sql_query_chain(llm, db)
        
        # Generate the SQL query
        query = chain.invoke({"question": request.question})
        logger.info(f"Generated SQL query: {query}")
        
        # Fix table and column names
        if request.table_mappings and request.column_mappings:
            query = fix_table_and_column_names(query, request.table_mappings, request.column_mappings)
            logger.info(f"Fixed SQL query: {query}")
        
        return TextToSQLResponse(query=query, explanation="Generated SQL query based on the question.")
        
    except Exception as e:
        logger.error(f"Error generating SQL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 