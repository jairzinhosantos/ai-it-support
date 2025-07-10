import os
import json
import re
import logging
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AzureOpenAI
from config.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureOpenAIClient:
    """Class to interact with Azure OpenAI service."""

    def __init__(self):
        try:
            # Set parameters
            config = Config().config
            self.response_format = config["model"]["parameters"]["response_format"]
            self.temperature = config["model"]["parameters"]["temperature"]
            self.top_p = config["model"]["parameters"]["top_p"]
            self.max_tokens = config["model"]["parameters"]["max_tokens"]
            self.seed = config["model"]["parameters"]["seed"]
            logger.info("Configuration loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    @staticmethod
    def load_env_var():
        """Loads necessary environment variables for Azure OpenAI."""
        try:
            load_dotenv()
            required_vars = [
                    "AZURE_OPENAI_ENDPOINT",
                    "AZURE_OPENAI_API_KEY",
                    "AZURE_OPENAI_API_VERSION"
            ]
            env_vars = {var: os.getenv(var) for var in required_vars}
            missing_vars = [var for var, value in env_vars.items() if not value]
            if missing_vars:
                logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
                raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")
            logger.info("Azure OpenAI environment variables loaded successfully.")
            return env_vars
        except Exception as e:
            logger.error(f"Error loading environment variables: {e}")
            raise
    
    @staticmethod
    def create_openai_client(env_vars):
        """Creates and returns an Azure OpenAI client instance."""
        try:
            client = AzureOpenAI(
                azure_endpoint=env_vars["AZURE_OPENAI_ENDPOINT"],
                api_key=env_vars["AZURE_OPENAI_API_KEY"],
                api_version=env_vars["AZURE_OPENAI_API_VERSION"]
            )
            logger.info("Azure OpenAI client created successfully.")
            return client
        except Exception as e:
            logger.error(f"Error creating Azure OpenAI client: {e}")
            raise
    
    @staticmethod
    def read_file(file_path, as_json=False):
        """Reads content from a file."""
        try:
            with open(file_path, 'r') as file:
                logger.info(f"File '{file_path}' successfully loaded.")
                if as_json:
                    return json.load(file)
                else:
                    return file.read()
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON file: {file_path}")
            return ""
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return ""
    
    @staticmethod
    def parse_content(response_content):
        """Extracts JSON content from a message string."""
        # Remove JSON code block markers if present
        response_content = re.sub(r'^```json\s*', '', response_content.strip(), flags=re.MULTILINE)
        response_content = re.sub(r'^```\s*', '', response_content.strip(), flags=re.MULTILINE)
        response_content = re.sub(r'\s*```$', '', response_content.strip(), flags=re.MULTILINE)
        
        # Remove triple single quotes at the start and end, handling potential whitespace
        response_content = re.sub(r'^\s*\'\'\'|^\s*"""', '', response_content.strip())
        response_content = re.sub(r'\'\'\'\s*$|"""\s*$', '', response_content.strip())
        
        response_content = response_content.strip()
        try:
            return json.loads(response_content)
        except json.JSONDecodeError:
            return response_content  # Return the plain text if it's not JSON

    def openai_response(self, client, model, messages, tools = None, tool_choice = None, functions = None, function_call = None):
        """Gets a response from Azure OpenAI with multiple response format options."""
        try:
            completion_params = {
                "model": model,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": self.max_tokens,
                "seed": self.seed,
                "messages": messages
            }

            if self.response_format is None or self.response_format == "normal":
                completion = client.chat.completions.create(**completion_params)
                response_content = completion.choices[0].message.content
                json_data = self.parse_content(response_content)
                response = json_data if json_data else response_content
                logger.info("Azure OpenAI response generated by content.")
            elif self.response_format == "tools":
                completion_params.update({"tools": tools, "tool_choice": tool_choice})
                completion = client.chat.completions.create(**completion_params)
                tool_calls = completion.choices[0].message.tool_calls
                if tool_calls:
                    response = tool_calls[0].function.arguments
                    logger.info("Azure OpenAI response generated by tool_call.")
                else:
                    response_content = completion.choices[0].message.content
                    json_data = self.parse_content(response_content)
                    response = json_data if json_data else response_content
                    logger.warning("Azure OpenAI response generated by content, not by tool_call.")
            elif self.response_format == "function_calling":
                completion_params.update({"functions": functions, "function_call": function_call})
                completion = client.chat.completions.create(**completion_params)
                function_call = completion.choices[0].message.function_call
                if function_call:
                    #response = function_call.arguments
                    try:
                        response = json.loads(function_call.arguments)
                    except json.JSONDecodeError:
                        response = {"answer": function_call.arguments}
                    logger.info("Azure OpenAI response generated by function_call.")
                else:
                    response_content = completion.choices[0].message.content
                    json_data = self.parse_content(response_content)
                    response = json_data if json_data else response_content
                    logger.warning("Azure OpenAI response generated by content, not by function_call.")
            elif self.response_format == "base_model":
                class StructureOutput(BaseModel):
                    answer: str
                    array_intent: list[str]
                    flag_intent: bool
                completion = client.beta.chat.completions.parse(
                                **completion_params,
                                response_format=StructureOutput
                            )
                response = completion.choices[0].message.parsed.model_dump()
                logger.info("Azure OpenAI response generated by base_model.")

            else:
                raise ValueError(f"Unknown response format: {self.response_format}")

            logger.info("Response received from Azure OpenAI.")
            
            return {
                "response": response,
                "model": model,
                "input_tokens": completion.usage.prompt_tokens,
                "output_tokens": completion.usage.completion_tokens
            }
        except Exception as e:
            logger.error(f"Error getting response from Azure OpenAI: {e}")
            raise

    def run_stream(self, model, system_prompt, message, messages_history=None, tools=None, tool_choice=None, functions=None, function_call=None):
        """Executes the OpenAI chat completion process with streaming."""
        try:
            env_vars = self.load_env_var()
            client = self.create_openai_client(env_vars)

            messages = [{"role": "system", "content": f"'''{system_prompt}'''"}]
            if messages_history:
                messages.extend(messages_history)
            if message:
                messages.extend(message)

            logger.info("Starting streaming OpenAI process")
            logger.info(f"Total messages: {len(messages)}")
            
            # Direct streaming implementation
            completion_params = {
                "model": model,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": self.max_tokens,
                "seed": self.seed,
                "messages": messages,
                "stream": True
            }

            logger.info("Creating Azure OpenAI stream...")
            
            stream = client.chat.completions.create(**completion_params)
            logger.info("Stream created successfully")
            
            full_content = ""
            input_tokens = 0
            output_tokens = 0
            chunk_count = 0
            
            logger.info("Starting to process stream...")
            
            for chunk in stream:
                chunk_count += 1
                logger.info(f"Processing chunk #{chunk_count}")
                
                if chunk.choices:
                    choice = chunk.choices[0]
                    
                    if choice.delta and choice.delta.content:
                        content = choice.delta.content
                        full_content += content
                        logger.info(f"Got content: '{content}' (len: {len(content)})")
                        
                        # DON'T yield individual chunks here - collect all content first
                    
                    if choice.finish_reason:
                        logger.info(f"Finish reason: {choice.finish_reason}")
                
                # Check for usage info
                if hasattr(chunk, 'usage') and chunk.usage:
                    input_tokens = chunk.usage.prompt_tokens
                    output_tokens = chunk.usage.completion_tokens
            
            logger.info(f"Stream completed. Chunks: {chunk_count}, Content length: {len(full_content)}")
            
            # Process content like the regular method and then stream the answer
            if full_content:
                # Parse the content like the regular method does
                logger.info("Processing full content with same logic as regular method")
                json_data = self.parse_content(full_content)
                response_data = json_data if json_data else full_content
                
                logger.info(f"Parsed response data: {response_data}")
                
                # Extract the answer field like the regular method does
                if isinstance(response_data, dict) and "answer" in response_data:
                    answer_text = response_data["answer"]
                    logger.info(f"Extracted answer from dict: {answer_text}")
                else:
                    answer_text = str(response_data)
                    logger.info(f"Using response_data as answer: {answer_text}")
                
                # Now stream the answer character by character
                logger.info("Starting character-by-character streaming of answer")
                for i, char in enumerate(answer_text):
                    yield {
                        "type": "content",
                        "content": char,
                        "full_content": answer_text[:i+1]
                    }
                
                # Final completion with all data
                yield {
                    "type": "complete",
                    "content": full_content,
                    "answer": answer_text,  # Add the extracted answer
                    "response_data": response_data,  # Add the parsed response
                    "model": model,
                    "input_tokens": input_tokens if input_tokens > 0 else len(str(messages)) // 4,
                    "output_tokens": output_tokens if output_tokens > 0 else len(full_content) // 4
                }
            else:
                logger.error("No content received from streaming")
                yield {
                    "type": "error",
                    "content": "No content received from Azure OpenAI"
                }
        
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            yield {
                "type": "error",
                "content": str(e)
            }
    
    def run(self, model, system_prompt, message, messages_history = None, tools = None, tool_choice = None, functions = None, function_call = None):
        """Executes the OpenAI chat completion process."""
        try:
            env_vars = self.load_env_var()
            client = self.create_openai_client(env_vars)

            messages = [{"role": "system", "content": f"'''{system_prompt}'''"}]
            if messages_history:
                messages.extend(messages_history)
            if message:
                messages.extend(message)

            ## logger.info(f"Messages: \n{messages}")
            result = self.openai_response(client, model, messages, tools, tool_choice, functions, function_call)
            return result
        
        except Exception as e:
            logger.error(f"Error running Azure OpenAI process: {e}")
            return {"error": str(e)}