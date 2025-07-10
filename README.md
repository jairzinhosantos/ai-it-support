# IT Support AI Assistant

## Table of Contents
[Project Description](#mag-project-description)<br>
[Architecture](#building_construction-architecture)<br>
[Components](#open_file_folder-components)<br>
[Technologies Used](#hammer_and_wrench-technologies-used)<br>
[Installation & Setup](#rocket-installation--setup)<br>
[Configuration](#gear-configuration)<br>
[Usage](#computer-usage)<br>
[Contributing](#handshake-contributing)<br>
[License](#page_facing_up-license)<br>

# Generic IT Support AI Assistant 🤖💻

**`An intelligent IT support system that provides automated first-line technical assistance using conversational AI powered by Azure OpenAI.`**

## :mag: Project Description

This IT Support AI Assistant is a flexible, configurable virtual assistant designed to provide first-line technical support for organizations. The system leverages Azure OpenAI's GPT-4o model for natural language processing and integrates with multiple services to deliver a comprehensive and efficient support experience.

### Key Features

- **Conversational AI Assistant**: Responds to queries with contextual understanding
- **Intelligent Self-Service**: Provides step-by-step solutions from knowledge base
- **Automatic Ticket Management**: Creates tickets in Trello when escalation is needed
- **Multimodal Support**: Accepts both text and audio queries (automatic transcription)
- **Conversation History**: Stores and tracks all interactions
- **Flexible Configuration**: Easy to customize for different organizations and use cases

## :building_construction: Architecture

The system follows a modular microservices-based architecture that enables scalability and maintainability. For detailed architecture information, see the [architecture document](architecture.md).

## :open_file_folder: Components

### Project Structure

```
ai-it-support/
├── app.py                    # Main Flask application
├── orchestrator.py           # Central orchestration logic
├── config/
│   ├── config.json          # System configuration
│   └── config.py            # Configuration loader
├── services/
│   ├── azopenai.py          # Azure OpenAI client
│   ├── aisearch.py          # Azure AI Search client
│   ├── cosmosdb.py          # Azure Cosmos DB client
│   ├── ticket_trello.py     # Trello ticket client
│   └── whisper.py           # Whisper audio client
├── prompts/
│   └── it-support-agent.prompt # System prompt
├── tools_functions/
│   └── it_support_ai.json   # AI function definitions
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/
│   └── index.html           # Web interface
└── requirements.txt         # Python dependencies
```

### Component Descriptions

#### Core Components

- **`app.py`**: Main Flask application entry point. Handles HTTP routes (`/`, `/chat`), user sessions, and audio/text processing.
  - `handle_text_request()`: Processes text-based chat requests
  - `handle_audio_request()`: Processes audio-based chat requests with Whisper transcription
  - `start_app()`: Launches the Flask application

- **`orchestrator.py`**: Core orchestration logic that coordinates all services and manages conversation flow.
  - `run()`: Main processing method that handles the complete request lifecycle
  - `parse_structured_response()`: Parses structured responses from the AI model
  - `format_response_for_frontend()`: Formats responses for the web interface

#### Service Layer

- **`services/azopenai.py`**: Azure OpenAI client (`AzureOpenAIClient`)
  - `run()`: Executes chat completion with function calling
  - `openai_response()`: Handles different response formats (normal, tools, function_calling)
  - `parse_content()`: Parses and cleans AI responses

- **`services/cosmosdb.py`**: Azure Cosmos DB client (`AzureCosmosDBClient`)
  - `get_chat_history_async()`: Retrieves conversation history asynchronously
  - `insert_items_async()`: Inserts chat history items
  - `insert_evals_async()`: Inserts evaluation metrics

- **`services/ticket_trello.py`**: Trello API client (`TrelloTicketClient`)
  - `create_ticket()`: Creates new tickets with priority-based list assignment
  - `update_ticket()`: Updates existing tickets
  - `_get_list_id_by_priority()`: Maps ticket priority to Trello lists

- **`services/aisearch.py`**: Azure AI Search client (`AzureAISearchClient`)
  - `run()`: Executes semantic search queries
  - `search()`: Performs hybrid/semantic search with vector queries

- **`services/whisper.py`**: Audio transcription client (`WhisperClient`)
  - `run()`: Transcribes audio to text using Azure OpenAI Whisper

#### Configuration System

- **`config/config.py`**: Configuration loader class (`Config`)
  - `load_config()`: Loads configuration from JSON file
  - Handles configuration errors gracefully

- **`config/config.json`**: Centralized configuration file containing:
  - Flask settings (host, port)
  - Model parameters (deployments, pricing, parameters)
  - Service configurations (AI Search, Trello mappings)

## :hammer_and_wrench: Technologies Used

### Cloud Services
- **Azure OpenAI**: GPT-4o and GPT-4o-mini models for natural language processing
- **Azure AI Search**: Semantic search capabilities with hybrid search
- **Azure Cosmos DB**: NoSQL database for conversation history and metrics
- **Azure Speech Services (Whisper)**: Audio-to-text transcription

### External Integrations
- **Trello API**: Ticket management system with flexible priority mapping
- **Flask**: Web framework for user interface

### Development Technologies
- **Python 3.8+**: Primary development language
- **Asyncio**: Asynchronous operations for better performance
- **HTML/CSS/JavaScript**: Responsive web frontend

## :rocket: Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Azure account with OpenAI, AI Search, and Cosmos DB services
- Trello account with API access

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone [REPOSITORY_URL]
   cd ai-it-support
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```env
   # Flask
   FLASK_SECRET_KEY=your_secret_key_here
   
   # Azure OpenAI
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your_api_key_here
   AZURE_OPENAI_API_VERSION=2024-02-01
   
   # Azure AI Search
   AZURE_AI_SEARCH_ENDPOINT=https://your-service.search.windows.net
   AZURE_AI_SEARCH_KEY=your_api_key_here
   AZURE_AI_SEARCH_INDEX_NAME=your_index_name
   SEMANTIC_CONFIGURATION_NAME=your_semantic_config
   
   # Azure Cosmos DB
   COSMOS_DB_ENDPOINT=https://your-account.documents.azure.com:443/
   COSMOS_DB_PRIMARY_KEY=your_primary_key_here
   COSMOS_DB_DATABASE_NAME=your_database_name
   COSMOS_DB_CONTAINER_HISTORY=chat_history
   COSMOS_DB_CONTAINER_EVALS=evaluations
   
   # Trello
   TRELLO_API_KEY=your_trello_api_key
   TRELLO_TOKEN=your_trello_token
   TRELLO_BOARD_ID=your_board_id
   
   # Trello Priority Lists (Recommended)
   TRELLO_LIST_HIGH_PRIORITY_ID=high_priority_list_id
   TRELLO_LIST_MEDIUM_PRIORITY_ID=medium_priority_list_id
   TRELLO_LIST_LOW_PRIORITY_ID=low_priority_list_id
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:8080`

## :gear: Configuration

### Main Configuration (`config/config.json`)

The configuration file provides flexible system settings:

#### Model Configuration
- **Deployments**: Azure OpenAI model deployments and pricing
- **Parameters**: Model parameters (temperature, max_tokens, etc.)
- **Response Format**: Support for function calling, tools, or normal responses

#### Service Configuration
- **AI Search**: Search type (hybrid, semantic, hybrid_semantic)
- **Trello**: Priority and issue type label mappings
- **Flask**: Server settings

#### Flexibility Features
The configuration system is designed for easy customization:
- **Environment-based overrides**: Environment variables take precedence
- **Fallback mechanisms**: Multiple configuration options for compatibility
- **Modular settings**: Each service can be configured independently

### Trello Configuration

#### Priority-Based System (Recommended)
```env
TRELLO_LIST_HIGH_PRIORITY_ID=high_priority_list_id
TRELLO_LIST_MEDIUM_PRIORITY_ID=medium_priority_list_id
TRELLO_LIST_LOW_PRIORITY_ID=low_priority_list_id
```

#### Legacy System (Backward Compatibility)
```env
TRELLO_LIST_PENDING_ID=pending_list_id
TRELLO_LIST_IN_PROGRESS_ID=in_progress_list_id
TRELLO_LIST_COMPLETED_ID=completed_list_id
TRELLO_LIST_CLOSED_ID=closed_list_id
```

### Obtaining Trello Credentials

1. **API Key**: Visit [https://trello.com/app-key](https://trello.com/app-key)
2. **Token**: Use the authorization link on the same page
3. **Board ID**: Extract from board URL: `https://trello.com/b/BOARD_ID/name`
4. **List IDs**: Query the API:
   ```bash
   curl "https://api.trello.com/1/boards/BOARD_ID/lists?key=API_KEY&token=TOKEN"
   ```

## :computer: Usage

### Web Interface
1. Navigate to `http://localhost:8080`
2. Type your IT support question or click the microphone to record audio
3. The assistant will provide answers, solutions, or create tickets as needed

### API Endpoint
- **POST** `/chat`: Main chat endpoint
  - **Text**: Send JSON with `{"query": "your question", "sessionID": "optional_session_id"}`
  - **Audio**: Send multipart form with audio file and optional sessionID

### Response Types
- **Simple**: Direct answer to the question
- **Knowledge Base**: Step-by-step solution with confirmation options
- **Options**: Multiple choice responses
- **Ticket**: Ticket creation confirmation with details

## :handshake: Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## :page_facing_up: License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Generic IT Support AI Assistant**  
*Version 1.0 - Designed for flexible IT support automation* 