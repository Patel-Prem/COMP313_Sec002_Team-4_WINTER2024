"use strict";

const serverUrl = "http://localhost:3001/";

async function toggleViewsAndLinks() {
    const token = localStorage.getItem('access_token');
    const isLoggedIn = token !== null;
    const userType = localStorage.getItem('userType');

    // Attempt to find elements; if not found, they'll be null
    const homeView = document.getElementById('homeView');
    const landingView = document.getElementById('landingView');
    const loginLink = document.getElementById('loginLink');
    const logoutLink = document.getElementById('logoutLink');
    const userTypeSection = document.getElementById('userTypeSection');
    const adminInfoSection = document.getElementById('adminInfo');
    const totalUsersDisplay = document.getElementById('totalUsers'); 

    // Hide or show views based on login status
    if (homeView || landingView) {
        const shouldHide = isLoggedIn && userType === 'admin';
        if(homeView)
            homeView.classList.toggle('d-none', shouldHide);
        if(landingView)
            landingView.classList.toggle('d-none', shouldHide);
        // Admin-specific actions
        if (userType === 'admin') {
            try {
                const response = await fetch(`${serverUrl}total_users`, {
                    method: 'GET',
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (!response.ok) throw new Error('Failed to fetch total users');

                const data = await response.json();
                if (totalUsersDisplay) totalUsersDisplay.textContent = `Total Users: ${data.totalUsers}`;

                // Show the admin info section specifically for admins
                if (adminInfoSection) adminInfoSection.classList.remove('d-none');
            } catch (error) {
                console.error('Error:', error);
                if (totalUsersDisplay) totalUsersDisplay.textContent = 'Error fetching total users.';
            }
        } else {
            // Hide the admin info section for non-admin users or if not logged in
            if (adminInfoSection) adminInfoSection.classList.add('d-none');
        }
    }
    // Toggle views if elements are found
    if (homeView && landingView) {
        homeView.classList.toggle('d-none', isLoggedIn);
        landingView.classList.toggle('d-none', !isLoggedIn);
    }

    // Toggle navigation links if elements are found
    if (loginLink && logoutLink) {
        loginLink.classList.toggle('d-none', isLoggedIn);
        logoutLink.classList.toggle('d-none', !isLoggedIn);
    }

    // Hide the user type section if userType is set and is one of the specified types
    if (userTypeSection && ['recruiter', 'premium', 'normal'].includes(userType)) {
        userTypeSection.style.display = 'none';
    }
}

// Function to handle login
function login() {
    fetch(serverUrl + "login")
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            window.location.href = data.login_url;
        })
        .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
        });
}

// Function to handle logout
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('userType');
    localStorage.removeItem('userEmail');
    fetch(serverUrl + "logout")
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            window.location.href = data.logout_url;
        })
        .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
        });
}

// Function to handle resume form submission
document.getElementById('resumeForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const token = localStorage.getItem('access_token');
    if (!token) {
        alert('You must register or log in first.');
        return;
    }

    const jobDescription = document.getElementById('jobDescription').value;
    const resumeUpload = document.getElementById('resumeUpload');
    const userEmail = localStorage.getItem('userEmail');
    const userType = document.querySelector('input[name="userType"]:checked').value;

    if (!resumeUpload.files.length || jobDescription.trim() === '') {
        alert('Please attach a resume and fill out the job description.');
        return;
    }

    const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const fileType = resumeUpload.files[0].type;
    if (!allowedTypes.includes(fileType)) {
        alert('Only PDF and DOC/DOCX files are allowed.');
        return;
    }

    showLoadingMessage();

    var formData = new FormData();
    formData.append('resume', resumeUpload.files[0]);
    formData.append('jobDescription', jobDescription);

    fetch(serverUrl + "upload", {
        method: 'POST',
        body: formData,
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('File upload failed');
        }
        return response.json();
    })
    .then(uploadData => {
        return fetch(serverUrl + "analyze", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                resume_text: uploadData.resume_text,
                job_description: jobDescription,
                user_type: userType,
                user_email: userEmail

            })
        });
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Analysis failed');
        }
        return response.json();
    })
    .then(analysisData => {
        displayAnalysisResults(analysisData);
    })
    .catch(error => {
        console.error('Error:', error);
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = `<p class="text-danger">Error processing your request. Please try again.</p>`;
    });
});

// Functions to create and display result cards
function displayAnalysisResults(data) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';
    resultsDiv.classList.remove('d-none');

    const userType = document.querySelector('input[name="userType"]:checked').value;

    createSimilarityScoreCard(data, resultsDiv);

    if (userType === 'premium' || userType === 'recruiter') {
        createKeywordsCard(data, resultsDiv);
    }

    if (userType === 'recruiter') {
        createEntitiesCard(data, resultsDiv);
    }
}

function createSimilarityScoreCard(data, container) {
    const scoreCard = document.createElement('div');
    scoreCard.className = 'card mb-3';
    const scoreCardBody = document.createElement('div');
    scoreCardBody.className = 'card-body';
    const scoreCardTitle = document.createElement('h5');
    scoreCardTitle.className = 'card-title';
    scoreCardTitle.innerHTML = `Similarity Score: <span class="badge bg-success">${data.score.toFixed(2)}</span>`;
    scoreCardBody.appendChild(scoreCardTitle);
    scoreCard.appendChild(scoreCardBody);
    container.appendChild(scoreCard);
}

function createKeywordsCard(data, container) {
    const keywordsCard = document.createElement('div');
    keywordsCard.className = 'card mb-3';
    const keywordsCardBody = document.createElement('div');
    keywordsCardBody.className = 'card-body';
    const keywordsCardTitle = document.createElement('h5');
    keywordsCardTitle.className = 'card-title';
    keywordsCardTitle.textContent = 'Suggested Keywords';
    keywordsCardBody.appendChild(keywordsCardTitle);

    if (data.missing_words && data.missing_words.length > 0) {
        const keywordsList = document.createElement('ul');
        keywordsList.className = 'list-unstyled';
        data.missing_words.forEach(word => {
            const listItem = document.createElement('li');
            listItem.innerHTML = `<span>${word}</span>`;
            keywordsList.appendChild(listItem);
        });
        keywordsCardBody.appendChild(keywordsList);
    } else {
        const noKeywordsMsg = document.createElement('p');
        noKeywordsMsg.textContent = 'No suggested keywords.';
        keywordsCardBody.appendChild(noKeywordsMsg);
    }
    keywordsCard.appendChild(keywordsCardBody);
    container.appendChild(keywordsCard);
}

function createEntitiesCard(data, container) {
    const entitiesCard = document.createElement('div');
    entitiesCard.className = 'card mb-3';
    const entitiesCardBody = document.createElement('div');
    entitiesCardBody.className = 'card-body';
    const entitiesCardTitle = document.createElement('h5');
    entitiesCardTitle.className = 'card-title';
    entitiesCardTitle.textContent = 'Detected PII Entities';
    entitiesCardBody.appendChild(entitiesCardTitle);

    const entitiesList = document.createElement('ul');
    entitiesList.className = 'list-group list-group-flush';
    if (data.entities && data.entities.length > 0) {
        data.entities.forEach(entity => {
            const listItem = document.createElement('li');
            listItem.className = 'list-group-item';
            listItem.textContent = `${entity.Type}: ${entity.Text}`;
            entitiesList.appendChild(listItem);
        });
    } else {
        const noEntitiesMsg = document.createElement('li');
        noEntitiesMsg.className = 'list-group-item';
        noEntitiesMsg.textContent = 'No PII entities detected.';
        entitiesList.appendChild(noEntitiesMsg);
    }
    entitiesCardBody.appendChild(entitiesList);
    entitiesCard.appendChild(entitiesCardBody);
    container.appendChild(entitiesCard);
}

function showLoadingMessage() {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = `<div class="text-center"><i class="fas fa-spinner fa-pulse fa-3x"></i><p class="mt-3">Analyzing your resume, please hold tight...</p></div>`;
    resultsDiv.classList.remove('d-none');
}

async function handleLoginRedirect() {
    const authCode = new URLSearchParams(window.location.search).get('code');
    if (authCode) {
        try {
            const response = await fetch(`${serverUrl}get_token?code=${authCode}`);
            if (!response.ok) {
                throw new Error('Failed to get access token');
            }
            const tokenData = await response.json();
            console.log(tokenData);
            localStorage.setItem('access_token', tokenData.access_token);
            
            // Check if user_email is part of the response
            if (tokenData.user_email) {
                localStorage.setItem('userEmail', tokenData.user_email);
            }

            // Check if user_type is part of the response and save it
            if (tokenData.user_type) {
                localStorage.setItem('userType', tokenData.user_type);
            }
            
            // Update views and links based on login status
            toggleViewsAndLinks();
        } catch (error) {
            console.error('Error:', error);
        }
    }
}

window.addEventListener('load', async function() {
    await handleLoginRedirect();
    toggleViewsAndLinks(); 
});