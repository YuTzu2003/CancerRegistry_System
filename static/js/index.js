document.addEventListener('DOMContentLoaded', function() {
const chatDisplay = document.getElementById('chatDisplay');
const userInput = document.getElementById('userInput');
const btnSend = document.getElementById('btnSend');

function addMessage(text, type) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${type}`;
    
    if (type === 'ai') {
        msgDiv.innerHTML = `<div class="avatar"><i class="bi bi-emoji-smile-fill"></i></div>
                            <div class="msg-content">${text}</div>`;
    } 
    else {
    msgDiv.innerHTML = `<div class="msg-content">${text}</div>`;
    }
    
    chatDisplay.appendChild(msgDiv);
    chatDisplay.scrollTop = chatDisplay.scrollHeight;
}

function handleSend() {
    const text = userInput.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    userInput.value = '';

    // Simulated AI response
    setTimeout(() => {
    addMessage("問題：「" + text + "」，我正在分析相關的癌症登記手冊與編碼規則...", "ai");
    }, 800);
}

btnSend.onclick = handleSend;
userInput.onkeypress = (e) => { if (e.key === 'Enter') handleSend(); };
});