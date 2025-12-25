const token = sessionStorage.getItem("access_token");
var chatMessages = document.getElementById("messages");
const messageForm = document.getElementById("message-form");

const display_name = sessionStorage.getItem('display_name');
document.querySelector("#ws-id").textContent = display_name


const target_display_name = sessionStorage.getItem("target");

function getDmId() {
	fetch(`http://127.0.0.1:8000/getdmid/${display_name}/${target_display_name}`, {
		method: "GET",
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
			sessionStorage.setItem('dm_id', data.dm_id);
		}

	});
}


getDmId()
const dm_id = sessionStorage.getItem('dm_id')
console.log(dm_id)


function getDms() {
        fetch(`http://127.0.0.1:8000/getdms/${dm_id}`, {
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
                                                <li class="text">${message.dm_content}</li>
                                        </div>
                                `)
                        })
                } else {
			chatMessages.insertAdjacentHTML('beforeend', `
				<div id="message">
					<li class="text">${data.detail}</li>
				</div>
			`);
		}
        })
}


getDms()


var dm = new WebSocket(`ws://localhost:8000/wsdm?token=${token}&target=${target_display_name}`);

messageForm.addEventListener("submit", function sendDm(event) {
	event.preventDefault();
	var input = document.getElementById('messageText');
	dm.send(input.value);
	input.value = '';
});


dm.onmessage = function(event) {
	chatMessages.insertAdjacentHTML('beforeend', `
		<div id="message">
			<li class="text">${event.data}</li>
		</div>
	`)
	chatMessages.scrollTop = chatMessages.scrollHeight;
};



