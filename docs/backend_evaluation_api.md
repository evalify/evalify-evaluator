# Evalify Evaluation API Documentation

This document provides comprehensive documentation for the Evaluation API endpoints in the `{base_url}/api/eval` router of Evalify-Backend. All endpoints are built using Next.js API routes and interact with the PostgreSQL database through Drizzle ORM.

---

## Table of Contents

1. [Base URL](#base-url)
2. [Authentication & Authorization](#authentication--authorization)
3. [Error Handling](#error-handling)
4. [API Endpoints](#api-endpoints)
   - [Get Quiz Details](#1-get-quiz-details)
   - [Get Quiz Questions](#2-get-quiz-questions)
   - [Get Specific Question](#3-get-specific-question)
   - [Get Quiz Settings](#4-get-quiz-settings)
   - [Get Student Quiz Responses](#5-get-student-quiz-responses)
   - [Get All Quiz Responses](#6-get-all-quiz-responses)
5. [Data Models](#data-models)
6. [Error Codes](#error-codes)

---

## Base URL

```
{base_url}/api/eval
```

### Available Routes Structure

```
/api/eval/quiz/{quizId}                                    # Quiz management
/api/eval/quiz/{quizId}/question                          # All questions in a quiz
/api/eval/quiz/{quizId}/question/{questionId}             # Specific question
/api/eval/quiz/{quizId}/settings                          # Quiz settings
/api/eval/quiz/{quizId}/student                           # All student responses
/api/eval/quiz/{quizId}/student/{studentId}               # Specific student response
/api/eval/quiz/{quizId}/save/{studentId}                  # Save student response (placeholder)
```

---

## Authentication & Authorization

### API Key Authentication

The Evaluation API endpoints are protected by **API Key authentication** implemented in `src/proxy.ts`. 

**Authentication Method:** API Key Header

All requests to the `/api/eval/*` endpoints must include the following header:

```
API_KEY: <EVALUATION_SERVICE_API_KEY>
```

The API key value is stored in the environment variable `EVALUATION_SERVICE_API_KEY`. If the header is missing or incorrect, the API returns:

```json
{
  "error": "Unauthorized",
  "status": 401
}
```

### Authentication Flow

1. Client sends request to `/api/eval/*` endpoint
2. The middleware in `src/proxy.ts` intercepts the request
3. Middleware checks for the `API_KEY` header
4. Compares the provided key with `process.env.EVALUATION_SERVICE_API_KEY`
5. If valid, request is processed; otherwise returns **401 Unauthorized**

### Example Request

```bash
curl -X GET "http://localhost:3000/api/eval/quiz/550e8400-e29b-41d4-a716-446655440000" \
  -H "API_KEY: your-evaluation-service-api-key"
```

### Environment Configuration

Ensure the following environment variable is set in your `.env.local`:

```env
EVALUATION_SERVICE_API_KEY=<your-secure-api-key>
```

### Additional Security Considerations

While API key authentication is in place, consider implementing:

- **Role-based access control (RBAC)** - Validate user permissions for accessing specific quiz/student data
- **Rate limiting** - Prevent abuse of the API endpoints
- **Request validation** - Implement comprehensive input validation on all endpoints
- **Data encryption** - Encrypt sensitive data in transit and at rest
- **Audit logging** - Track all API access and modifications for security audits
- **CORS configuration** - Properly configure CORS headers for backend integration

---

## Error Handling

All endpoints follow a consistent error response format:

### Error Response Format

```json
{
  "error": "Error message describing what went wrong",
  "status": 400 | 404 | 500
}
```

### HTTP Status Codes

| Status Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Bad Request (missing/invalid parameters) |
| 404 | Resource Not Found |
| 500 | Internal Server Error |

---

## API Endpoints

---

### 1. Get Quiz Details

Retrieve complete details of a specific quiz.

**Endpoint:** `GET /api/eval/quiz/{quizId}`

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `quizId` | UUID (string) | Yes | Unique identifier of the quiz |

**Query Parameters:** None

**Request Example:**

```bash
GET /api/eval/quiz/550e8400-e29b-41d4-a716-446655440000
```

**Response Schema:**

```typescript
{
  "quiz": {
    "id": string (UUID),
    "name": string,
    "description": string | null,
    "instructions": string | null,
    "startTime": Date (ISO 8601),
    "endTime": Date (ISO 8601),
    "duration": interval (PostgreSQL interval format),
    "password": string | null,
    "fullScreen": boolean,
    "shuffleQuestions": boolean,
    "shuffleOptions": boolean,
    "linearQuiz": boolean,
    "calculator": boolean,
    "autoSubmit": boolean,
    "publishResult": boolean,
    "publishQuiz": boolean,
    "kioskMode": boolean | null,
    "createdById": UUID | null,
    "created_at": Date (ISO 8601),
    "updated_at": Date (ISO 8601)
  }
}
```

**Success Response (200):**

```json
{
  "quiz": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Midterm Examination 2025",
    "description": "Comprehensive midterm exam covering modules 1-5",
    "instructions": "Complete all questions. Calculator is not allowed.",
    "startTime": "2025-02-15T10:00:00Z",
    "endTime": "2025-02-15T12:00:00Z",
    "duration": "02:00:00",
    "password": "exam123",
    "fullScreen": true,
    "shuffleQuestions": true,
    "shuffleOptions": true,
    "linearQuiz": false,
    "calculator": false,
    "autoSubmit": true,
    "publishResult": false,
    "publishQuiz": true,
    "kioskMode": false,
    "createdById": "660e8400-e29b-41d4-a716-446655440001",
    "created_at": "2025-01-20T14:30:00Z",
    "updated_at": "2025-02-10T09:15:00Z"
  }
}
```

**Error Response (400):**

```json
{
  "error": "Quiz ID is required",
  "status": 400
}
```

**Error Response (404):**

```json
{
  "error": "Quiz not found",
  "status": 404
}
```

**Error Response (500):**

```json
{
  "error": "Failed to fetch quiz data",
  "status": 500
}
```

---

### 2. Get Quiz Questions

Retrieve all questions associated with a specific quiz in order.

**Endpoint:** `GET /api/eval/quiz/{quizId}/question`

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `quizId` | UUID (string) | Yes | Unique identifier of the quiz |

**Query Parameters:** None

**Request Example:**

```bash
GET /api/eval/quiz/550e8400-e29b-41d4-a716-446655440000/question
```

**Response Schema:**

```typescript
{
  "data": Array<{
    "questionId": UUID,
    "orderIndex": number,
    "id": UUID,
    "type": "MCQ" | "MMCQ" | "TRUE_FALSE" | "DESCRIPTIVE" | "FILL_THE_BLANK" | "MATCHING" | "FILE_UPLOAD" | "CODING",
    "marks": number,
    "negativeMarks": number,
    "difficulty": "EASY" | "MEDIUM" | "HARD",
    "courseOutcome": "CO1" | "CO2" | "CO3" | "CO4" | "CO5" | "CO6" | "CO7" | "CO8" | null,
    "bloomTaxonomyLevel": "REMEMBER" | "UNDERSTAND" | "APPLY" | "ANALYZE" | "EVALUATE" | "CREATE" | null,
    "question": string,
    "questionData": JSON (structure varies by question type),
    "explaination": string | null,
    "solution": JSON (structure varies by question type),
    "createdById": UUID,
    "created_at": Date (ISO 8601),
    "updated_at": Date (ISO 8601)
  }>
}
```

**Success Response (200):**

```json
{
  "data": [
    {
      "questionId": "660e8400-e29b-41d4-a716-446655440001",
      "orderIndex": 1,
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "type": "MCQ",
      "marks": 2,
      "negativeMarks": 0.5,
      "difficulty": "MEDIUM",
      "courseOutcome": "CO1",
      "bloomTaxonomyLevel": "UNDERSTAND",
      "question": "What is the capital of France?",
      "questionData": {
        "options": [
          { "id": "opt1", "optionText": "Paris", "orderIndex": 1 },
          { "id": "opt2", "optionText": "London", "orderIndex": 2 },
          { "id": "opt3", "optionText": "Berlin", "orderIndex": 3 },
          { "id": "opt4", "optionText": "Madrid", "orderIndex": 4 }
        ]
      },
      "explaination": "Paris is the capital and most populous city of France.",
      "solution": {
        "correctOptions": [
          { "id": "opt1", "isCorrect": true }
        ]
      },
      "createdById": "770e8400-e29b-41d4-a716-446655440002",
      "created_at": "2025-01-10T10:00:00Z",
      "updated_at": "2025-02-05T15:30:00Z"
    },
    {
      "questionId": "660e8400-e29b-41d4-a716-446655440002",
      "orderIndex": 2,
      "id": "660e8400-e29b-41d4-a716-446655440002",
      "type": "MMCQ",
      "marks": 3,
      "negativeMarks": 1,
      "difficulty": "HARD",
      "courseOutcome": "CO3",
      "bloomTaxonomyLevel": "APPLY",
      "question": "Select all correct statements about photosynthesis:",
      "questionData": {
        "options": [
          { "id": "opt1", "optionText": "It occurs in the chloroplast", "orderIndex": 1 },
          { "id": "opt2", "optionText": "It requires sunlight", "orderIndex": 2 },
          { "id": "opt3", "optionText": "It produces glucose", "orderIndex": 3 },
          { "id": "opt4", "optionText": "It consumes glucose", "orderIndex": 4 }
        ]
      },
      "explaination": "Photosynthesis is the process by which plants convert light energy into chemical energy.",
      "solution": {
        "correctOptions": [
          { "id": "opt1", "isCorrect": true },
          { "id": "opt2", "isCorrect": true },
          { "id": "opt3", "isCorrect": true }
        ]
      },
      "createdById": "770e8400-e29b-41d4-a716-446655440003",
      "created_at": "2025-01-12T14:20:00Z",
      "updated_at": "2025-02-06T11:45:00Z"
    }
  ]
}
```

**Error Response (500):**

```json
{
  "error": "Failed to fetch quiz questions",
  "status": 500
}
```

---

### 3. Get Specific Question

Retrieve a single question from a quiz with full details.

**Endpoint:** `GET /api/eval/quiz/{quizId}/question/{questionId}`

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `quizId` | UUID (string) | Yes | Unique identifier of the quiz |
| `questionId` | UUID (string) | Yes | Unique identifier of the question |

**Query Parameters:** None

**Request Example:**

```bash
GET /api/eval/quiz/550e8400-e29b-41d4-a716-446655440000/question/660e8400-e29b-41d4-a716-446655440001
```

**Response Schema:**

```typescript
{
  "data": {
    "questionId": UUID,
    "orderIndex": number,
    "id": UUID,
    "type": "MCQ" | "MMCQ" | "TRUE_FALSE" | "DESCRIPTIVE" | "FILL_THE_BLANK" | "MATCHING" | "FILE_UPLOAD" | "CODING",
    "marks": number,
    "negativeMarks": number,
    "difficulty": "EASY" | "MEDIUM" | "HARD",
    "courseOutcome": "CO1" | "CO2" | "CO3" | "CO4" | "CO5" | "CO6" | "CO7" | "CO8" | null,
    "bloomTaxonomyLevel": "REMEMBER" | "UNDERSTAND" | "APPLY" | "ANALYZE" | "EVALUATE" | "CREATE" | null,
    "question": string,
    "questionData": JSON (structure varies by question type),
    "explaination": string | null,
    "solution": JSON (structure varies by question type),
    "createdById": UUID,
    "created_at": Date (ISO 8601),
    "updated_at": Date (ISO 8601)
  }
}
```

**Success Response (200):**

```json
{
  "data": {
    "questionId": "660e8400-e29b-41d4-a716-446655440001",
    "orderIndex": 1,
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "type": "MCQ",
    "marks": 2,
    "negativeMarks": 0.5,
    "difficulty": "MEDIUM",
    "courseOutcome": "CO1",
    "bloomTaxonomyLevel": "UNDERSTAND",
    "question": "What is the capital of France?",
    "questionData": {
      "options": [
        { "id": "opt1", "optionText": "Paris", "orderIndex": 1 },
        { "id": "opt2", "optionText": "London", "orderIndex": 2 },
        { "id": "opt3", "optionText": "Berlin", "orderIndex": 3 },
        { "id": "opt4", "optionText": "Madrid", "orderIndex": 4 }
      ]
    },
    "explaination": "Paris is the capital and most populous city of France.",
    "solution": {
      "correctOptions": [
        { "id": "opt1", "isCorrect": true }
      ]
    },
    "createdById": "770e8400-e29b-41d4-a716-446655440002",
    "created_at": "2025-01-10T10:00:00Z",
    "updated_at": "2025-02-05T15:30:00Z"
  }
}
```

**Error Response (400):**

```json
{
  "error": "Quiz ID and Question ID are required",
  "status": 400
}
```

**Error Response (404):**

```json
{
  "error": "Question not found",
  "status": 404
}
```

**Error Response (500):**

```json
{
  "error": "Failed to fetch quiz question",
  "status": 500
}
```

---

### 4. Get Quiz Settings

Retrieve evaluation settings and configuration for a specific quiz.

**Endpoint:** `GET /api/eval/quiz/{quizId}/settings`

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `quizId` | UUID (string) | Yes | Unique identifier of the quiz |

**Query Parameters:** None

**Request Example:**

```bash
GET /api/eval/quiz/550e8400-e29b-41d4-a716-446655440000/settings
```

**Response Schema:**

```typescript
{
  "settings": {
    "id": UUID,
    "mcqGlobalPartialMarking": boolean,
    "mcqGlobalNegativeMark": number | null,
    "mcqGlobalNegativePercent": number | null,
    "codingGlobalPartialMarking": boolean,
    "llmEvaluationEnabled": boolean,
    "llmProvider": string | null,
    "llmModelName": string | null,
    "fitbLlmSystemPrompt": string | null,
    "descLlmSystemPrompt": string | null
  }
}
```

**Success Response (200):**

```json
{
  "settings": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "mcqGlobalPartialMarking": true,
    "mcqGlobalNegativeMark": 1.0,
    "mcqGlobalNegativePercent": null,
    "codingGlobalPartialMarking": true,
    "llmEvaluationEnabled": true,
    "llmProvider": "openai",
    "llmModelName": "gpt-4",
    "fitbLlmSystemPrompt": "You are an evaluator...",
    "descLlmSystemPrompt": "Evaluate the descriptive answer..."
  }
}
```

**Error Response (400):**

```json
{
  "error": "Quiz ID is required",
  "status": 400
}
```

**Error Response (404):**

```json
{
  "error": "Quiz settings not found",
  "status": 404
}
```

**Error Response (500):**

```json
{
  "error": "Failed to fetch quiz settings",
  "status": 500
}
```

---

### 5. Get Student Quiz Responses

Retrieve the quiz response for a specific student in a specific quiz.

**Endpoint:** `GET /api/eval/quiz/{quizId}/student/{studentId}`

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `quizId` | UUID (string) | Yes | Unique identifier of the quiz |
| `studentId` | UUID (string) | Yes | Unique identifier of the student |

**Query Parameters:** None

**Request Example:**

```bash
GET /api/eval/quiz/550e8400-e29b-41d4-a716-446655440000/student/880e8400-e29b-41d4-a716-446655440004
```

**Response Schema:**

```typescript
{
  "response": {
    "quizId": UUID,
    "studentId": UUID,
    "startTime": Date (ISO 8601),
    "endTime": Date (ISO 8601) | null,
    "submissionTime": Date (ISO 8601) | null,
    "ip": Array<string> | null,
    "duration": interval (PostgreSQL interval format),
    "response": JSON | null (stores student answers),
    "score": Decimal | null,
    "violations": Array<string> | null,
    "isViolated": boolean,
    "submissionStatus": "NOT_SUBMITTED" | "SUBMITTED" | "AUTO_SUBMITTED",
    "evaluationStatus": "NOT_EVALUATED" | "EVALUATED" | "FAILED",
    "created_at": Date (ISO 8601),
    "updated_at": Date (ISO 8601)
  }
}
```

**Success Response (200):**

```json
{
  "response": {
    "quizId": "550e8400-e29b-41d4-a716-446655440000",
    "studentId": "880e8400-e29b-41d4-a716-446655440004",
    "startTime": "2025-02-15T10:00:00Z",
    "endTime": "2025-02-15T11:45:00Z",
    "submissionTime": "2025-02-15T11:45:30Z",
    "ip": ["192.168.1.100", "10.0.0.50"],
    "duration": "01:45:30",
    "response": {
      "660e8400-e29b-41d4-a716-446655440001": {
        "answer": "opt1",
        "markedForReview": false,
        "timeSpentSeconds": 45
      },
      "660e8400-e29b-41d4-a716-446655440002": {
        "answers": ["opt1", "opt3"],
        "markedForReview": true,
        "timeSpentSeconds": 120
      }
    },
    "score": "8.5",
    "violations": null,
    "isViolated": false,
    "submissionStatus": "SUBMITTED",
    "evaluationStatus": "EVALUATED",
    "created_at": "2025-02-15T10:00:00Z",
    "updated_at": "2025-02-15T11:50:00Z"
  }
}
```

**Error Response (400):**

```json
{
  "error": "Quiz ID and Student ID are required",
  "status": 400
}
```

**Error Response (404):**

```json
{
  "error": "Quiz response not found",
  "status": 404
}
```

**Error Response (500):**

```json
{
  "error": "Failed to fetch quiz response",
  "status": 500
}
```

---

### 6. Get All Quiz Responses

Retrieve all student responses for a specific quiz.

**Endpoint:** `GET /api/eval/quiz/{quizId}/student`

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `quizId` | UUID (string) | Yes | Unique identifier of the quiz |

**Query Parameters:** None

**Request Example:**

```bash
GET /api/eval/quiz/550e8400-e29b-41d4-a716-446655440000/student
```

**Response Schema:**

```typescript
{
  "responses": Array<{
    "quizId": UUID,
    "studentId": UUID,
    "startTime": Date (ISO 8601),
    "endTime": Date (ISO 8601) | null,
    "submissionTime": Date (ISO 8601) | null,
    "ip": Array<string> | null,
    "duration": interval (PostgreSQL interval format),
    "response": JSON | null (stores student answers),
    "score": Decimal | null,
    "violations": Array<string> | null,
    "isViolated": boolean,
    "submissionStatus": "NOT_SUBMITTED" | "SUBMITTED" | "AUTO_SUBMITTED",
    "evaluationStatus": "NOT_EVALUATED" | "EVALUATED" | "FAILED",
    "created_at": Date (ISO 8601),
    "updated_at": Date (ISO 8601)
  }>
}
```

**Success Response (200):**

```json
{
  "responses": [
    {
      "quizId": "550e8400-e29b-41d4-a716-446655440000",
      "studentId": "880e8400-e29b-41d4-a716-446655440004",
      "startTime": "2025-02-15T10:00:00Z",
      "endTime": "2025-02-15T11:45:00Z",
      "submissionTime": "2025-02-15T11:45:30Z",
      "ip": ["192.168.1.100"],
      "duration": "01:45:30",
      "response": {
        "660e8400-e29b-41d4-a716-446655440001": { "answer": "opt1" },
        "660e8400-e29b-41d4-a716-446655440002": { "answers": ["opt1", "opt3"] }
      },
      "score": "8.5",
      "violations": null,
      "isViolated": false,
      "submissionStatus": "SUBMITTED",
      "evaluationStatus": "EVALUATED",
      "created_at": "2025-02-15T10:00:00Z",
      "updated_at": "2025-02-15T11:50:00Z"
    },
    {
      "quizId": "550e8400-e29b-41d4-a716-446655440000",
      "studentId": "990e8400-e29b-41d4-a716-446655440005",
      "startTime": "2025-02-15T10:05:00Z",
      "endTime": null,
      "submissionTime": null,
      "ip": ["192.168.1.105"],
      "duration": "00:00:00",
      "response": null,
      "score": null,
      "violations": null,
      "isViolated": false,
      "submissionStatus": "NOT_SUBMITTED",
      "evaluationStatus": "NOT_EVALUATED",
      "created_at": "2025-02-15T10:05:00Z",
      "updated_at": "2025-02-15T10:05:00Z"
    }
  ]
}
```

**Error Response (400):**

```json
{
  "error": "Quiz ID is required",
  "status": 400
}
```

**Error Response (500):**

```json
{
  "error": "Failed to fetch quiz responses",
  "status": 500
}
```

---

## Data Models

### Quiz Model

```typescript
interface Quiz {
  id: string;                    // UUID
  name: string;                  // Quiz title
  description?: string;          // Long description
  instructions?: string;         // Instructions for students
  startTime: Date;               // When the quiz becomes available
  endTime: Date;                 // When the quiz closes
  duration: string;              // How long each student has (PostgreSQL interval)
  password?: string;             // Optional password to access quiz
  fullScreen: boolean;           // Require fullscreen mode
  shuffleQuestions: boolean;     // Randomize question order
  shuffleOptions: boolean;       // Randomize answer options
  linearQuiz: boolean;           // Linear navigation (no going back)
  calculator: boolean;           // Allow calculator during quiz
  autoSubmit: boolean;           // Auto-submit when time expires
  publishResult: boolean;        // Show scores to students after submission
  publishQuiz: boolean;          // Quiz is available to students
  kioskMode?: boolean;           // Kiosk/restricted mode
  createdById?: string;          // UUID of quiz creator
  created_at: Date;              // Creation timestamp
  updated_at: Date;              // Last modification timestamp
}
```

### Question Model

```typescript
interface Question {
  id: string;                           // UUID
  type: QuestionType;                   // MCQ, MMCQ, TRUE_FALSE, etc.
  marks: number;                        // Points for correct answer
  negativeMarks: number;                // Points deducted for wrong answer
  difficulty: DifficultyLevel;          // EASY, MEDIUM, HARD
  courseOutcome?: string;               // CO1-CO8
  bloomTaxonomyLevel?: string;          // REMEMBER, UNDERSTAND, APPLY, etc.
  question: string;                     // Question text/content
  questionData: JSON;                   // Type-specific data (options, etc.)
  explaination?: string;                // Why the answer is correct
  solution: JSON;                       // Correct answer(s)
  createdById: string;                  // UUID of question creator
  created_at: Date;                     // Creation timestamp
  updated_at: Date;                     // Last modification timestamp
}
```

### QuizResponse Model

```typescript
interface QuizResponse {
  quizId: string;                                                    // UUID of quiz
  studentId: string;                                                 // UUID of student
  startTime: Date;                                                   // When student started
  endTime?: Date;                                                    // When student finished
  submissionTime?: Date;                                             // Actual submission time
  ip?: string[];                                                     // IP addresses used during quiz
  duration: string;                                                  // Time taken (PostgreSQL interval)
  response?: JSON;                                                   // Student's answers
  score?: number;                                                    // Final score (decimal)
  violations?: string[];                                             // List of rule violations
  isViolated: boolean;                                               // Whether violations occurred
  submissionStatus: "NOT_SUBMITTED" | "SUBMITTED" | "AUTO_SUBMITTED"; // Submission state
  evaluationStatus: "NOT_EVALUATED" | "EVALUATED" | "FAILED";       // Evaluation state
  created_at: Date;                                                  // Record creation time
  updated_at: Date;                                                  // Last update time
}
```

### QuizEvaluationSettings Model

```typescript
interface QuizEvaluationSettings {
  id: string;                                     // UUID (same as quizId)
  mcqGlobalPartialMarking: boolean;               // Enable partial marking for MCQs globally
  mcqGlobalNegativeMark?: number;                 // Global negative mark value
  mcqGlobalNegativePercent?: number;              // Global negative mark percentage
  codingGlobalPartialMarking: boolean;            // Enable partial marking for coding questions
  llmEvaluationEnabled: boolean;                  // Enable LLM-based evaluation
  llmProvider?: string;                           // LLM provider (e.g., "openai")
  llmModelName?: string;                          // Model name (e.g., "gpt-4")
  fitbLlmSystemPrompt?: string;                   // System prompt for Fill-in-the-Blank evaluation
  descLlmSystemPrompt?: string;                   // System prompt for Descriptive evaluation
}
```

### Question Types & Structures

#### MCQ (Multiple Choice Question)

```typescript
interface MCQQuestion extends Question {
  type: "MCQ";
  questionData: {
    options: Array<{
      id: string;
      optionText: string;
      orderIndex: number;
    }>;
  };
  solution: {
    correctOptions: Array<{
      id: string;
      isCorrect: boolean;
    }>;
  };
}
```

#### MMCQ (Multiple Select Multiple Choice Question)

```typescript
interface MMCQQuestion extends Question {
  type: "MMCQ";
  questionData: {
    options: Array<{
      id: string;
      optionText: string;
      orderIndex: number;
    }>;
  };
  solution: {
    correctOptions: Array<{
      id: string;
      isCorrect: boolean;
    }>;
  };
}
```

#### TRUE_FALSE

```typescript
interface TrueFalseQuestion extends Question {
  type: "TRUE_FALSE";
  solution: {
    trueFalseAnswer: boolean;
  };
}
```

#### FILL_THE_BLANK

```typescript
interface FillInBlanksQuestion extends Question {
  type: "FILL_THE_BLANK";
  questionData: {
    config: {
      blankCount: number;
      acceptableAnswers: Record<number, {
        answers: string[];
        type: "TEXT" | "NUMBER" | "UPPERCASE" | "LOWERCASE";
      }>;
      evaluationType: "STRICT" | "NORMAL" | "LENIENT";
    };
  };
  solution: {
    acceptableAnswers: Record<number, {
      answers: string[];
      type: string;
    }>;
  };
}
```

#### MATCHING

```typescript
interface MatchingQuestion extends Question {
  type: "MATCHING";
  questionData: {
    options: Array<{
      id: string;
      isLeft: boolean;
      text: string;
      orderIndex: number;
    }>;
  };
  solution: {
    options: Array<{
      id: string;
      matchPairIds: string[];
    }>;
  };
}
```

#### DESCRIPTIVE

```typescript
interface DescriptiveQuestion extends Question {
  type: "DESCRIPTIVE";
  questionData: {
    config: {
      minWords?: number;
      maxWords?: number;
    };
  };
  solution: {
    modelAnswer?: string;
    keywords?: string[];
  };
}
```

#### CODING

```typescript
interface CodingQuestion extends Question {
  type: "CODING";
  questionData: {
    config: {
      language: "JAVA" | "PYTHON" | "CPP" | "JAVASCRIPT" | "C" | "OCTAVE" | "SCALA";
      templateCode?: string;
      boilerplateCode?: string;
      timeLimitMs?: number;
      memoryLimitMb?: number;
    };
    testCases: Array<{
      id: string;
      input: string;
      visibility: "VISIBLE" | "HIDDEN";
      marksWeightage?: number;
      orderIndex: number;
    }>;
  };
  solution: {
    referenceSolution?: string;
    testCases: Array<{
      id: string;
      expectedOutput: string;
    }>;
  };
}
```

#### FILE_UPLOAD

```typescript
interface FileUploadQuestion extends Question {
  type: "FILE_UPLOAD";
  questionData: {
    config: {
      allowedFileTypes?: string[];
      maxFileSizeInMB?: number;
      maxFiles?: number;
    };
  };
}
```

---

## Error Codes

| Error Code | HTTP Status | Description | Common Cause |
|---|---|---|---|
| `Quiz ID is required` | 400 | Quiz ID parameter is missing | Missing or empty `quizId` parameter |
| `Quiz not found` | 404 | Quiz with given ID does not exist | Invalid or non-existent `quizId` |
| `Quiz ID and Question ID are required` | 400 | One or both required parameters missing | Missing `quizId` or `questionId` |
| `Question not found` | 404 | Question not found in the quiz | Invalid `questionId` or not part of quiz |
| `Quiz ID and Student ID are required` | 400 | One or both required parameters missing | Missing `quizId` or `studentId` |
| `Quiz response not found` | 404 | No response record for student in quiz | Student hasn't started quiz or invalid IDs |
| `Quiz settings not found` | 404 | Settings not found for the quiz | Invalid `quizId` or settings not initialized |
| `Failed to fetch quiz data` | 500 | Database error occurred | Server/database connection issue |
| `Failed to fetch quiz questions` | 500 | Database error occurred | Server/database connection issue |
| `Failed to fetch quiz question` | 500 | Database error occurred | Server/database connection issue |
| `Failed to fetch quiz responses` | 500 | Database error occurred | Server/database connection issue |
| `Failed to fetch quiz response` | 500 | Database error occurred | Server/database connection issue |
| `Failed to fetch quiz settings` | 500 | Database error occurred | Server/database connection issue |

---

## Implementation Notes

### Endpoints Under Development

The following endpoints are currently placeholders and require implementation:

1. **`POST /api/eval/quiz/{quizId}/save/{studentId}`** - Not yet implemented (for saving student responses)

### Security Considerations

1. **Add Authentication Middleware** - Implement JWT validation for all endpoints
2. **Add Authorization Checks** - Verify user has permission to access quiz/student data
3. **Validate Input** - Use schema validation for all incoming parameters
4. **Rate Limiting** - Implement rate limiting to prevent abuse
5. **Data Sanitization** - Sanitize all outputs to prevent XSS attacks
6. **CORS Configuration** - Configure CORS appropriately for backend integration

### Recommended Enhancements

1. Add pagination support for large result sets (e.g., `page`, `limit` query parameters)
2. Add filtering options (e.g., by submission status, evaluation status)
3. Add sorting options (e.g., by score, submission time)
4. Implement batch operations for better performance
5. Add caching layer (Redis) for frequently accessed quiz data
6. Add comprehensive logging using the existing logger in `src/lib/logger.ts`
7. Add analytics tracking using `src/hooks/use-analytics.ts`
8. Add proper error tracking and monitoring

---

## Version History

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2025-02-16 | Initial API documentation |

---

## Contact & Support

For backend implementation support or API clarifications, contact the Evalify development team.
