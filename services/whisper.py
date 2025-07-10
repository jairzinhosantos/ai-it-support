import os
import json
import logging
from dotenv import load_dotenv
from openai import AzureOpenAI
from config.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhisperClient:
    """Class to interact with Whisper service."""
    def __init__(self):
        config = Config().config
        self.whisper = config["model"]["deployments"]["whisper"]["name"]

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

    def run(self, audio_path, operation_type):
        logger.info(f"WhisperClient.run called with audio_path: {audio_path}, operation_type: {operation_type}")
        
        # Check if file exists and get file size
        if not os.path.exists(audio_path):
            logger.error(f"Audio file does not exist: {audio_path}")
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        file_size = os.path.getsize(audio_path)
        logger.info(f"Audio file size: {file_size} bytes")
        
        if file_size == 0:
            logger.error("Audio file is empty")
            raise ValueError("Audio file is empty")
        
        logger.info("Loading environment variables...")
        env_vars = self.load_env_var()
        
        logger.info("Creating OpenAI client...")
        client = self.create_openai_client(env_vars)

        try:
            logger.info(f"Opening audio file: {audio_path}")
            with open(audio_path, "rb") as audio:
                if operation_type == 'speech_to_text':
                    logger.info(f"Calling Azure OpenAI transcriptions API with model: {self.whisper}")
                    
                    response = client.audio.transcriptions.create(
                        file=audio,
                        model=self.whisper,
                        language="es",  # Explicitly set to Spanish for better accuracy
                        prompt="Este es un audio en español de un usuario solicitando ayuda técnica de TI."  # Context for better accuracy
                    )
                    
                    transcribed_text = response.text
                    logger.info(f"Transcription successful. Text: '{transcribed_text}' (length: {len(transcribed_text)})")
                    return transcribed_text
                
                elif operation_type == 'text_to_speech':
                    logger.info("Text-to-speech not implemented")
                    return ''
                    
        except Exception as e:
            logger.error(f"Error processing audio with Whisper: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            raise
        
'''
whisper_client = WhisperClient()
audio_path = 'assets/audios/output_audio.wav'
operation_type = 'speech_to_text'
result = whisper_client.run(audio_path, operation_type)

print(result)
'''