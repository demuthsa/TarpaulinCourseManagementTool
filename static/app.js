document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const fetchCoursesButton = document.getElementById('fetchCourses');
    const fetchUsersButton = document.getElementById('fetchUsers');
    const coursesList = document.getElementById('coursesList');
    const usersList = document.getElementById('usersList');
    const createCourseForm = document.getElementById('createCourseForm');
    const updateAvatarForm = document.getElementById('updateAvatarForm');
    const loginSection = document.getElementById('loginSection');
    const contentSection = document.getElementById('contentSection');
    const navCourses = document.getElementById('navCourses');
    const navUsers = document.getElementById('navUsers');
    const navAvatar = document.getElementById('navAvatar');

    let token = '';
    let userRole = '';

    loginForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const formData = new FormData(loginForm);
        const username = formData.get('username');
        const password = formData.get('password');

        fetch('/users/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.token) {
                token = data.token;
                alert('Login successful');
                // Decode the JWT to get user role
                const payload = JSON.parse(atob(token.split('.')[1]));
                userRole = payload.nickname;
                setupContentBasedOnRole();
            } else {
                alert('Login failed');
            }
        });
    });

    function setupContentBasedOnRole() {
        loginSection.style.display = 'none';
        contentSection.style.display = 'block';

        // Display sections based on user role
        if (userRole.includes('admin')) {
            navCourses.style.display = 'block';
            navUsers.style.display = 'block';
            navAvatar.style.display = 'block';
            document.getElementById('courses').style.display = 'block';
            document.getElementById('users').style.display = 'block';
            document.getElementById('userAvatar').style.display = 'block';
        } else if (userRole.includes('instructor')) {
            navCourses.style.display = 'block';
            navAvatar.style.display = 'block';
            document.getElementById('courses').style.display = 'block';
            document.getElementById('userAvatar').style.display = 'block';
        } else if (userRole.includes('student')) {
            navCourses.style.display = 'block';
            navAvatar.style.display = 'block';
            document.getElementById('courses').style.display = 'block';
            document.getElementById('userAvatar').style.display = 'block';
        }
    }

    fetchCoursesButton.addEventListener('click', function() {
        fetch('/courses', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => response.json())
        .then(data => {
            coursesList.innerHTML = '';
            data.courses.forEach(course => {
                const div = document.createElement('div');
                div.className = 'course';
                div.textContent = `${course.title} - ${course.subject} ${course.number}`;
                coursesList.appendChild(div);
            });
        });
    });

    fetchUsersButton.addEventListener('click', function() {
        fetch('/users', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => response.json())
        .then(data => {
            usersList.innerHTML = '';
            data.forEach(user => {
                const div = document.createElement('div');
                div.className = 'user';
                div.textContent = `${user.id} - ${user.role}`;
                usersList.appendChild(div);
            });
        });
    });

    createCourseForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const formData = new FormData(createCourseForm);
        const courseData = {
            title: formData.get('title'),
            subject: formData.get('subject'),
            number: formData.get('number'),
            term: formData.get('term'),
            instructor_id: formData.get('instructor_id')
        };

        fetch('/courses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(courseData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.id) {
                alert('Course created successfully');
                fetchCoursesButton.click();
            } else {
                alert('Failed to create course');
            }
        });
    });

    updateAvatarForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const formData = new FormData(updateAvatarForm);
        const userId = formData.get('user_id');
        const file = formData.get('file');

        fetch(`/users/${userId}/avatar`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.avatar_url) {
                alert('Avatar updated successfully');
            } else {
                alert('Failed to update avatar');
            }
        });
    });
});
