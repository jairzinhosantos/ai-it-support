document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const chatBox = document.getElementById('chatBox');
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    const deleteHistoryButton = document.getElementById('deleteHistory');
    const micButton = document.getElementById('micButton');
    const micIcon = document.getElementById('micIcon');
    const stopIcon = document.getElementById('stopIcon');

    // Audio recording variables
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;

    // Make sessionId editable
    let sessionId = generateSessionId();
    
    // Initial message
    addWelcomeMessage();

    // Function to show welcome message
    function addWelcomeMessage() {
        //addMessage("Hi! I'm your virtual assistant, how can I help you today?", true);
    }

    // Simplified function to clear the chat
    function clearChat() {
        // Clear the chat area
        chatBox.innerHTML = '';
        // Generate new session_id
        sessionId = generateSessionId();
        // Show welcome message
        addWelcomeMessage();
    }

    // Handle click on clear history button
    deleteHistoryButton.addEventListener('click', function() {
        try {
            clearChat();
        } catch (error) {
            console.error('Error while clearing history:', error);
            addMessage("Sorry, an error occurred while clearing the history. Please try again.", true);
        }
    });

    // Handle microphone button click
    micButton.addEventListener('click', function() {
        console.log('Mic button clicked, isRecording:', isRecording);
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    });

    // Handle message submission
    messageForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        // Disable input and button while processing
        messageInput.disabled = true;
        messageInput.value = '';

        try {
            // Show user message
            addMessage(message, false);

            // Show loading indicator
            const loadingIndicator = addLoadingIndicator();

            // Send message to backend
            const response = await sendMessage(sessionId, message);
            
            // Remove loading indicator
            loadingIndicator.remove();

            // Process backend response
            if (response) {
                console.log('Backend response:', response); // For debugging
                let responseText = '';
                let options = [];
                let ticket = null;
                
                // Nueva lógica para manejar la respuesta estructurada
                if (response.type && response.message) {
                    responseText = response.message;
                    
                    // Si hay opciones, crear botones
                    if (response.options && response.options.length > 0) {
                        options = response.options;
                    }
                    
                    // Si hay ticket, mostrar información
                    if (response.ticket) {
                        ticket = response.ticket;
                    }
                    
                    // Agregar el mensaje principal
                    addMessage(responseText, true);
                    
                    // Si hay opciones, agregar botones
                    if (options.length > 0) {
                        addOptions(options);
                    }
                    
                    // Si hay ticket, mostrar información
                    if (ticket) {
                        addTicketInfo(ticket);
                    }
                    
                } else {
                    // Verificar la estructura específica de la respuesta (compatibilidad con versión anterior)
                    if (response.response && response.response.answer) {
                        responseText = response.response.answer;
                    } else if (response.response) {
                        responseText = response.response;
                    } else if (response.answer) {
                        responseText = response.answer;
                    } else if (typeof response === 'string') {
                        responseText = response;
                    } else {
                        console.log('Unrecognized response structure:', response);
                        throw new Error('Unrecognized response format');
                    }

                    if (responseText) {
                        addMessage(responseText, true);
                        // Ensure scroll after the response
                        scrollToBottom();
                    }
                }
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage("Sorry, an error occurred. Please try again.", true);
        } finally {
            // Re-enable input
            messageInput.disabled = false;
            messageInput.focus();
            // Ensure scroll to bottom
            scrollToBottom();
        }
    });

    // ===== FUNCIONES DE GRABACIÓN DE AUDIO =====

    async function startRecording() {
        try {
            console.log('Attempting to start recording...');
            
            // Check if getUserMedia is supported
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('getUserMedia no es compatible con este navegador');
            }
            
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 44100
                } 
            });
            console.log('Got media stream successfully');
            
            mediaRecorder = new MediaRecorder(stream, {
                mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
            });
            audioChunks = [];

            mediaRecorder.ondataavailable = function(event) {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                    console.log('Audio data available:', event.data.size, 'bytes');
                }
            };

            mediaRecorder.onstop = async function() {
                console.log('Recording stopped, processing audio...');
                const audioBlob = new Blob(audioChunks, { 
                    type: mediaRecorder.mimeType || 'audio/wav' 
                });
                console.log('Audio blob created:', audioBlob.size, 'bytes');
                
                if (audioBlob.size > 0) {
                    await sendAudioMessage(audioBlob);
                } else {
                    console.error('Audio blob is empty');
                    addMessage("Error: No se grabó audio. Intenta de nuevo.", true);
                }
                
                // Stop all tracks to release the microphone
                stream.getTracks().forEach(track => {
                    track.stop();
                    console.log('Track stopped:', track.kind);
                });
            };

            mediaRecorder.onerror = function(event) {
                console.error('MediaRecorder error:', event.error);
                addMessage("Error durante la grabación. Intenta de nuevo.", true);
            };

            mediaRecorder.start(1000); // Collect data every 1000ms
            isRecording = true;
            updateMicButton();
            
            console.log('Recording started successfully');
            
        } catch (error) {
            console.error('Error starting recording:', error);
            let errorMessage = "Error al acceder al micrófono. ";
            
            if (error.name === 'NotAllowedError') {
                errorMessage += "Permisos denegados. Por favor, permite el acceso al micrófono.";
            } else if (error.name === 'NotFoundError') {
                errorMessage += "No se encontró micrófono.";
            } else if (error.name === 'NotSupportedError') {
                errorMessage += "Tu navegador no soporta grabación de audio.";
            } else if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
                errorMessage += "Requiere HTTPS para funcionar.";
            } else {
                errorMessage += error.message;
            }
            
            addMessage(errorMessage, true);
            isRecording = false;
            updateMicButton();
        }
    }

    function stopRecording() {
        console.log('Stop recording called, isRecording:', isRecording);
        if (mediaRecorder && isRecording && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            isRecording = false;
            updateMicButton();
            console.log('Recording stopped');
        }
    }

    function updateMicButton() {
        console.log('Updating mic button, isRecording:', isRecording);
        if (isRecording) {
            micButton.classList.add('recording');
            micIcon.style.display = 'none';
            stopIcon.style.display = 'block';
            micButton.title = 'Detener grabación';
            console.log('Button set to recording state');
        } else {
            micButton.classList.remove('recording');
            micIcon.style.display = 'block';
            stopIcon.style.display = 'none';
            micButton.title = 'Iniciar grabación';
            console.log('Button set to normal state');
        }
    }

    async function sendAudioMessage(audioBlob) {
        try {
            console.log('Sending audio message, blob size:', audioBlob.size);
            
            // Disable input and button while processing
            messageInput.disabled = true;
            micButton.disabled = true;

            // Show initial loading indicator for transcription (without bot avatar)
            const transcriptionLoadingIndicator = addTranscriptionLoadingIndicator();

            // Create FormData to send audio file
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');
            formData.append('sessionID', sessionId);

            console.log('Sending to backend...');
            // Send audio to backend
            const response = await fetch('/chat', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
            }

            const result = await response.json();
            console.log('Audio processing result:', result);
            
            // Remove transcription loading indicator
            transcriptionLoadingIndicator.remove();

            // Process backend response
            if (result) {
                // First, show the transcribed text as user message if available
                if (result.transcribed_text) {
                    addMessage(result.transcribed_text, false);
                    
                    // Add a small delay to show the transcription first
                    await new Promise(resolve => setTimeout(resolve, 300));
                    
                    // Show bot loading indicator for processing the response
                    const responseLoadingIndicator = addLoadingIndicator();
                    
                    // Add another small delay to simulate processing
                    await new Promise(resolve => setTimeout(resolve, 800));
                    
                    // Remove response loading indicator
                    responseLoadingIndicator.remove();
                }
                
                let responseText = '';
                let options = [];
                let ticket = null;
                
                if (result.type && result.message) {
                    responseText = result.message;
                    
                    if (result.options && result.options.length > 0) {
                        options = result.options;
                    }
                    
                    if (result.ticket) {
                        ticket = result.ticket;
                    }
                    
                    addMessage(responseText, true);
                    
                    if (options.length > 0) {
                        addOptions(options);
                    }
                    
                    if (ticket) {
                        addTicketInfo(ticket);
                    }
                    
                } else {
                    // Compatibility with previous format
                    if (result.response && result.response.answer) {
                        responseText = result.response.answer;
                    } else if (result.response) {
                        responseText = result.response;
                    } else if (result.answer) {
                        responseText = result.answer;
                    } else if (typeof result === 'string') {
                        responseText = result;
                    } else {
                        console.log('Unrecognized response structure:', result);
                        throw new Error('Unrecognized response format');
                    }

                    if (responseText) {
                        addMessage(responseText, true);
                        scrollToBottom();
                    }
                }
            }
        } catch (error) {
            console.error('Error sending audio:', error);
            addMessage("Error al procesar el audio: " + error.message, true);
        } finally {
            // Re-enable input and microphone
            messageInput.disabled = false;
            micButton.disabled = false;
            messageInput.focus();
            scrollToBottom();
        }
    }

    // Improved function to scroll to the last message
    function scrollToBottom() {
        // Get the last message
        const messages = chatBox.getElementsByClassName('message');
        const lastMessage = messages[messages.length - 1];
        
        if (lastMessage) {
            // Use scrollIntoView for a more reliable scroll
            lastMessage.scrollIntoView({ behavior: 'smooth', block: 'end' });
            
            // Ensure it reaches the bottom after everything has been rendered
            setTimeout(() => {
                chatBox.scrollTop = chatBox.scrollHeight;
            }, 100);
        }
    }

    // Function to add messages
    function addMessage(text, isBot) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isBot ? 'bot' : 'user'}`;

        if (isBot) {
            const avatarDiv = document.createElement('div');
            avatarDiv.className = 'bot-avatar';
            const avatarImg = document.createElement('img');
            avatarImg.src = '/static/images/avatar.svg';
            avatarImg.alt = 'Bot Avatar';
            avatarDiv.appendChild(avatarImg);
            messageDiv.appendChild(avatarDiv);
        }

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Process the text to convert <link> tags into hyperlinks
        const processLinks = (text) => {
            const linkRegex = /<link>(.*?)<\/link>/g;
            const parts = text.split(linkRegex);
            
            return parts.map((part, index) => {
                if (index % 2 === 0) {
                    // Normal text
                    const span = document.createElement('span');
                    span.textContent = part;
                    return span;
                } else {
                    // It's a link
                    const link = document.createElement('a');
                    link.href = part;
                    link.textContent = part;
                    link.target = '_blank';
                    link.rel = 'noopener noreferrer';
                    link.className = 'chat-link';
                    return link;
                }
            });
        };

        // Split the text into lines and process each one
        const lines = text.split(/\n/);
        
        lines.forEach((line, index) => {
            // Process the links in this line
            const elements = processLinks(line);
            
            // Add the elements of the line
            elements.forEach(element => {
                contentDiv.appendChild(element);
            });
            
            // Add a line break after each line, except the last one
            if (index < lines.length - 1) {
                contentDiv.appendChild(document.createElement('br'));
            }
        });

        messageDiv.appendChild(contentDiv);
        chatBox.appendChild(messageDiv);
        scrollToBottom();
    }

    function addLoadingIndicator() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';

        // Add avatar
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'bot-avatar';
        const avatarImg = document.createElement('img');
        avatarImg.src = '/static/images/avatar.svg';
        avatarImg.alt = 'Bot Avatar';
        avatarDiv.appendChild(avatarImg);
        messageDiv.appendChild(avatarDiv);

        // Add loading indicator
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content loading';
        
        // Create the container of the writing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        
        // Add only the animated dots
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            dot.textContent = '.';
            typingDiv.appendChild(dot);
        }
        
        contentDiv.appendChild(typingDiv);
        messageDiv.appendChild(contentDiv);

        chatBox.appendChild(messageDiv);
        scrollToBottom();
        return messageDiv;
    }

    function addTranscriptionLoadingIndicator() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content transcription-loading';
        contentDiv.style.cssText = `
            background: rgba(33, 41, 84, 0.3);
            color: white;
            font-style: italic;
            opacity: 0.85;
        `;
        
        const transcriptionText = document.createElement('span');
        transcriptionText.textContent = 'Transcribing audio...';
        contentDiv.appendChild(transcriptionText);
        
        messageDiv.appendChild(contentDiv);
        chatBox.appendChild(messageDiv);
        scrollToBottom();
        return messageDiv;
    }

    function generateSessionId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    async function sendMessage(sessionId, message) {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                sessionID: sessionId,
                query: message || ''
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    // ===== FUNCIONALIDADES ADICIONALES =====

    function addOptions(options) {
        const optionsContainer = document.createElement('div');
        optionsContainer.className = 'options-container';

        options.forEach((option, index) => {
            const button = document.createElement('button');
            button.className = 'option-button';
            
            // Manejar tanto objetos como strings simples
            let optionText = '';
            let optionType = '';
            
            if (typeof option === 'string') {
                optionText = option;
                // Para botones simples, asignar tipos por defecto
                if (option.toLowerCase().includes('sí') || option.toLowerCase().includes('si') || option.toLowerCase().includes('yes')) {
                    optionType = 'success';
                } else if (option.toLowerCase().includes('no')) {
                    optionType = 'error';
                } else {
                    optionType = index === 0 ? 'success' : 'error';
                }
            } else {
                optionText = option.text || option;
                optionType = option.type || (index === 0 ? 'success' : 'error');
            }
            
            button.textContent = optionText;
            button.setAttribute('data-type', optionType);
            
            // Manejar el click del botón
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Verificar si ya está deshabilitado para evitar doble procesamiento
                if (button.disabled) {
                    return;
                }
                
                // Deshabilitar todos los botones después del click
                optionsContainer.querySelectorAll('.option-button').forEach(btn => {
                    btn.disabled = true;
                    btn.style.opacity = '0.6';
                });
                
                // Deshabilitar el input principal también
                messageInput.disabled = true;
                
                // Procesar la selección
                handleOptionClick({
                    text: optionText,
                    type: optionType,
                    response: typeof option === 'object' ? option.response : null
                });
            });

            optionsContainer.appendChild(button);
        });

        // Agregar el contenedor de opciones al último mensaje del bot
        const lastBotMessage = Array.from(chatBox.querySelectorAll('.message.bot')).pop();
        if (lastBotMessage) {
            const messageContent = lastBotMessage.querySelector('.message-content');
            messageContent.appendChild(optionsContainer);
        }

        scrollToBottom();
    }

    function handleOptionClick(option) {
        console.log('Option clicked:', option);
        
        // Enviar la respuesta como si fuera un mensaje del usuario
        addMessage(option.text, false);
        
        // Agregar respuesta automática del bot si la hay
        if (option.response) {
            setTimeout(() => {
                addMessage(option.response, true);
            }, 500);
        } else {
            // Si no hay respuesta automática, enviar al backend
            setTimeout(async () => {
                let loadingIndicator = null;
                try {
                    console.log('Sending option to backend:', option.text, 'with sessionId:', sessionId);
                    loadingIndicator = addLoadingIndicator();
                    const response = await sendMessage(sessionId, option.text);
                    if (loadingIndicator) {
                        loadingIndicator.remove();
                        loadingIndicator = null;
                    }
                    
                    if (response) {
                        console.log('Option click response:', response); // Para debugging
                        let responseText = '';
                        let options = [];
                        let ticket = null;
                        
                        // Usar la misma lógica que en el submit principal
                        if (response.type && response.message) {
                            responseText = response.message;
                            
                            if (response.options && response.options.length > 0) {
                                options = response.options;
                            }
                            
                            if (response.ticket) {
                                ticket = response.ticket;
                            }
                            
                            addMessage(responseText, true);
                            
                            if (options.length > 0) {
                                addOptions(options);
                            }
                            
                            if (ticket) {
                                addTicketInfo(ticket);
                            }
                            
                        } else {
                            // Compatibilidad con formato anterior
                            if (response.response && response.response.answer) {
                                responseText = response.response.answer;
                            } else if (response.response) {
                                responseText = response.response;
                            } else if (response.answer) {
                                responseText = response.answer;
                            } else if (typeof response === 'string') {
                                responseText = response;
                            } else {
                                console.log('Unrecognized response structure in option click:', response);
                                responseText = "Respuesta procesada correctamente.";
                            }
                            
                            if (responseText) {
                                addMessage(responseText, true);
                            }
                        }
                    }
                } catch (error) {
                    console.error('Error sending option response:', error);
                    console.error('Error details:', error.message, error.stack);
                    if (loadingIndicator) {
                        loadingIndicator.remove();
                        loadingIndicator = null;
                    }
                    addMessage("Error al procesar la respuesta. Intenta de nuevo.", true);
                } finally {
                    // Re-enable input
                    messageInput.disabled = false;
                    messageInput.focus();
                    scrollToBottom();
                }
            }, 500);
        }
    }

    function addTicketInfo(ticket) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';

        // Agregar avatar del bot
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'bot-avatar';
        const avatarImg = document.createElement('img');
        avatarImg.src = '/static/images/avatar.svg';
        avatarImg.alt = 'Bot Avatar';
        avatarDiv.appendChild(avatarImg);
        messageDiv.appendChild(avatarDiv);

        // Contenedor del contenido
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Crear tabla de información del ticket
        const ticketTable = document.createElement('table');
        ticketTable.className = 'ticket-info';

        // Agregar filas de información del ticket
        Object.entries(ticket).forEach(([key, value]) => {
            const row = document.createElement('tr');
            
            const keyCell = document.createElement('td');
            keyCell.textContent = key + ':';
            
            const valueCell = document.createElement('td');
            valueCell.textContent = value;
            
            row.appendChild(keyCell);
            row.appendChild(valueCell);
            ticketTable.appendChild(row);
        });

        contentDiv.appendChild(ticketTable);
        messageDiv.appendChild(contentDiv);
        chatBox.appendChild(messageDiv);
        
        scrollToBottom();
    }
});