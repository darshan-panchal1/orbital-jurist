"""
Groq Client Wrapper for LLM Interactions
"""
import json
import logging
from typing import List, Dict, Any, Optional
from groq import Groq
from config import settings

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("GroqClient")

class GroqClient:
    """Wrapper for Groq API with structured output support"""
    
    def __init__(self, model: str = None, temperature: float = None):
        self.model = model or settings.PHYSICS_MODEL
        self.temperature = temperature or settings.TEMPERATURE
        
        try:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            logger.info(f"GroqClient initialized. Model: {self.model}, Temp: {self.temperature}")
        except Exception as e:
            logger.critical(f"Failed to initialize Groq client: {e}")
            raise e
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a chat completion with optional tool calling
        """
        logger.info(f"Sending Chat Request. Messages: {len(messages)}, MaxTokens: {max_tokens or settings.MAX_TOKENS}")
        logger.debug(f"Request Payload (Last Message): {messages[-1]['content'][:100]}...")  # Log start of last msg
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens or settings.MAX_TOKENS,
        }
        
        if tools:
            logger.info(f"Attached {len(tools)} tools to request.")
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"
        
        try:
            response = self.client.chat.completions.create(**kwargs)
            logger.info("Chat Response Received.")
            parsed_result = self._parse_response(response)
            
            # Log usage/content summary
            if parsed_result.get('tool_calls'):
                logger.info(f"Response contains {len(parsed_result['tool_calls'])} tool calls.")
            else:
                content_preview = parsed_result.get('content', '')[:50].replace('\n', ' ') if parsed_result.get('content') else "None"
                logger.debug(f"Response Content: {content_preview}...")
                
            return parsed_result
            
        except Exception as e:
            logger.error(f"Groq API Error: {str(e)}")
            return {
                "error": str(e),
                "content": None,
                "tool_calls": []
            }
    
    def _parse_response(self, response) -> Dict[str, Any]:
        """Parse Groq response into standardized format"""
        try:
            message = response.choices[0].message
            
            result = {
                "content": message.content,
                "tool_calls": [],
                "finish_reason": response.choices[0].finish_reason
            }
            
            # Parse tool calls if present
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    try:
                        args = json.loads(tool_call.function.arguments)
                        result["tool_calls"].append({
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": args
                            }
                        })
                        logger.debug(f"Parsed Tool Call: {tool_call.function.name}")
                    except json.JSONDecodeError as je:
                        logger.error(f"Failed to parse arguments for tool {tool_call.function.name}: {je}")
            
            return result
        except Exception as e:
            logger.error(f"Response parsing failed: {e}")
            return {"error": "Response parsing failed", "content": None}
    
    def structured_output(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Request structured JSON output matching a schema
        """
        logger.info("Initiating Structured Output Request")
        logger.debug(f"Target Schema Keys: {list(schema.get('properties', {}).keys())}")
        
        # Add schema instruction to system message
        schema_prompt = f"\n\nYou must respond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        
        # Append to last message or create system message
        enhanced_messages = messages.copy()
        enhanced_messages[-1]["content"] += schema_prompt
        
        response = self.chat(enhanced_messages)
        
        if response.get("content"):
            try:
                # Extract JSON from response
                content = response["content"]
                logger.debug(f"Raw Structured Response: {content[:200]}...") # Log raw before parsing
                
                # Remove markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                parsed_json = json.loads(content.strip())
                logger.info("Structured JSON parsed successfully.")
                return parsed_json
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON Parsing Failed: {str(e)}")
                logger.debug(f"Failed Content: {response['content']}")
                return {
                    "error": f"Failed to parse JSON: {str(e)}",
                    "raw_content": response["content"]
                }
        
        logger.warning("Structured output request returned no content.")
        return response