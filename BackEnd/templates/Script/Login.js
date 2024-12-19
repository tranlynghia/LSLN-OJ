
// app.use(cors({
//     origin: 'http://localhost:5000',
//     credentials: true
//   }));
fetch("http://localhost:5000/api/login", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify({
        username: "testUser",
        password: "testPassword"
    })
})
.then(response => response.json())
.then(data => console.log("Kết nối thành công:", data))
.catch(error => console.error("Lỗi kết nối:", error));


// Hàm đăng ký
async function registerUser() {
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    const email = document.getElementById('register-email').value;

    const response = await fetch('/api/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password, email })
    });

    const result = await response.json();
    alert(result.message);
}

// Hàm đăng nhập
async function loginUser() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    const response = await fetch('/api/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
    });

    const result = await response.json();
    alert(result.message);
}
fetch('/login', {
    method: 'POST', // Phải khớp với phương thức trong route
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        username: 'yourUsername',
        password: 'yourPassword'
    })
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));

