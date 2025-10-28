# Test Cases: OAuth2

## Overview
This set of tests covers the implementation of OAuth2 authentication for users to log in with Google and GitHub accounts. It ensures that the system handles user authentication, token storage, and session management correctly.

## Prerequisites
- Node.js environment with Express backend
- React frontend with necessary dependencies
- PostgreSQL database with user sessions table
- Sample test data (see below)

## Test Scenarios

### Scenario 1: Happy Path - Normal Flow

**Given**: Initial conditions and setup
- User is logged out of the system
- System has a valid client ID for Google and GitHub OAuth2 providers

**When**: User clicks "Login with Google" or "Login with GitHub"
- The system redirects to the chosen OAuth2 provider for authorization

**Then**: The user is redirected back with an access token and a secure HTTP-only cookie stored on their browser
- The system verifies the access token and updates the user session

**Test Steps**:
1. Navigate to login page with valid client ID for Google or GitHub
2. Click "Login with Google" or "Login with GitHub"
3. Verify redirect to OAuth2 provider is successful
4. Verify access token is stored in secure HTTP-only cookie
5. Verify system updates user session correctly

---

### Scenario 2: Happy Path - Refresh Token Flow

**Given**: Initial conditions and setup
- User has an existing access token that will expire soon
- System has a valid client ID for Google and GitHub OAuth2 providers

**When**: Access token is about to expire or has expired
- The system triggers automatic refresh using the refresh token

**Then**: A new access token is obtained, stored in secure HTTP-only cookie, and user session is updated
- The system verifies that the new access token can be used successfully

**Test Steps**:
1. Obtain an existing access token (or simulate expiration)
2. Verify system triggers automatic refresh using refresh token
3. Verify new access token is stored in secure HTTP-only cookie
4. Verify system updates user session correctly
5. Verify new access token can be used successfully

---

### Scenario 3: Error Handling - Invalid Credentials

**Given**: Initial conditions and setup
- User has invalid credentials for Google or GitHub OAuth2 provider
- System has a valid client ID for both providers

**When**: User tries to log in with invalid credentials
- The system detects and handles the error

**Then**: An appropriate error message is displayed, and user session remains intact
- The system prevents unauthorized access

**Test Steps**:
1. Navigate to login page with invalid credentials
2. Click "Login with Google" or "Login with GitHub"
3. Verify an error message is displayed correctly
4. Verify user session remains intact after handling the error
5. Verify that unauthorized access is prevented

---

### Scenario 4: Performance/Load

**Given**: High load or stress condition (e.g., multiple concurrent users)
- System has a performance baseline to compare against

**When**: System handles high load or stress without significant performance degradation

**Then**: Performance meets requirements and system remains stable
- The system can handle increased traffic effectively

**Test Steps**:
1. Simulate high load or stress on the system (e.g., multiple concurrent users)
2. Measure system performance under load
3. Compare measured performance to baseline performance
4. Verify that system remains stable throughout
5. Verify that response times, error rates, and other critical metrics meet requirements

## Test Data

```json
{
  "google_client_id": "valid-client-id",
  "github_client_id": "valid-client-id",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaGFuIjoiMjMwfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaGFuIjoiMjMwfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
  "user_session_id": "valid-user-session-id"
}
```

## Acceptance Criteria

- [ ] All happy path scenarios pass
- [ ] Edge cases handled correctly
- [ ] Error messages are clear and actionable
- [ ] Performance meets requirements
- [ ] Security considerations addressed

## Notes

- Make sure to cover all possible edge cases, including but not limited to:
  - Different client IDs for Google and GitHub providers
  - Users with existing access tokens that expire or have expired
  - Invalid credentials for both Google and GitHub OAuth2 providers
  - High load or stress conditions during testing