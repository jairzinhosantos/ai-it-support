# Generic IT Support AI Assistant

**An intelligent IT support system that provides automated first-line technical assistance using conversational AI powered by Azure OpenAI.**

## Table of Contents

- [Project Description](#project-description)
- [Architecture](#architecture)
- [Components](#components)
- [Technologies Used](#technologies-used)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Project Description

This IT Support AI Assistant is a flexible, configurable virtual assistant designed to provide first-line technical support for organizations. The system leverages Azure OpenAI's GPT-4o model for natural language processing and integrates with multiple services to deliver a comprehensive and efficient support experience.

### Key Features

- **Conversational AI Assistant**: Responds to queries with contextual understanding
- **Intelligent Self-Service**: Provides step-by-step solutions from knowledge base
- **Automatic Ticket Management**: Creates tickets in Trello when escalation is needed
- **Multimodal Support**: Accepts both text and audio queries (automatic transcription)
- **Conversation History**: Stores and tracks all interactions
- **Flexible Configuration**: Easy to customize for different organizations and use cases

## Architecture

The system follows a modular microservices-based architecture that enables scalability and maintainability. For detailed architecture information, see the [architecture document](architecture.md).

## Components

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

- **app.py**: Main Flask application entry point. Handles HTTP routes, user sessions, and audio/text processing.
- **orchestrator.py**: Core orchestration logic that coordinates all services and manages conversation flow.

#### Service Layer

- **services/azopenai.py**: Azure OpenAI client with support for function calling and multiple response formats
- **services/cosmosdb.py**: Azure Cosmos DB client for asynchronous chat history and metrics storage
- **services/ticket_trello.py**: Trello API client with flexible priority-based ticket management
- **services/aisearch.py**: Azure AI Search client for semantic and hybrid search capabilities
- **services/whisper.py**: Audio transcription client using Azure OpenAI Whisper

#### Configuration System

- **config/config.py**: Configuration loader with error handling
- **config/config.json**: Centralized configuration file with modular service settings

## Technologies Used

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

## Installation & Setup

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

## Configuration

### Main Configuration

The `config/config.json` file provides flexible system settings:

- **Model Configuration**: Azure OpenAI model deployments, pricing, and parameters
- **Service Configuration**: AI Search types, Trello mappings, and Flask settings
- **Flexibility Features**: Environment-based overrides, fallback mechanisms, and modular settings

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

1. **Get API Key**: Visit https://trello.com/app-key to get your API key
2. **Get Token**: Use the link on the API key page to generate a token
3. **Get Board ID**: From your Trello board URL: `https://trello.com/b/BOARD_ID/board-name`
4. **Get List IDs**: Use Trello's API or browser developer tools to find list IDs

## Usage

### Starting the Application

1. Ensure all environment variables are configured
2. Run the Flask application:
   ```bash
   python app.py
   ```
3. Open your browser and navigate to `http://localhost:8080`

### Using the Interface

1. **Text Chat**: Type your IT support question in the chat interface
2. **Audio Chat**: Click the microphone button to record your question
3. **Ticket Creation**: The system automatically creates tickets for issues requiring escalation
4. **Knowledge Base**: The system provides solutions from the knowledge base when available

### Example Interactions

- "I forgot my password"
- "My computer won't start"
- "I need access to a shared folder"
- "My email is not working"

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Generic IT Support AI Assistant**  
*Version 1.0 - Intelligent IT Support Automation*
