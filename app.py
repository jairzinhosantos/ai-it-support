import os
import logging
import sys
import uuid
import asyncio
from flask import Flask, jsonify, request, render_template, session
from flask_cors import CORS
from orchestrator import Orchestrator
from config.config import Config
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Flask application
#app = Flask(__name__)
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv("FLASK_SECRET_KEY")

CORS(app)

# Initialize handler
config = Config().config
orchestrator = Orchestrator()

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/chat", methods=["POST"])
def chat():
    """Endpoint for handling chat requests (text or audio)."""
    try:
        logger.info("Processing chat request...")

        # Check if request contains files (audio)
        if 'audio' in request.files:
            logger.info("Processing audio request...")
            return handle_audio_request()
        else:
            logger.info("Processing text request...")
            return handle_text_request()
            
    except Exception as e:
        logger.error(f"Error during chat processing: {e}")
        return jsonify({"error": str(e)}), 500

def handle_text_request():
    """Handle text-based chat requests."""
    try:
        data = request.get_json(force=True)
        if not data:
            logger.error("No JSON received in the request.")
            return jsonify({"error": "No JSON received in the request."}), 400
        
        logger.info(f"Received data: {data}")

        session_id = data.get('sessionID') or session.get('sessionID')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id

        query = data.get('query')
        if not query:
            logger.error("Missing 'query' in the request.")
            return jsonify({"error": "Missing 'query' in the request."}), 400

        response = asyncio.run(orchestrator.run(session_id, query))
        return response
    except KeyError as e:
        logger.error(f"Missing key in JSON data: {e}")
        return jsonify({"error": f"Missing key in JSON data: {e}"}), 400

def handle_audio_request():
    """Handle audio-based chat requests."""
    try:
        from services.whisper import WhisperClient
        
        # Get session ID
        session_id = request.form.get('sessionID') or session.get('sessionID')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id

        # Get audio file
        audio_file = request.files['audio']
        if not audio_file:
            logger.error("No audio file received.")
            return jsonify({"error": "No audio file received."}), 400

        logger.info(f"Audio file received. Filename: {audio_file.filename}")
        logger.info(f"Audio file content type: {audio_file.content_type}")
        logger.info(f"Audio file content length: {audio_file.content_length}")

        # Save audio file temporarily
        import tempfile
        import os
        
        # Create temporary file
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, 'temp_audio.wav')
        audio_file.save(audio_path)
        
        # Check file size after saving
        file_size = os.path.getsize(audio_path)
        logger.info(f"Audio file saved to: {audio_path}")
        logger.info(f"Saved file size: {file_size} bytes")

        try:
            # Convert audio to text using Whisper
            logger.info("Initializing WhisperClient...")
            whisper_client = WhisperClient()
            
            logger.info(f"Calling whisper_client.run with audio_path: {audio_path}")
            transcribed_text = whisper_client.run(audio_path, 'speech_to_text')
            
            logger.info(f"Whisper transcription completed. Result: '{transcribed_text}'")
            logger.info(f"Transcribed text length: {len(transcribed_text) if transcribed_text else 0}")
            
            if not transcribed_text or transcribed_text.strip() == "":
                logger.error("Empty transcription received from Whisper.")
                return jsonify({"error": "No se pudo transcribir el audio. Por favor, intenta de nuevo."}), 400

            # Process the transcribed text through the normal flow
            response = asyncio.run(orchestrator.run(session_id, transcribed_text))
            
            # Extract the JSON data from the response and add transcribed text
            if isinstance(response, tuple) and len(response) == 2:
                response_data, status_code = response
                try:
                    # Get the JSON data from the Flask response
                    if hasattr(response_data, 'get_json'):
                        response_json = response_data.get_json()
                    else:
                        response_json = response_data
                    
                    # Add transcribed text to the response
                    if isinstance(response_json, dict):
                        response_json['transcribed_text'] = transcribed_text
                    else:
                        response_json = {
                            'transcribed_text': transcribed_text,
                            'message': str(response_json)
                        }
                    
                    return jsonify(response_json), status_code
                    
                except Exception as e:
                    logger.error(f"Error processing response tuple: {e}")
                    return jsonify({
                        "transcribed_text": transcribed_text,
                        "message": "Audio procesado correctamente"
                    }), 200
            else:
                try:
                    # Handle single response object
                    if hasattr(response, 'get_json'):
                        response_json = response.get_json()
                    elif hasattr(response, 'json'):
                        response_json = response.json
                    else:
                        response_json = response
                    
                    # Add transcribed text to the response
                    if isinstance(response_json, dict):
                        response_json['transcribed_text'] = transcribed_text
                        return jsonify(response_json)
                    else:
                        return jsonify({
                            "transcribed_text": transcribed_text,
                            "message": str(response_json)
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing single response: {e}")
                    return jsonify({
                        "transcribed_text": transcribed_text,
                        "message": "Audio procesado correctamente"
                    })
            
        finally:
            # Clean up temporary file
            try:
                os.remove(audio_path)
                os.rmdir(temp_dir)
                logger.info("Temporary audio file cleaned up.")
            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up temporary file: {cleanup_error}")
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return jsonify({"error": f"Error procesando el audio: {str(e)}"}), 500

def start_app():
    """Starts the Flask application."""
    app.run(host=config["flask"]["host"], port=config["flask"]["port"], debug=True)

if __name__ == "__main__":
    start_app()