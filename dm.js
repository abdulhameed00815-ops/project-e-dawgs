const token = localStorage.getItem("access_token")
var chatMessages = document.getElementById("messages");

const target = localStorage.getItem("target");
var dm = new WebSocket(`ws://localhost:8000/wsdm/${displayName}?token=${token}&target=${target}`);

dm.onmessage = function(event) {
	chatMessages.insertAdjacentHTML('beforeend', `
		<div id="message">
			<li class="text">${event.data}</li>
		</div>
	`)
	chatMessages.scrollTop = chatMessages.scrollHeight;
};


function sendDm(event) {
	var input = document.getElementById('messageText');
	dm.send(input.value);
	input.value = '';
	event.preventDefault();
}

