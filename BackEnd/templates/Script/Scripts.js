
// Lấy các input elements
const usernameInput = document.getElementById('user');
const passwordInput = document.getElementById('pass');
const emailInput = document.getElementById('email');
const signUpButton = document.querySelector('.sign-up-htm button');

// Thêm event listener cho nút "Sign Up"
signUpButton.addEventListener('click', async () => {
  // Lấy giá trị từ các input
  const username = usernameInput.value;
  const password = passwordInput.value;
  const email = emailInput.value;

  try {
    // Gửi POST request lên server
    const response = await fetch('/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, password, email })
    });

    if (response.ok) {
      // Hiển thị thông báo thành công
      document.getElementById('responseMessage').textContent = 'Registration successful!';
    } else {
      // Hiển thị thông báo lỗi
      document.getElementById('responseMessage').textContent = 'Registration failed. Please try again.';
    }
  } catch (error) {
    console.error('Error:', error);
    // Hiển thị thông báo lỗi
    document.getElementById('responseMessage').textContent = 'An error occurred. Please try again later.';
  }
});