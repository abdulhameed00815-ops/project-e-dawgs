signupForm = document.getElementById('signin-form')
signupForm.addEventListener('submit', function signin(e) {
        e.preventDefault()
        var email = document.getElementById('email').value;
        var password = document.getElementById('password').value;
        fetch('http://127.0.0.1:8000/signin', {
                method:'POST',
                headers: {
                        'accept': 'application/json, text/plain, */*',
                        'content-type': 'application/json'
                },
                body:JSON.stringify({email:email, password:password})
        })
        .then(res => {
                return res.json().then(data => ({ status: res.status, data: data }));
        })
        .then(({ status, data }) => {
                if (status === 200) {
                        localStorage.setItem('access_token', data.access_token);
			localStorage.setItem('display_name', data.display_name);
                        window.location.assign("http://localhost:5500/chat.html");
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

