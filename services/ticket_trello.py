import os
import json
import logging
import requests
from dotenv import load_dotenv
from config.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrelloTicketClient:
    """Class to interact with Trello API for ticket management."""

    def __init__(self):
        try:
            # Set parameters from config
            config = Config().config
            self.trello_config = config.get("trello", {})
            self.default_board_id = self.trello_config.get("default_board_id")
            self.default_list_id = self.trello_config.get("default_list_id")  # Lista "Pendientes"
            self.priority_labels = self.trello_config.get("priority_labels", {})
            self.issue_type_labels = self.trello_config.get("issue_type_labels", {})
            logger.info("Trello configuration loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading Trello configuration: {e}")
            raise

    @staticmethod
    def load_env_var():
        """Loads necessary environment variables for Trello API."""
        try:
            load_dotenv()
            required_vars = [
                "TRELLO_API_KEY",
                "TRELLO_TOKEN",
                "TRELLO_BOARD_ID"
            ]
            
            # Priority-based list variables
            priority_vars = [
                "TRELLO_LIST_HIGH_PRIORITY_ID",
                "TRELLO_LIST_MEDIUM_PRIORITY_ID", 
                "TRELLO_LIST_LOW_PRIORITY_ID"
            ]
            
            # Optional status-based lists for updates
            status_vars = [
                "TRELLO_LIST_IN_PROGRESS_ID",
                "TRELLO_LIST_COMPLETED_ID",
                "TRELLO_LIST_CLOSED_ID"
            ]
            
            # Load all variables
            all_vars = required_vars + priority_vars + status_vars
            env_vars = {var: os.getenv(var) for var in all_vars}
            
            # Check only required vars
            missing_required = [var for var in required_vars if not env_vars[var]]
            if missing_required:
                logger.error(f"Missing required Trello environment variables: {', '.join(missing_required)}")
                raise ValueError(f"Missing required Trello environment variables: {', '.join(missing_required)}")
            
            # Check priority vars (now optional for backwards compatibility)
            missing_priority = [var for var in priority_vars if not env_vars[var]]
            configured_priority = [var for var in priority_vars if env_vars[var]]
            
            if configured_priority:
                # If some priority lists are configured, warn about missing ones
                if missing_priority:
                    logger.warning(f"Some priority list variables not configured: {', '.join(missing_priority)}")
                else:
                    logger.info("All priority list variables configured successfully.")
            else:
                # If no priority lists are configured, check if legacy lists exist
                legacy_lists = ["TRELLO_LIST_PENDING_ID", "TRELLO_LIST_IN_PROGRESS_ID", "TRELLO_LIST_COMPLETED_ID", "TRELLO_LIST_CLOSED_ID"]
                configured_legacy = [var for var in legacy_lists if env_vars.get(var)]
                
                if configured_legacy:
                    logger.info(f"Using legacy list configuration: {', '.join(configured_legacy)}")
                else:
                    logger.error("No list configuration found! Please configure either priority-based or legacy lists.")
                    raise ValueError("No Trello list configuration found. Please check your environment variables.")
            
            # Check status vars silently (only log if at least one is configured)
            missing_status = [var for var in status_vars if not env_vars[var]]
            configured_status = [var for var in status_vars if env_vars[var]]
            if configured_status:
                if missing_status:
                    logger.warning(f"Some optional status list variables not configured: {', '.join(missing_status)}")
                else:
                    logger.info("All status list variables configured successfully.")
            # If none are configured, we skip the warning (they're truly optional)
            
            logger.info("Trello environment variables loaded successfully.")
            return env_vars
        except Exception as e:
            logger.error(f"Error loading Trello environment variables: {e}")
            raise

    def get_trello_headers(self, env_vars):
        """Returns the authorization parameters for Trello API."""
        return {
            'key': env_vars["TRELLO_API_KEY"],
            'token': env_vars["TRELLO_TOKEN"]
        }

    def _get_list_id_by_priority(self, priority, env_vars):
        """Returns the appropriate list ID based on ticket priority with fallback compatibility."""
        
        # Priority-based mapping (new system)
        priority_list_mapping = {
            'alta': env_vars.get("TRELLO_LIST_HIGH_PRIORITY_ID"),
            'high': env_vars.get("TRELLO_LIST_HIGH_PRIORITY_ID"),
            'media': env_vars.get("TRELLO_LIST_MEDIUM_PRIORITY_ID"),
            'medium': env_vars.get("TRELLO_LIST_MEDIUM_PRIORITY_ID"),
            'baja': env_vars.get("TRELLO_LIST_LOW_PRIORITY_ID"),
            'low': env_vars.get("TRELLO_LIST_LOW_PRIORITY_ID")
        }
        
        # Get list ID from priority mapping
        list_id = priority_list_mapping.get(priority.lower() if priority else None)
        
        # Fallback to legacy system if new priority lists aren't configured
        if not list_id:
            logger.warning(f"No priority-specific list configured for '{priority}', trying fallback options...")
            
            # Legacy fallback mapping (for backwards compatibility)
            legacy_fallbacks = {
                'alta': env_vars.get("TRELLO_LIST_IN_PROGRESS_ID"),  # High priority -> In Progress
                'high': env_vars.get("TRELLO_LIST_IN_PROGRESS_ID"),
                'media': env_vars.get("TRELLO_LIST_PENDING_ID"),     # Medium priority -> Pending (if exists)
                'medium': env_vars.get("TRELLO_LIST_PENDING_ID"),
                'baja': env_vars.get("TRELLO_LIST_COMPLETED_ID"),    # Low priority -> Completed
                'low': env_vars.get("TRELLO_LIST_COMPLETED_ID")
            }
            
            list_id = legacy_fallbacks.get(priority.lower() if priority else None)
            
            if list_id:
                logger.info(f"Using legacy fallback list for priority '{priority}': {list_id}")
            else:
                # Final fallback: try any available list
                available_lists = [
                    env_vars.get("TRELLO_LIST_MEDIUM_PRIORITY_ID"),
                    env_vars.get("TRELLO_LIST_PENDING_ID"),
                    env_vars.get("TRELLO_LIST_IN_PROGRESS_ID"),
                    env_vars.get("TRELLO_LIST_HIGH_PRIORITY_ID"),
                    env_vars.get("TRELLO_LIST_LOW_PRIORITY_ID")
                ]
                
                list_id = next((lst for lst in available_lists if lst), None)
                
                if list_id:
                    logger.warning(f"Using first available list as fallback: {list_id}")
                else:
                    logger.error("No valid list ID found in any configuration!")
        
        return list_id

    def create_ticket(self, ticket_data):
        """Creates a new ticket in Trello."""
        try:
            env_vars = self.load_env_var()
            auth_params = self.get_trello_headers(env_vars)
            
            # Use environment variables or fallback to config
            board_id = self.default_board_id or env_vars["TRELLO_BOARD_ID"]
            
            # Get the correct list based on priority
            priority = ticket_data.get('priority', 'Media')
            list_id = self._get_list_id_by_priority(priority, env_vars)
            
            logger.info(f"Creating ticket with priority '{priority}' in list ID: {list_id}")
            
            # Prepare card data
            card_name = f"[{ticket_data.get('issue_type', 'Soporte')}] - {ticket_data.get('user_name', 'Usuario')}"
            
            # Create description with ticket details
            description_lines = [
                f"**ID del Ticket:** {ticket_data.get('ticket_id', 'N/A')}",
                f"**Usuario:** {ticket_data.get('user_name', 'N/A')}",
                f"**Tipo de Problema:** {ticket_data.get('issue_type', 'N/A')}",
                f"**Prioridad:** {ticket_data.get('priority', 'Media')}",
                f"**Estado:** {ticket_data.get('status', 'Pendiente')}",
                "",
                f"**Descripción:**",
                f"{ticket_data.get('description', 'Sin descripción proporcionada')}",
                ""
            ]
            
            if ticket_data.get('asset_tag'):
                description_lines.insert(-2, f"**Tag del Activo:** {ticket_data.get('asset_tag')}")
            
            description = "\n".join(description_lines)
            
            # Prepare API request
            url = "https://api.trello.com/1/cards"
            params = {
                **auth_params,
                'idList': list_id,
                'name': card_name,
                'desc': description,
                'pos': 'top'  # Colocar al inicio de la lista
            }
            
            # Debug logging for request parameters
            safe_params = {k: v for k, v in params.items() if k not in ['key', 'token']}
            safe_params['key'] = f"{params['key'][:8]}..."
            safe_params['token'] = f"{params['token'][:8]}..."
            logger.info(f"Sending request to Trello API: {url}")
            logger.info(f"Request params: {safe_params}")
            
            response = requests.post(url, params=params)
            
            # Debug logging
            logger.info(f"Trello API Response Status: {response.status_code}")
            logger.info(f"Trello API Response Headers: {dict(response.headers)}")
            logger.info(f"Trello API Response Content: {response.text[:500]}...")  # First 500 chars
            
            response.raise_for_status()
            
            # Better JSON parsing with error handling
            try:
                card_data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response content: {response.text}")
                raise ValueError(f"Invalid JSON response from Trello API: {response.text[:200]}")
            
            trello_card_id = card_data['id']
            
            # Add labels if configured
            self._add_labels_to_card(trello_card_id, ticket_data, env_vars)
            
            logger.info(f"Trello ticket created successfully with ID: {trello_card_id}")
            return {
                "success": True,
                "trello_card_id": trello_card_id,
                "trello_url": card_data['url'],
                "ticket_id": ticket_data.get('ticket_id')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating Trello ticket: {e}")
            return {"success": False, "error": str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"Trello API returned invalid JSON: {e}")
            logger.error(f"This usually means the list ID is incorrect or doesn't exist")
            return {"success": False, "error": f"Invalid list ID or API response: {list_id}"}
        except Exception as e:
            logger.error(f"Unexpected error creating Trello ticket: {e}")
            return {"success": False, "error": str(e)}

    def update_ticket(self, trello_card_id, update_data):
        """Updates an existing ticket in Trello."""
        try:
            env_vars = self.load_env_var()
            auth_params = self.get_trello_headers(env_vars)
            
            url = f"https://api.trello.com/1/cards/{trello_card_id}"
            params = {**auth_params}
            
            # Get current card data
            current_card = requests.get(url, params=params)
            if current_card.status_code == 200:
                card_data = current_card.json()
                current_name = card_data['name']
                current_desc = card_data['desc']
                
                # Update card name if status changed
                if 'status' in update_data:
                    new_status = update_data['status']
                    # Update name to reflect new status
                    new_name = f"{current_name} - {new_status}"
                    params['name'] = new_name
                    
                    # Update description with new status
                    updated_desc = self._update_description_status(current_desc, new_status)
                    params['desc'] = updated_desc
                    
                    # Move to different list based on status
                    new_list_id = self._get_list_id_by_status(new_status, env_vars)
                    if new_list_id:
                        params['idList'] = new_list_id
                        logger.info(f"Moving ticket to list {new_list_id} for status '{new_status}'")
                
                # Update list if priority changed
                if 'priority' in update_data:
                    new_priority = update_data['priority']
                    new_list_id = self._get_list_id_by_priority(new_priority, env_vars)
                    params['idList'] = new_list_id
                    
                    # Update description with new priority
                    updated_desc = self._update_description_priority(current_desc, new_priority)
                    params['desc'] = updated_desc
                    
                    logger.info(f"Moving ticket to list {new_list_id} for priority '{new_priority}'")
            
            # Add comment about the update
            if 'comment' in update_data:
                self._add_comment_to_card(trello_card_id, update_data['comment'], env_vars)
            
            response = requests.put(url, params=params)
            response.raise_for_status()
            
            logger.info(f"Trello ticket {trello_card_id} updated successfully")
            return {"success": True, "trello_card_id": trello_card_id}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating Trello ticket {trello_card_id}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error updating Trello ticket {trello_card_id}: {e}")
            return {"success": False, "error": str(e)}

    def delete_ticket(self, trello_card_id):
        """Deletes a ticket from Trello."""
        try:
            env_vars = self.load_env_var()
            auth_params = self.get_trello_headers(env_vars)
            
            url = f"https://api.trello.com/1/cards/{trello_card_id}"
            params = {**auth_params}
            
            response = requests.delete(url, params=params)
            response.raise_for_status()
            
            logger.info(f"Trello ticket {trello_card_id} deleted successfully")
            return {"success": True, "trello_card_id": trello_card_id}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting Trello ticket {trello_card_id}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error deleting Trello ticket {trello_card_id}: {e}")
            return {"success": False, "error": str(e)}

    def _add_labels_to_card(self, card_id, ticket_data, env_vars):
        """Adds appropriate labels to the card based on priority and issue type."""
        try:
            auth_params = self.get_trello_headers(env_vars)
            
            # Add priority label
            priority = ticket_data.get('priority', '').lower()
            if priority in self.priority_labels:
                label_id = self.priority_labels[priority]
                self._add_label_to_card(card_id, label_id, auth_params)
            
            # Add issue type label
            issue_type = ticket_data.get('issue_type', '').lower()
            if issue_type in self.issue_type_labels:
                label_id = self.issue_type_labels[issue_type]
                self._add_label_to_card(card_id, label_id, auth_params)
                
        except Exception as e:
            logger.warning(f"Could not add labels to card {card_id}: {e}")

    def _add_label_to_card(self, card_id, label_id, auth_params):
        """Adds a specific label to a card."""
        url = f"https://api.trello.com/1/cards/{card_id}/idLabels"
        params = {**auth_params, 'value': label_id}
        requests.post(url, params=params)

    def _add_comment_to_card(self, card_id, comment, env_vars):
        """Adds a comment to a Trello card."""
        try:
            auth_params = self.get_trello_headers(env_vars)
            url = f"https://api.trello.com/1/cards/{card_id}/actions/comments"
            params = {**auth_params, 'text': comment}
            
            response = requests.post(url, params=params)
            response.raise_for_status()
            
        except Exception as e:
            logger.warning(f"Could not add comment to card {card_id}: {e}")

    def _update_description_status(self, current_desc, new_status):
        """Updates the status in the card description."""
        lines = current_desc.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('**Estado:**'):
                lines[i] = f"**Estado:** {new_status}"
                break
        return '\n'.join(lines)

    def _update_description_priority(self, current_desc, new_priority):
        """Updates the priority in the card description."""
        lines = current_desc.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('**Prioridad:**'):
                lines[i] = f"**Prioridad:** {new_priority}"
                break
        return '\n'.join(lines)

    def _get_list_id_by_status(self, status, env_vars):
        """Returns the appropriate list ID based on ticket status."""
        status_list_mapping = {
            'pendiente': env_vars.get("TRELLO_LIST_PENDING_ID"),
            'en progreso': env_vars.get("TRELLO_LIST_IN_PROGRESS_ID"),
            'completado': env_vars.get("TRELLO_LIST_COMPLETED_ID"),
            'cerrado': env_vars.get("TRELLO_LIST_CLOSED_ID")
        }
        return status_list_mapping.get(status.lower())

    def run(self, action, **kwargs):
        """Main method to execute Trello operations."""
        try:
            if action == "create":
                return self.create_ticket(kwargs.get('ticket_data', {}))
            elif action == "update":
                return self.update_ticket(
                    kwargs.get('trello_card_id'),
                    kwargs.get('update_data', {})
                )
            elif action == "delete":
                return self.delete_ticket(kwargs.get('trello_card_id'))
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"Error running Trello operation '{action}': {e}")
            return {"success": False, "error": str(e)}
