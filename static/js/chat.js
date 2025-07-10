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

    // Streaming variables
    let currentStreamingMessage = null;
    let isStreaming = false;
    let streamingBuffer = [];
    let isShowingLoadingDots = true;
    let bufferTimeout = null;

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

            // Start streaming response
            await sendStreamingMessage(sessionId, message);

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

    // ===== STREAMING FUNCTIONS =====

    async function sendStreamingMessage(sessionId, message) {
        return new Promise((resolve, reject) => {
            try {
                if (isStreaming) {
                    console.log('Already streaming, skipping request');
                    resolve();
                    return;
                }

                isStreaming = true;

                // Create streaming message element
                currentStreamingMessage = createStreamingMessageElement();
                
                // Send the message via POST to start streaming
                fetch('/chat/stream', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        sessionID: sessionId,
                        query: message
                    })
                }).then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    // Handle the streaming response
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    
                    function readStream() {
                        reader.read().then(({ done, value }) => {
                            if (done) {
                                finishStreamingMessage();
                                resolve();
                                return;
                            }
                            
                            const chunk = decoder.decode(value, { stream: true });
                            const lines = chunk.split('\n');
                            
                            for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                    try {
                                        const data = JSON.parse(line.substring(6));
                                        
                                        if (data.type === 'content') {
                                            handleStreamingData(data);
                                        } else if (data.type === 'options') {
                                            // Wait for streaming to finish, then add options
                                            setTimeout(() => {
                                                finishStreamingMessage();
                                                addOptions(data.options);
                                            }, 100);
                                        } else if (data.type === 'ticket') {
                                            // Wait for streaming to finish, then add ticket
                                            setTimeout(() => {
                                                finishStreamingMessage();
                                                addTicketInfo(data.ticket);
                                            }, 100);
                                        } else if (data.type === 'complete') {
                                            // Streaming is complete
                                            setTimeout(() => {
                                                finishStreamingMessage();
                                            }, 100);
                                        } else if (data.type === 'error') {
                                            handleStreamingData(data);
                                        }
                                        
                                    } catch (e) {
                                        console.error('Error parsing streaming data:', e);
                                    }
                                }
                            }
                            
                            readStream();
                        }).catch(error => {
                            console.error('Error reading stream:', error);
                            finishStreamingMessage();
                            reject(error);
                        });
                    }
                    
                    readStream();
                    
                }).catch(error => {
                    console.error('Error starting stream:', error);
                    finishStreamingMessage();
                    reject(error);
                });

            } catch (error) {
                console.error('Error in sendStreamingMessage:', error);
                finishStreamingMessage();
                reject(error);
            }
        });
    }

    function createStreamingMessageElement() {
        // Reset streaming state
        streamingBuffer = [];
        isShowingLoadingDots = true;
        
        // Clear any existing timeout
        if (bufferTimeout) {
            clearTimeout(bufferTimeout);
        }
        
        // Create message using original structure
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

        // Add message content with loading dots
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content streaming-message';
        contentDiv.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';

        messageDiv.appendChild(contentDiv);
        chatBox.appendChild(messageDiv);

        // Start streaming content after showing loading dots for a while
        bufferTimeout = setTimeout(() => {
            startStreamingContent();
        }, 3000); // Show loading dots for 3 seconds (increased from 1.2s)

        // Scroll to bottom
        scrollToBottom();

        return contentDiv;
    }

    function handleStreamingData(data) {
        if (!currentStreamingMessage) return;

        if (data.type === 'content') {
            appendToStreamingMessage(data.content);
        } else if (data.type === 'error') {
            // Handle error immediately
            isShowingLoadingDots = false;
            if (bufferTimeout) {
                clearTimeout(bufferTimeout);
                bufferTimeout = null;
            }
            currentStreamingMessage.innerHTML = `<span class="error">Error: ${data.content}</span>`;
            finishStreamingMessage();
        }
    }

    function appendToStreamingMessage(content) {
        if (!currentStreamingMessage) return;

        // If we're still showing loading dots, buffer the content and start streaming immediately
        if (isShowingLoadingDots) {
            streamingBuffer.push(content);
            // Start streaming content immediately when we get the first chunk
            startStreamingContent();
            return;
        }

        // Add new content normally
        const currentContent = currentStreamingMessage.textContent || '';
        const newContent = currentContent + content;
        
        // Process links like the original function
        const processedContent = processLinksForBotMessage(newContent);
        currentStreamingMessage.innerHTML = processedContent;
        
        // Scroll to bottom
        scrollToBottom();
    }

    function startStreamingContent() {
        if (!currentStreamingMessage) return;
        
        isShowingLoadingDots = false;
        
        // Clear any existing timeout
        if (bufferTimeout) {
            clearTimeout(bufferTimeout);
            bufferTimeout = null;
        }
        
        // Clear loading dots
        currentStreamingMessage.innerHTML = '';
        
        // Process buffered content gradually
        let currentIndex = 0;
        let accumulatedContent = '';
        
        function processNextChunk() {
            if (currentIndex < streamingBuffer.length && currentStreamingMessage) {
                const chunk = streamingBuffer[currentIndex];
                accumulatedContent += chunk;
                
                const processedContent = processLinksForBotMessage(accumulatedContent);
                currentStreamingMessage.innerHTML = processedContent;
                
                currentIndex++;
                scrollToBottom();
                
                // Continue with next chunk after a small delay for visual effect
                setTimeout(processNextChunk, 80);
            }
        }
        
        // Start processing chunks
        processNextChunk();
    }

    function finishStreamingMessage() {
        if (!currentStreamingMessage) return;

        // Clear any timeouts
        if (bufferTimeout) {
            clearTimeout(bufferTimeout);
            bufferTimeout = null;
        }

        // Ensure any remaining buffered content is displayed
        if (isShowingLoadingDots && streamingBuffer.length > 0) {
            startStreamingContent();
        }

        // Remove streaming class
        currentStreamingMessage.classList.remove('streaming-message');

        // Clean up
        currentStreamingMessage = null;
        isStreaming = false;
        streamingBuffer = [];
        isShowingLoadingDots = true;

        // Scroll to bottom
        scrollToBottom();
    }

    // Function to process links like the original
    function processLinksForBotMessage(text) {
        const linkRegex = /<link>(.*?)<\/link>/g;
        const parts = text.split(linkRegex);
        
        let result = '';
        parts.forEach((part, index) => {
            if (index % 2 === 0) {
                // Normal text
                result += part;
            } else {
                // It's a link
                result += `<a href="${part}" target="_blank" rel="noopener noreferrer" class="chat-link">${part}</a>`;
            }
        });
        
        return result;
    }

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

            mediaRecorder.start();
            isRecording = true;
            updateMicButton();
            console.log('Recording started');

        } catch (error) {
            console.error('Error starting recording:', error);
            addMessage("Error al iniciar la grabación: " + error.message, true);
        }
    }

    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            updateMicButton();
            console.log('Recording stopped by user');
        }
    }

    function updateMicButton() {
        if (isRecording) {
            micButton.classList.add('recording');
            micIcon.style.display = 'none';
            stopIcon.style.display = 'block';
        } else {
            micButton.classList.remove('recording');
            micIcon.style.display = 'block';
            stopIcon.style.display = 'none';
        }
    }

    // ===== FUNCIONES DE ENVÍO DE AUDIO =====

    async function sendAudioMessage(audioBlob) {
        try {
            // Disable input while processing
            messageInput.disabled = true;
            
            // Show transcription loading indicator
            const transcriptionLoadingIndicator = addTranscriptionLoadingIndicator();
            
            // Create FormData to send audio
            const formData = new FormData();
            formData.append('audio', audioBlob, 'audio.wav');
            formData.append('sessionID', sessionId);
            
            console.log('Sending audio to server for transcription...');
            
            // Send audio to server for transcription only
            const response = await fetch('/transcribe', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('Audio transcription received:', result);
            
            // Remove transcription loading indicator
            transcriptionLoadingIndicator.remove();
            
            // Show the transcribed text to user
            if (result.transcribed_text) {
                addMessage(result.transcribed_text, false);
                console.log('Transcribed text:', result.transcribed_text);
                
                // Now use streaming for the AI response
                await sendStreamingMessage(sessionId, result.transcribed_text);
            } else {
                throw new Error('No transcribed text received');
            }
            
        } catch (error) {
            console.error('Error sending audio message:', error);
            addMessage("Error al procesar el audio: " + error.message, true);
        } finally {
            // Re-enable input
            messageInput.disabled = false;
            messageInput.focus();
            scrollToBottom();
        }
    }

    // ===== FUNCIONES DE UTILIDAD =====

    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Function to add a message to the chat (original structure)
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
        
        // Process the text to convert <link> tags into hyperlinks (original logic)
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

        // Split the text into lines and process each one (original logic)
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

    // Loading indicator with original structure
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
        
        // Create enhanced loading with dots
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading-dots';
        
        const loadingSpan = document.createElement('span');
        loadingSpan.textContent = 'Thinking';
        loadingDiv.appendChild(loadingSpan);
        
        // Add animated dots
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'loading-dot';
            loadingDiv.appendChild(dot);
        }
        
        contentDiv.appendChild(loadingDiv);
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

    // Legacy function for non-streaming messages (kept for audio)
    async function sendMessage(sessionId, message) {
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    sessionID: sessionId,
                    query: message
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }

    // Function to add options as buttons (using original styling)
    function addOptions(options) {
        const optionsContainer = document.createElement('div');
        optionsContainer.className = 'options-container';

        options.forEach((option, index) => {
            const button = document.createElement('button');
            button.className = 'option-button';
            
            // Handle both objects and simple strings
            let optionText = '';
            let optionType = '';
            
            if (typeof option === 'string') {
                optionText = option;
                // For simple buttons, assign default types
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
            
            // Handle button click
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Check if already disabled to avoid double processing
                if (button.disabled) {
                    return;
                }
                
                // Disable all buttons after click
                optionsContainer.querySelectorAll('.option-button').forEach(btn => {
                    btn.disabled = true;
                    btn.style.opacity = '0.6';
                });
                
                // Disable main input as well
                messageInput.disabled = true;
                
                // Process the selection
                handleOptionClick(optionText);
            });

            optionsContainer.appendChild(button);
        });

        // Add the options container to the last bot message
        const lastBotMessage = Array.from(chatBox.querySelectorAll('.message.bot')).pop();
        if (lastBotMessage) {
            const messageContent = lastBotMessage.querySelector('.message-content');
            messageContent.appendChild(optionsContainer);
        }

        scrollToBottom();
    }

    // Function to handle option clicks (now with streaming)
    function handleOptionClick(optionText) {
        console.log('Option clicked:', optionText);
        
        // Send the response as if it were a user message
        addMessage(optionText, false);
        
        // Process with streaming
        setTimeout(async () => {
            try {
                await sendStreamingMessage(sessionId, optionText);
            } catch (error) {
                console.error('Error sending option response:', error);
                addMessage("Error al procesar la respuesta. Intenta de nuevo.", true);
            } finally {
                // Re-enable input
                messageInput.disabled = false;
                messageInput.focus();
                scrollToBottom();
            }
        }, 500);
    }

    // Function to add ticket information (using original structure)
    function addTicketInfo(ticket) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';

        // Add bot avatar
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'bot-avatar';
        const avatarImg = document.createElement('img');
        avatarImg.src = '/static/images/avatar.svg';
        avatarImg.alt = 'Bot Avatar';
        avatarDiv.appendChild(avatarImg);
        messageDiv.appendChild(avatarDiv);

        // Content container
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Create ticket info table
        const ticketTable = document.createElement('table');
        ticketTable.className = 'ticket-info';

        // Add ticket information rows
        Object.entries(ticket).forEach(([key, value]) => {
            const row = document.createElement('tr');
            
            const keyCell = document.createElement('td');
            keyCell.textContent = key + ':';
            
            const valueCell = document.createElement('td');
            if (key === 'trello_url' && value) {
                const link = document.createElement('a');
                link.href = value;
                link.textContent = 'Ver en Trello';
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                valueCell.appendChild(link);
            } else {
                valueCell.textContent = value;
            }
            
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