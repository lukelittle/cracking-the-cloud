/*
 * main.js - Client-Side JavaScript for Survey Application
 *
 * WHAT THIS FILE DOES:
 * Contains all the JavaScript functions that make the survey interactive:
 * - Submitting votes to the API
 * - Fetching and displaying results
 * - Resetting survey data
 * - Managing session IDs for vote tracking
 *
 * KEY CONCEPTS FOR STUDENTS:
 * 1. Fetch API: Modern way to make HTTP requests in JavaScript
 * 2. Async/Await: Handling asynchronous operations cleanly
 * 3. Local Storage: Browser storage for persisting data
 * 4. DOM Manipulation: Updating HTML elements with JavaScript
 * 5. Error Handling: Try/catch blocks for robust code
 * 6. JSON: JavaScript Object Notation for data exchange
 *
 * ARCHITECTURE:
 * Browser (this file) ←→ API Gateway ←→ Lambda Functions ←→ DynamoDB
 */

// API_URL: This placeholder is replaced by Terraform during deployment
// Terraform uses templatefile() to insert the actual API Gateway URL
const API_URL = '${API_URL}';

/**
 * SESSION ID MANAGEMENT
 * 
 * getSessionId() - Creates or retrieves a unique identifier for this browser session
 * 
 * PURPOSE:
 * Prevents users from voting multiple times from the same browser session.
 * Uses sessionStorage (not localStorage) for privacy - data is cleared when tab closes.
 * 
 * PRIVACY NOTE:
 * - sessionStorage: Cleared when browser tab/window closes
 * - localStorage: Persists across browser sessions (would allow long-term tracking)
 * 
 * RETURNS: A UUID (Universally Unique Identifier) as a string
 */
function getSessionId() {
    // Try to get existing sessionId from browser's sessionStorage
    let sessionId = sessionStorage.getItem('sessionId');
    
    // If no sessionId exists, create a new one
    if (!sessionId) {
        // crypto.randomUUID() generates a random UUID like:
        // "550e8400-e29b-41d4-a716-446655440000"
        sessionId = crypto.randomUUID();
        
        // Store it in sessionStorage for this browser session
        sessionStorage.setItem('sessionId', sessionId);
    }
    
    return sessionId;
}

/**
 * VOTE SUBMISSION
 * 
 * vote(option) - Submits a user's vote to the backend API
 * 
 * PARAMETERS:
 * - option: String - One of 'no', 'aws', or 'other'
 * 
 * WORKFLOW:
 * 1. Get or create session ID
 * 2. Update UI to show "submitting" message
 * 3. Send POST request to API with vote data
 * 4. Handle success or error response
 * 5. Update UI with result and disable buttons
 * 
 * ASYNC/AWAIT EXPLANATION:
 * - 'async' keyword makes this function return a Promise
 * - 'await' pauses execution until the Promise resolves
 * - This makes asynchronous code read like synchronous code
 */
async function vote(option) {
    // STEP 1: Get the message div element to show feedback to user
    // document.getElementById() finds an element by its id attribute
    const messageDiv = document.getElementById('message');
    
    // STEP 2: Show "submitting" message while we wait for API response
    // .textContent sets the text inside the element
    messageDiv.textContent = 'Submitting your vote...';
    
    // STEP 3: Get the session ID for this vote
    const sessionId = getSessionId();

    try {
        // STEP 4: Send POST request to the API
        // fetch() is the modern way to make HTTP requests in JavaScript
        // await pauses here until the request completes
        const response = await fetch(`${API_URL}vote`, {
            method: 'POST',  // HTTP method (POST to send data)
            headers: {
                'Content-Type': 'application/json',  // Tell server we're sending JSON
            },
            // Convert JavaScript object to JSON string for the request body
            body: JSON.stringify({ vote: option, sessionId: sessionId }),
        });

        // STEP 5: Check if request was successful
        // response.ok is true for status codes 200-299
        if (!response.ok) {
            // If not successful, throw an error to jump to the catch block
            throw new Error(`HTTP error! status: $${response.status}`);
        }

        // STEP 6: Update UI for successful vote
        messageDiv.textContent = 'Thank you for voting!';
        
        // STEP 7: Disable all vote buttons to prevent re-voting
        // querySelectorAll() finds all elements matching the CSS selector
        // forEach() loops through each button
        document.querySelectorAll('.vote-btn').forEach(button => {
            button.disabled = true;  // Disable the button
        });
        
    } catch (error) {
        // STEP 8: Handle any errors
        // console.error() logs errors to browser's developer console
        console.error('Error submitting vote:', error);
        
        // Show error message to user
        messageDiv.textContent = 'Sorry, there was an error submitting your vote.';
    }
}

/**
 * RESULTS FETCHING
 * 
 * getResults() - Fetches current vote counts from the API
 * 
 * WORKFLOW:
 * 1. Send GET request to /results endpoint
 * 2. Parse JSON response
 * 3. Call renderChart() with the data (if on results.html)
 * 
 * NOTE: This function is called from results.html
 * The renderChart() function is defined in results.html, not here
 */
async function getResults() {
    try {
        // STEP 1: Fetch results from API
        // No body needed for GET requests
        const response = await fetch(`${API_URL}results`);
        
        // STEP 2: Check if request was successful
        if (!response.ok) {
            throw new Error(`HTTP error! status: $${response.status}`);
        }
        
        // STEP 3: Parse JSON response
        // response.json() converts JSON string to JavaScript object
        // Example response: { "no": 5, "aws": 12, "other": 3 }
        const data = await response.json();
        
        // STEP 4: Update the chart if renderChart function exists
        // typeof checks if the function is defined (results.html defines it)
        if (typeof renderChart === 'function') {
            renderChart(data);
        }
    } catch (error) {
        console.error('Error fetching results:', error);
    }
}

/**
 * SURVEY RESET
 * 
 * resetSurvey() - Deletes all survey data from the database
 * 
 * WORKFLOW:
 * 1. Show confirmation dialog to user
 * 2. If confirmed, send POST request to /reset endpoint
 * 3. Handle response and update UI
 * 4. Refresh results chart if on results page
 * 
 * SECURITY NOTE:
 * In production, this would require authentication.
 * Currently anyone who knows the URL can reset the survey!
 */
async function resetSurvey() {
    // STEP 1: Get the message div for user feedback
    const messageDiv = document.getElementById('message');
    
    // STEP 2: Show confirmation dialog
    // confirm() shows a browser dialog with OK/Cancel buttons
    // Returns true if user clicks OK, false if Cancel
    if (!confirm('Are you sure you want to reset all survey data? This cannot be undone.')) {
        return;  // Exit function if user clicked Cancel
    }

    // STEP 3: Show "resetting" message
    messageDiv.textContent = 'Resetting survey...';

    try {
        // STEP 4: Send POST request to reset endpoint
        const response = await fetch(`${API_URL}reset`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        // STEP 5: Check if request was successful
        if (!response.ok) {
            throw new Error(`HTTP error! status: $${response.status}`);
        }

        // STEP 6: Show success message
        messageDiv.textContent = 'Survey has been reset successfully!';
        
        // STEP 7: Refresh the results chart if we're on results.html
        // This shows the empty chart after reset
        if (typeof renderChart === 'function') {
            getResults();  // Fetch fresh data to update chart
        }
    } catch (error) {
        // STEP 8: Handle errors
        console.error('Error resetting survey:', error);
        messageDiv.textContent = 'An error occurred while resetting the survey.';
    }
}

/*
 * SUMMARY OF HOW IT ALL WORKS TOGETHER:
 * 
 * 1. USER VOTES (index.html):
 *    - User clicks button → vote() called → POST to /vote → Lambda stores in DynamoDB
 * 
 * 2. VIEW RESULTS (results.html):
 *    - Page loads → getResults() called → GET from /results → Lambda counts votes
 *    - renderChart() displays data → Repeats every 3 seconds for live updates
 * 
 * 3. RESET SURVEY (reset.html):
 *    - User clicks reset → Confirmation dialog → resetSurvey() → POST to /reset
 *    - Lambda deletes all items from DynamoDB → Results chart refreshes
 * 
 * DEBUGGING TIPS:
 * - Press F12 in browser to open Developer Tools
 * - Check Console tab for error messages
 * - Check Network tab to see API requests/responses
 * - Use console.log() to print values for debugging
 */
