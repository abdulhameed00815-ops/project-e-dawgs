const now = new Date()
const customTime = now.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit', 
    hour12: false 
}); 
const token = localStorage.getItem("access_token")
const displayName = localStorage.getItem('display_name');
document.querySelector("#ws-id").textContent = displayName
var ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);

ws.onmessage = function(event) {
	var messages = document.getElementById('messages');
	var message = document.createElement('li');
	var content = document.createTextNode(event.data);
	message.appendChild(content);
	messages.appendChild(message);
};

function sendMessage(event) {
	var input = document.getElementById('messageText');
	ws.send(input.value);
	input.value = '';
	event.preventDefault();
}
