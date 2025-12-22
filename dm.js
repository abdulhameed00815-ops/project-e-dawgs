const token = sessionStorage.getItem("access_token");
var chatMessages = document.getElementById("messages");

const target = sessionStorage.getItem("target");
var dm = new WebSocket(`ws://localhost:8000/wsdm?token=${token}&target=${target}`);

dm.onmessage = function(event) {
	chatMessages.insertAdjacentHTML('beforeend', `
		<div id="message">
			<li class="text">${event.data}</li>
		</div>
	`)
	chatMessages.scrollTop = chatMessages.scrollHeight;
};


function sendDm(event) {
	event.preventDefault();
	var input = document.getElementById('messageText');
	dm.send(input.value);
	input.value = '';
}

