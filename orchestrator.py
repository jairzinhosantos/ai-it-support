import json
import logging
import asyncio
import os
import time
from flask import request, jsonify
from services.azopenai import AzureOpenAIClient
from services.aisearch import AzureAISearchClient
from services.cosmosdb import AzureCosmosDBClient
from services.ticket_trello import TrelloTicketClient
from config.config import Config


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Azure SDK logging level to WARNING to reduce noise
azure_logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
azure_logger.setLevel(logging.WARNING)

class Orchestrator:
    """Class to handle chat interactions."""

    def __init__(self):
        try:
            # Set parameters configuration
            config = Config().config
            self.azurecosmos = AzureCosmosDBClient()            
            self.gpt4o_name = config["model"]["deployments"]["gpt-4o"]["name"]
            self.gpt4o_input_price = config["model"]["deployments"]["gpt-4o"]["price"]["input_tokens"]
            self.gpt4o_output_price = config["model"]["deployments"]["gpt-4o"]["price"]["output_tokens"]
            self.gpt4o_mini_name = config["model"]["deployments"]["gpt-4o-mini"]["name"]
            self.gpt4o_mini_input_price = config["model"]["deployments"]["gpt-4o-mini"]["price"]["input_tokens"]
            self.gpt4o_mini_output_price = config["model"]["deployments"]["gpt-4o-mini"]["price"]["output_tokens"]

            self.prompts_path = config["model"]["prompt"]["path"]
            self.system_prompt = config["model"]["prompt"]["system_prompt"]

            self.tools_path = config["model"]["parameters"]["tools"]["path"]
            self.tools = config["model"]["parameters"]["tools"]["file"]
            self.tool_choice = config["model"]["parameters"]["tools"]["tool_choice"]

            self.functions_path = config["model"]["parameters"]["functions"]["path"]
            self.functions = config["model"]["parameters"]["functions"]["file"]
            self.function_call = config["model"]["parameters"]["functions"]["function_call"]

            self.data_path = config["model"]["data"]["path"]
            self.data = config["model"]["data"]["file"]
            logger.info("Configuration loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
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
    
    def parse_structured_response(self, response_data):
        """
        Parsea la respuesta estructurada del modelo según los escenarios definidos en el prompt:
        1. Respuesta simple (solo answer)
        2. Respuesta con opciones (answer + options)
        3. Respuesta con KB (answer con pasos + options para confirmar)
        4. Respuesta con ticket (answer + ticket_summary)
        5. Respuesta con estado de ticket (answer con estado traducido)
        """
        try:
            # Convertir string a dict si es necesario
            if isinstance(response_data, str):
                try:
                    parsed_data = json.loads(response_data)
                except json.JSONDecodeError:
                    return {
                        "flag_kb": False,
                        "flag_options": False,
                        "flag_ticket": False,
                        "answer": str(response_data),
                        "options": [],
                        "ticket_summary": None
                    }
            elif isinstance(response_data, dict):
                parsed_data = response_data
            else:
                raise ValueError(f"Unexpected response type: {type(response_data)}")

            # Extraer campos base
            structured_response = {
                "flag_kb": parsed_data.get("flag_kb", False),
                "flag_options": parsed_data.get("flag_options", False),
                "flag_ticket": parsed_data.get("flag_ticket", False),
                "answer": parsed_data.get("answer", ""),
                "options": parsed_data.get("options", []),
                "ticket_summary": parsed_data.get("ticket_summary")
            }

            return structured_response

        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return {
                "flag_kb": False,
                "flag_options": False,
                "flag_ticket": False,
                "answer": "Error procesando la respuesta",
                "options": [],
                "ticket_summary": None
            }

    def format_response_for_frontend(self, structured_response):
        """
        Formatea la respuesta para el frontend según los diferentes escenarios del prompt.
        """
        response = {
            "type": "simple",  # Tipo por defecto
            "message": structured_response["answer"]
        }

        # Escenario: Respuesta con KB (pasos de solución)
        if structured_response["flag_kb"]:
            response["type"] = "knowledge_base"
            # Si hay KB, siempre habrá opciones de confirmación
            response["options"] = structured_response["options"]  # ["Completado ✅", "No funciona ❌"]

        # Escenario: Respuesta con opciones (sin KB)
        elif structured_response["flag_options"]:
            response["type"] = "options"
            response["options"] = structured_response["options"]

        # Escenario: Respuesta con ticket
        if structured_response["flag_ticket"] and structured_response["ticket_summary"]:
            response["type"] = "ticket"
            ticket = structured_response["ticket_summary"]
            
            # Formatear información del ticket de manera amigable
            ticket_info = {
                "id": ticket["ticket_id"],
                "tipo": ticket["issue_type"],
                "prioridad": ticket["priority"],
                "estado": ticket["status"],
                "usuario": ticket["user_name"]
            }
            if "asset_tag" in ticket and ticket["asset_tag"]:
                ticket_info["activo"] = ticket["asset_tag"]
                
            response["ticket"] = ticket_info

        return response

    async def run_stream(self, session_id, query):
        """Processes the chat request with streaming response."""
        try:
            start_time = time.time()
            logger.info("Starting streaming chat response processing...")
            
            azurezopenai = AzureOpenAIClient()
            azureaisearch = AzureAISearchClient()

            model_gpt4o = self.gpt4o_name
            model_gpt4o_mini = self.gpt4o_mini_name

            if not query or not session_id:
                logger.error("query or session_id not provided")
                yield f"data: {json.dumps({'error': 'query or session_id not provided'})}\n\n"
                return

            # Load system prompt and data
            system_prompt = self.read_file(os.path.join(self.prompts_path, self.system_prompt))

            message_user = [{"role": "user", "content": f"'''{query}'''"}]
            messages_history = await self.azurecosmos.get_chat_history_async(session_id)

            # Initialize variables for streaming
            full_content = ""
            input_tokens = 0
            output_tokens = 0
            model_used = model_gpt4o

            # Start streaming from Azure OpenAI (without function calling for streaming)
            logger.info("Starting streaming from Azure OpenAI...")
            
            try:
                stream = azurezopenai.run_stream(
                    model_gpt4o,
                    system_prompt,
                    message_user,
                    messages_history
                    # Note: No function calling for streaming
                )

                # Debug: Check if stream is working
                logger.info("Stream generator created successfully")
                
                for chunk in stream:
                    logger.info(f"Received chunk: {chunk}")
                    
                    if chunk["type"] == "content":
                        # Send incremental content to frontend
                        full_content = chunk["full_content"]
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk['content']})}\n\n"
                    
                    elif chunk["type"] == "complete":
                        # Process complete response
                        full_content = chunk["content"]
                        input_tokens = chunk["input_tokens"]
                        output_tokens = chunk["output_tokens"]
                        model_used = chunk["model"]
                        
                        # Use the parsed response data (already processed by azopenai.py)
                        response_data = chunk["response_data"]
                        answer_text = chunk["answer"]  # The extracted answer field
                        
                        logger.info(f"Streaming completed. Answer: {answer_text}")
                        logger.info(f"Response data: {response_data}")
                        break
                    
                    elif chunk["type"] == "error":
                        logger.error(f"Streaming error: {chunk['content']}")
                        yield f"data: {json.dumps({'type': 'error', 'content': chunk['content']})}\n\n"
                        return

                logger.info(f"After streaming loop. Full content length: {len(full_content) if full_content else 0}")
                
                # After streaming is complete, try to parse the response for structured data
                if full_content:
                    logger.info("Processing full content received from streaming")
                    
                    # Parse structured response using the same logic as regular method
                    structured_response = self.parse_structured_response(response_data)
                    
                    # Format for frontend
                    frontend_response = self.format_response_for_frontend(structured_response)
                    
                    # Send additional response data (options, tickets, etc.) if any
                    if structured_response["flag_options"] and structured_response["options"]:
                        yield f"data: {json.dumps({'type': 'options', 'options': structured_response['options']})}\n\n"
                    
                    if structured_response["flag_ticket"] and structured_response["ticket_summary"]:
                        # Create ticket in Trello
                        try:
                            trello_client = TrelloTicketClient()
                            ticket_data = structured_response["ticket_summary"]
                            trello_result = trello_client.run("create", ticket_data=ticket_data)
                            
                            if trello_result.get("success"):
                                logger.info(f"Ticket created successfully in Trello: {trello_result.get('trello_card_id')}")
                                ticket_info = frontend_response.get("ticket", {})
                                ticket_info["trello_url"] = trello_result.get("trello_url")
                                ticket_info["trello_id"] = trello_result.get("trello_card_id")
                                
                                yield f"data: {json.dumps({'type': 'ticket', 'ticket': ticket_info})}\n\n"
                            else:
                                logger.error(f"Error creating ticket in Trello: {trello_result.get('error')}")
                        except Exception as e:
                            logger.error(f"Error attempting to create ticket in Trello: {e}")
                    
                    # Save to database
                    message_save = [
                        {"role": "user", "content": query},
                        {"role": "assistant", "content": json.dumps(structured_response)}
                    ]

                    # Calculate costs
                    total_tokens_cost = (
                        input_tokens * self.gpt4o_input_price +
                        output_tokens * self.gpt4o_output_price
                    )

                    # Save evaluations
                    evals_save = [{
                        "chat": {
                            "query": query,
                            "structured_response": structured_response,
                            "frontend_response": frontend_response
                        },
                        "cost": {
                            "model": model_used,
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "input_tokens_price": self.gpt4o_input_price,
                            "output_tokens_price": self.gpt4o_output_price,
                            "total_tokens_cost": total_tokens_cost,
                        },
                        "time": time.time() - start_time
                    }]

                    # Save to database asynchronously
                    await asyncio.gather(
                        self.azurecosmos.insert_items_async(
                            self.azurecosmos.container_history,
                            session_id,
                            message_save,
                            "chat_history"
                        ),
                        self.azurecosmos.insert_evals_async(session_id, evals_save)
                    )

                    # Send completion signal
                    yield f"data: {json.dumps({'type': 'complete', 'message': 'Response completed'})}\n\n"
                    
                    logger.info("Streaming chat response processing completed successfully.")
                else:
                    logger.error("No content received from streaming")
                    logger.error(f"Full content variable: '{full_content}'")
                    yield f"data: {json.dumps({'type': 'error', 'content': 'No content received'})}\n\n"
                    
            except Exception as e:
                logger.error(f"Error in streaming process: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        except Exception as e:
            logger.error(f"Error in streaming chat processing: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    async def run(self, session_id, query):
        """Processes the chat request and returns a response."""
        try:
            start_time = time.time()
            logger.info("Starting chat response processing...")
            azurezopenai = AzureOpenAIClient()
            azureaisearch = AzureAISearchClient()

            model_gpt4o=self.gpt4o_name
            model_gpt4o_mini=self.gpt4o_mini_name

            if not query or not session_id:
                logger.error("query or session_id not provided")
                return jsonify({"error": "query or session_id not provided"}), 400

            # Load system prompt and data
            system_prompt = self.read_file(os.path.join(self.prompts_path, self.system_prompt))

            functions = self.read_file(os.path.join(self.functions_path, self.functions), as_json=True)
            function_call = self.function_call

            '''
            context_results = azureaisearch.run(query)
            if not context_results:
                raise ValueError("Empty response from Azure OpenAI")
            context = [item['content'] for item in context_results]
            logger.info(f"Context: \n{context}")
            '''
            #user_input = {"CONTEXT": f"'''{context}'''", "QUERY": {query}}
            #message_user = [{"role": "user", "content": f"'''{user_input}'''"}]
            
            message_user = [{"role": "user", "content": f"'''{query}'''"}]
            
            messages_history = await self.azurecosmos.get_chat_history_async(session_id)

            result = azurezopenai.run(
                                model_gpt4o, 
                                system_prompt, 
                                message_user, 
                                messages_history,
                                # tools,
                                # tool_choice,
                                functions,
                                function_call
                                )
            
            if not result:
                raise ValueError("Empty result from Azure OpenAI")
            logger.info(f"Result received: {result}")

            response_data = result["response"]

            logger.info(f"Response data: \n{response_data}")
            logger.info(f"Type of response_data: {type(response_data)}")
            logger.info(f"Is dict: {isinstance(response_data, dict)}")
            logger.info(f"Has 'answer' key: {'answer' in response_data if isinstance(response_data, dict) else 'N/A'}")

            if isinstance(response_data, dict) and "answer" in response_data:
                answer = response_data["answer"]
                logger.info(f"Extracted answer from dict: {answer}")
            else:
                answer = response_data
                logger.info(f"Using response_data as answer: {answer}")

            logger.info(f"Final answer: \n{answer}")
            execution_time = time.time() - start_time
        
            # Parsear la respuesta estructurada
            structured_response = self.parse_structured_response(response_data)
            
            # Log para debugging
            logger.info("Parsed structured response:")
            logger.info(json.dumps(structured_response, indent=2))

            # Formatear respuesta para el frontend
            frontend_response = self.format_response_for_frontend(structured_response)
            
            # Log de la respuesta formateada
            logger.info("Formatted frontend response:")
            logger.info(json.dumps(frontend_response, indent=2))

            # Crear ticket en Trello si es necesario
            trello_result = None
            if structured_response["flag_ticket"] and structured_response["ticket_summary"]:
                try:
                    trello_client = TrelloTicketClient()
                    ticket_data = structured_response["ticket_summary"]
                    trello_result = trello_client.run("create", ticket_data=ticket_data)
                    
                    if trello_result.get("success"):
                        logger.info(f"Ticket creado exitosamente en Trello: {trello_result.get('trello_card_id')}")
                        # Agregar información del ticket de Trello a la respuesta
                        if "ticket" in frontend_response:
                            frontend_response["ticket"]["trello_url"] = trello_result.get("trello_url")
                            frontend_response["ticket"]["trello_id"] = trello_result.get("trello_card_id")
                    else:
                        logger.error(f"Error creando ticket en Trello: {trello_result.get('error')}")
                except Exception as e:
                    logger.error(f"Error al intentar crear ticket en Trello: {e}")
                    trello_result = {"success": False, "error": str(e)}

            # Guardar en el historial la respuesta completa
            message_save = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": json.dumps(structured_response)}
            ]

            # Calcular costos
            total_tokens_cost = (
                result["input_tokens"] * self.gpt4o_input_price +
                result["output_tokens"] * self.gpt4o_output_price
            )

            # Guardar evaluaciones
            evals_save = [{
                "chat": {
                    "query": query,
                    "structured_response": structured_response,
                    "frontend_response": frontend_response
                },
                "cost": {
                    "model": result["model"],
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "input_tokens_price": self.gpt4o_input_price,
                    "output_tokens_price": self.gpt4o_output_price,
                    "total_tokens_cost": total_tokens_cost,
                },
                "trello": trello_result,
                "time": time.time() - start_time
            }]

            # Guardar en base de datos
            await asyncio.gather(
                self.azurecosmos.insert_items_async(
                    self.azurecosmos.container_history,
                    session_id,
                    message_save,
                    "chat_history"
                ),
                self.azurecosmos.insert_evals_async(session_id, evals_save)
            )

            logger.info("Chat response processing completed successfully.")
            return jsonify(frontend_response), 200
        except Exception as e:
            logger.error(f"Error in chat processing: {e}")
            return jsonify({"error": str(e)}), 500