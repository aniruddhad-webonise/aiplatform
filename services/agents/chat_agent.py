"""
Chat agent implementation.

This module implements a basic chat agent using LangChain and OpenAI.
"""
import logging
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ...core.interfaces.agent_interface import BaseAgent, AgentConfig, AgentRequest, AgentResponse, AgentType

logger = logging.getLogger(__name__)


class ChatAgent(BaseAgent):
    """
    Basic chat agent for general conversational AI.
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the chat agent.
        
        Args:
            config: Configuration for the agent
        """
        super().__init__(config)
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
        
        # Set up the default prompt template
        system_prompt = config.additional_params.get("system_prompt", """
        You are a helpful AI assistant. Provide clear, concise, and accurate responses to the user's questions.
        """)
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])
        
        self.output_parser = StrOutputParser()
        
        # Set up the chain
        self.chain = self.prompt_template | self.llm | self.output_parser
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Process a chat request and return a response.
        
        Args:
            request: The chat request
            
        Returns:
            The chat response
        """
        try:
            # Extract the input content
            input_content = request.content
            
            # Extract any additional context from the request
            context = request.context or {}
            
            # Log the request
            logger.info(f"Processing chat request: {input_content[:50]}...")
            
            # Invoke the LangChain chain
            response_content = await self.chain.ainvoke({
                "input": input_content
            })
            
            # Create and return the response
            return AgentResponse(
                content=response_content,
                success=True,
                metadata={
                    "model": self.config.model_name,
                    "agent_type": self.agent_type.value
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing chat request: {e}")
            return AgentResponse(
                content=None,
                success=False,
                error=f"Error processing chat request: {str(e)}"
            ) 