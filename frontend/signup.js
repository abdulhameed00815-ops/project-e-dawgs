signupForm = document.getElementById('signup-form')
signupForm.addEventListener('submit', function signup(e) {
	e.preventDefault()
	var displayName = document.getElementById('display-name').value; 
	var email = document.getElementById('email').value;
	var password = document.getElementById('password').value;
	fetch('http://127.0.0.1:8000/signup', {
		method:'POST',
		headers: {
			'accept': 'application/json, text/plain, */*',
			'content-type': 'application/json'
		},
                body:JSON.stringify({email:email, display_name:displayName, password:password})
	})
	.then(res => {
		return res.json().then(data => ({ status: res.status, data: data }));
	})
	.then(({ status, data }) => {
		if (status === 200) {
			localStorage.setItem('access_token', data.access_token);
			window.location.assign("http://localhost:5500/signin.html");
		} else {
			var output = document.getElementById('output');
			output.innerHTML = `
				<h2>${data.detail}</h2>
			`
			setTimeout(() => {
				window.location.reload();
			}, 3000);
		}
	});
})
