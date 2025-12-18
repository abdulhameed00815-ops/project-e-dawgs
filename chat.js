const token = localStorage.getItem("access_token")
var chatMessages = document.getElementById("messages");
window.onload = function getMessages() {
	fetch("http://127.0.0.1:8000/getmessages", {
		method:'GET',
		headers: {
			"Authorization": `Bearer ${token}`,
			"Accept": 'application/json, text/plain, */*',
                        "Content-type": 'application/json'

		}
	})
  	.then(res => {
        	return res.json().then(data => ({ status: res.status, data: data }));
        })
	.then(({ status, data }) => {
		if (status === 200) {
			data.forEach(function(message) {
				chatMessages.insertAdjacentHTML('beforeend', `
					<div id="message">
						<li class="text">${message.message_content}</li>
					</div>
				`)
			}) 
		}	
	})
}
const displayName = localStorage.getItem('display_name');
document.querySelector("#ws-id").textContent = displayName
var ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);

ws.onmessage = function(event) {
	chatMessages.insertAdjacentHTML('beforeend', `
		<div id="message">
			<li class="text">${event.data}</li>
		</div>
	`)
};

function sendMessage(event) {
	var input = document.getElementById('messageText');
	ws.send(input.value);
	input.value = '';
	event.preventDefault();
}
