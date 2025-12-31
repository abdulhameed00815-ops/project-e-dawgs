let token = sessionStorage.getItem("access_token")
let refreshToken = sessionStorage.getItem("refresh_token")
var chatMessages = document.getElementById("messages");
console.log(token);
window.onload = function getMessages() {
	fetch("http://localhost:8000/getmessages", {
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
		} else if (status !== 200) {
			fetch("http://localhost:8000/refresh/", {
				credentials: "include"
			})
			.then(res => {
				return res.json().then(data => ({ status: res.status, data: data }));
			})
			.then(({ status, data }) => {
				if (status === 200) {
					sessionStorage.setItem("access_token", data.access_token);
					console.log(`${data.access_token} is the new meta`)
					window.location.reload();
				}
			})
		}	
	})
}


const displayName = sessionStorage.getItem('display_name');
document.querySelector("#ws-id").textContent = displayName
var ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);


ws.onclose = function (event) {
	if (event.code !== 1000) {
		window.location.reload();
	}
}


ws.onmessage = function(event) {
	chatMessages.insertAdjacentHTML('beforeend', `
		<div id="message">
			<li class="text">${event.data}</li>
		</div>
	`)
	chatMessages.scrollTop = chatMessages.scrollHeight;
};

function sendMessage(event) {
	var input = document.getElementById('messageText');
	ws.send(input.value);
	input.value = '';
	event.preventDefault();
}

const targetForm = document.getElementById("target-form")
targetForm.addEventListener("submit", function dm(e) {
	e.preventDefault()
	const target = document.getElementById("target").value;
	sessionStorage.setItem("target", target)
	window.location.assign("http://localhost:8000/static/dm.html");
})
