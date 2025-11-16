from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


class QuestionType(str, Enum):
    MCQ = "MCQ"
    MMCQ = "MMCQ"
    TRUE_FALSE = "TRUE_FALSE"
    DESCRIPTIVE = "DESCRIPTIVE"
    FILL_THE_BLANK = "FILL_THE_BLANK"
    MATCHING = "MATCHING"
    FILE_UPLOAD = "FILE_UPLOAD"
    CODING = "CODING"


class DifficultyLevel(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class CourseOutcome(str, Enum):
    CO1 = "CO1"
    CO2 = "CO2"
    CO3 = "CO3"
    CO4 = "CO4"
    CO5 = "CO5"
    CO6 = "CO6"
    CO7 = "CO7"
    CO8 = "CO8"


class BloomTaxonomyLevel(str, Enum):
    REMEMBER = "REMEMBER"
    UNDERSTAND = "UNDERSTAND"
    APPLY = "APPLY"
    ANALYZE = "ANALYZE"
    EVALUATE = "EVALUATE"
    CREATE = "CREATE"


class SubmissionStatus(str, Enum):
    NOT_SUBMITTED = "NOT_SUBMITTED"
    SUBMITTED = "SUBMITTED"
    AUTO_SUBMITTED = "AUTO_SUBMITTED"


class EvaluationStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    EVALUATED = "EVALUATED"
    FAILED = "FAILED"


class BlankEvaluationType(str, Enum):
    STRICT = "STRICT"
    NORMAL = "NORMAL"
    LENIENT = "LENIENT"


class BlankAnswerType(str, Enum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    UPPERCASE = "UPPERCASE"
    LOWERCASE = "LOWERCASE"


class CodingLanguage(str, Enum):
    JAVA = "JAVA"
    PYTHON = "PYTHON"
    CPP = "CPP"
    JAVASCRIPT = "JAVASCRIPT"
    C = "C"
    OCTAVE = "OCTAVE"
    SCALA = "SCALA"


class TestCaseVisibility(str, Enum):
    VISIBLE = "VISIBLE"
    HIDDEN = "HIDDEN"


class QuestionOption(BaseModel):
    id: str
    optionText: str
    orderIndex: int


class CorrectOption(BaseModel):
    id: str
    isCorrect: bool


class MCQQuestionData(BaseModel):
    options: List[QuestionOption]


class MCQSolution(BaseModel):
    correctOptions: List[CorrectOption]


class TrueFalseQuestionData(BaseModel):
    model_config = ConfigDict(extra="allow")


class TrueFalseSolution(BaseModel):
    trueFalseAnswer: bool


class BlankAcceptableAnswer(BaseModel):
    answers: List[str]
    type: BlankAnswerType


class FillBlankConfig(BaseModel):
    blankCount: int
    acceptableAnswers: Dict[int, BlankAcceptableAnswer]
    evaluationType: BlankEvaluationType


class FillBlankQuestionData(BaseModel):
    config: FillBlankConfig


class FillBlankSolution(BaseModel):
    acceptableAnswers: Dict[int, BlankAcceptableAnswer]


class MatchingOption(BaseModel):
    id: str
    isLeft: bool
    text: str
    orderIndex: int


class MatchingQuestionData(BaseModel):
    options: List[MatchingOption]


class MatchingSolutionOption(BaseModel):
    id: str
    matchPairIds: List[str]


class MatchingSolution(BaseModel):
    options: List[MatchingSolutionOption]


class DescriptiveConfig(BaseModel):
    minWords: Optional[int] = None
    maxWords: Optional[int] = None


class DescriptiveQuestionData(BaseModel):
    config: DescriptiveConfig


class DescriptiveSolution(BaseModel):
    modelAnswer: Optional[str] = None
    keywords: Optional[List[str]] = None


class CodingConfig(BaseModel):
    language: CodingLanguage
    templateCode: Optional[str] = None
    boilerplateCode: Optional[str] = None
    timeLimitMs: Optional[int] = None
    memoryLimitMb: Optional[int] = None


class CodingTestCase(BaseModel):
    id: str
    input: str
    visibility: TestCaseVisibility
    marksWeightage: Optional[float] = None
    orderIndex: int


class CodingQuestionData(BaseModel):
    config: CodingConfig
    testCases: List[CodingTestCase]


class CodingSolutionTestCase(BaseModel):
    id: str
    expectedOutput: str


class CodingSolution(BaseModel):
    referenceSolution: Optional[str] = None
    testCases: List[CodingSolutionTestCase]


class FileUploadConfig(BaseModel):
    allowedFileTypes: Optional[List[str]] = None
    maxFileSizeInMB: Optional[int] = None
    maxFiles: Optional[int] = None


class FileUploadQuestionData(BaseModel):
    config: FileUploadConfig


class GenericQuestionData(BaseModel):
    """Fallback schema for question types that are not yet modeled."""

    model_config = ConfigDict(extra="allow")


class GenericSolution(BaseModel):
    """Fallback schema for solution payloads that are not yet modeled."""

    model_config = ConfigDict(extra="allow")


QuestionData = Union[
    MCQQuestionData,
    TrueFalseQuestionData,
    FillBlankQuestionData,
    MatchingQuestionData,
    DescriptiveQuestionData,
    CodingQuestionData,
    FileUploadQuestionData,
    GenericQuestionData,
]

QuestionSolution = Union[
    MCQSolution,
    TrueFalseSolution,
    FillBlankSolution,
    MatchingSolution,
    DescriptiveSolution,
    CodingSolution,
    GenericSolution,
]


class QuizQuestion(BaseModel):
    questionId: str
    orderIndex: int
    id: str
    type: QuestionType
    marks: float
    negativeMarks: float
    difficulty: DifficultyLevel
    courseOutcome: Optional[CourseOutcome] = None
    bloomTaxonomyLevel: Optional[BloomTaxonomyLevel] = None
    question: str
    questionData: QuestionData
    # NOTE: The backend API uses the misspelled field name 'explaination'.
    # Use the correct spelling 'explanation' in code, and alias to 'explaination' for compatibility.
    explanation: Optional[str] = Field(
        default=None, description="Explanation text from backend", alias="explaination"
    )
    solution: Optional[QuestionSolution] = None
    createdById: str
    created_at: datetime
    updated_at: datetime


class Quiz(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    startTime: datetime
    endTime: datetime
    duration: str
    password: Optional[str] = None
    fullScreen: bool
    shuffleQuestions: bool
    shuffleOptions: bool
    linearQuiz: bool
    calculator: bool
    autoSubmit: bool
    publishResult: bool
    publishQuiz: bool
    kioskMode: Optional[bool] = None
    createdById: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class QuizDetailsResponse(BaseModel):
    quiz: Quiz


class QuizQuestionsResponse(BaseModel):
    data: List[QuizQuestion]


class QuizQuestionResponse(BaseModel):
    data: QuizQuestion


class QuizSettingsResponse(BaseModel):
    message: str


class QuizResponseRecord(BaseModel):
    quizId: str
    studentId: str
    startTime: datetime
    endTime: Optional[datetime] = None
    submissionTime: Optional[datetime] = None
    ip: Optional[List[str]] = None
    duration: str
    response: Optional[Dict[str, Any]] = None
    score: Optional[float] = None
    violations: Optional[List[str]] = None
    isViolated: bool
    submissionStatus: SubmissionStatus
    evaluationStatus: EvaluationStatus
    created_at: datetime
    updated_at: datetime


class QuizStudentResponse(BaseModel):
    response: QuizResponseRecord


class QuizResponsesResponse(BaseModel):
    responses: List[QuizResponseRecord]
