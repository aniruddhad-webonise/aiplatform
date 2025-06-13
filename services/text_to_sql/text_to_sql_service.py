import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SQLQuery(BaseModel):
    """SQL query generated from natural language."""
    query: str = Field(description="The generated SQL query")
    explanation: str = Field(description="Explanation of the generated query")

class TextToSQLService:
    """Service to convert natural language to SQL queries using LLM."""
    
    def __init__(self, model_name: str = "gpt-4"):
        """Initialize the text-to-SQL service.
        
        Args:
            model_name: Name of the OpenAI model to use
        """
        load_dotenv()
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.1,
            max_tokens=500
        )
        self.parser = PydanticOutputParser(pydantic_object=SQLQuery)
        
        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a SQL expert. Your task is to convert natural language questions into SQL queries.
            Given a database schema and a natural language question, generate a valid SQL query.
            
            Rules:
            1. Only generate SELECT queries
            2. Use proper table aliases
            3. Include JOINs when needed
            4. Add appropriate WHERE clauses
            5. Use proper SQL syntax for the target database (PostgreSQL, MySQL, etc.)
            6. Explain your query in simple terms
            
            Database Schema:
            {schema}
            
            {format_instructions}
            """),
            ("human", "{question}")
        ])
    
    async def generate_sql(self, 
                          question: str, 
                          schema: Dict[str, Any], 
                          db_type: str = "postgresql") -> SQLQuery:
        """Generate SQL query from natural language question.
        
        Args:
            question: Natural language question
            schema: Database schema information
            db_type: Type of database (postgresql, mysql, etc.)
            
        Returns:
            SQLQuery object containing the generated query and explanation
        """
        try:
            # Format schema information
            schema_info = self._format_schema(schema)
            
            # Generate the query
            chain = self.prompt | self.llm | self.parser
            result = await chain.ainvoke({
                "question": question,
                "schema": schema_info,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            logger.info(f"Generated SQL query: {result.query}")
            logger.info(f"Explanation: {result.explanation}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating SQL query: {str(e)}")
            raise
    
    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format schema information for the prompt.
        
        Args:
            schema: Database schema information
            
        Returns:
            Formatted schema string
        """
        schema_info = []
        
        # Add tables and their columns
        for table_name, table_info in schema.get("tables", {}).items():
            columns = [f"{col['name']} ({col['type']})" for col in table_info.get("columns", [])]
            schema_info.append(f"Table: {table_name}")
            schema_info.append("Columns:")
            schema_info.extend([f"  - {col}" for col in columns])
            schema_info.append("")
        
        # Add views
        if "views" in schema:
            schema_info.append("Views:")
            for view_name in schema["views"]:
                schema_info.append(f"  - {view_name}")
        
        return "\n".join(schema_info) 