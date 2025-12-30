const token = sessionStorage.getItem("access_token");
var chatMessages = document.getElementById("messages");
const messageForm = document.getElementById("message-form");
const mainHeader = document.getElementById("main-header");
const loungeButton = document.getElementById("button1");

const display_name = sessionStorage.getItem('display_name');
document.querySelector("#ws-id").textContent = display_name


const target_display_name = sessionStorage.getItem("target");

mainHeader.textContent = `You are in a DM with: ${target_display_name}`;

loungeButton.addEventListener("click", function returnToLounge() { 
	window.location.assign("http://localhost:5500/chat.html")
});

function getDmId() {
	fetch(`http://127.0.0.1:8000/getdmid/${display_name}/${target_display_name}`, {
		credentials: "include"
	})
	.then(res => {
		return res.json().then(data => ({ status: res.status, data: data }));
	})
	.then(({ status, data }) => {
		if (status === 200) {
			sessionStorage.setItem('dm_id', data.dm_id);
		} else if (status === 402) {
			fetch("http://127.0.0.1:8000/refresh/", {
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

	});
}


getDmId()
const dm_id = sessionStorage.getItem('dm_id')


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
                        data.dms.forEach(function(message) {
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
			window.location.reload();
		}
        })
}


getDms()


var dm = new WebSocket(`ws://localhost:8000/wsdm?token=${token}&target=${target_display_name}`);


dm.onclose = function (event) {
        if (event.code !== 1000) {
                window.location.reload();
        }
}


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



