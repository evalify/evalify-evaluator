from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal, TypeVar, Generic

from pydantic import BaseModel, ConfigDict, Field


class QuestionType(str, Enum):
    MCQ = "MCQ"
    MMCQ = "MMCQ"
    TRUE_FALSE = "TRUE_FALSE"
    DESCRIPTIVE = "DESCRIPTIVE"
    FILL_THE_BLANK = "FILL_THE_BLANK"
    MATCHING = "MATCHING"
    FILE_UPLOAD = "FILE_UPLOAD"
    CODING = "CODING"


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
    blankWeights: Optional[Dict[int, float]] = None
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


# ==============================================================================
# Student Answer Schemas
# ==============================================================================


class BaseStudentAnswer(BaseModel):
    """Base wrapper for student answers if they always come wrapped."""

    studentAnswer: Any


class MCQStudentAnswer(BaseStudentAnswer):
    studentAnswer: str  # The selected option ID


class MMCQStudentAnswer(BaseStudentAnswer):
    studentAnswer: List[str]  # List of selected option IDs


class TrueFalseStudentAnswer(BaseStudentAnswer):
    studentAnswer: Union[bool, str]  # "true"/"false" or True/False


class MatchStudentAnswerItem(BaseModel):
    id: str
    matchPairIds: List[str]


class MatchStudentAnswer(BaseStudentAnswer):
    studentAnswer: List[MatchStudentAnswerItem]


class DescriptiveStudentAnswer(BaseStudentAnswer):
    studentAnswer: str


class FillBlankStudentAnswer(BaseStudentAnswer):
    studentAnswer: Dict[int, str]  # Map of blank index to answer text


class CodingStudentAnswer(BaseStudentAnswer):
    studentAnswer: str  # The code submitted


class FileUploadStudentAnswer(BaseStudentAnswer):
    studentAnswer: str  # The file URL or path


T = TypeVar("T")


class DataWrapper(BaseModel, Generic[T]):
    data: T
    version: int


class BaseQuizQuestion(BaseModel):
    """Base schema for quiz questions."""

    model_config = ConfigDict(extra="ignore")

    id: str
    marks: float
    negativeMarks: float
    question: str


class MCQQuizQuestion(BaseQuizQuestion):
    type: Literal[QuestionType.MCQ]
    questionData: DataWrapper[MCQQuestionData]
    solution: Optional[DataWrapper[MCQSolution]] = None


class MMCQQuizQuestion(BaseQuizQuestion):
    type: Literal[QuestionType.MMCQ]
    questionData: DataWrapper[MCQQuestionData]
    solution: Optional[DataWrapper[MCQSolution]] = None


class TrueFalseQuizQuestion(BaseQuizQuestion):
    type: Literal[QuestionType.TRUE_FALSE]
    questionData: DataWrapper[TrueFalseQuestionData]
    solution: Optional[DataWrapper[TrueFalseSolution]] = None


class DescriptiveQuizQuestion(BaseQuizQuestion):
    type: Literal[QuestionType.DESCRIPTIVE]
    questionData: DataWrapper[DescriptiveQuestionData]
    solution: Optional[DataWrapper[DescriptiveSolution]] = None


class FillBlankQuizQuestion(BaseQuizQuestion):
    type: Literal[QuestionType.FILL_THE_BLANK]
    questionData: DataWrapper[FillBlankQuestionData]
    solution: Optional[DataWrapper[FillBlankSolution]] = None


class MatchingQuizQuestion(BaseQuizQuestion):
    type: Literal[QuestionType.MATCHING]
    questionData: DataWrapper[MatchingQuestionData]
    solution: Optional[DataWrapper[MatchingSolution]] = None


class CodingQuizQuestion(BaseQuizQuestion):
    type: Literal[QuestionType.CODING]
    questionData: DataWrapper[CodingQuestionData]
    solution: Optional[DataWrapper[CodingSolution]] = None


class FileUploadQuizQuestion(BaseQuizQuestion):
    type: Literal[QuestionType.FILE_UPLOAD]
    questionData: DataWrapper[FileUploadQuestionData]
    solution: Optional[DataWrapper[GenericSolution]] = None


class FallbackQuizQuestion(BaseQuizQuestion):
    type: QuestionType
    questionData: DataWrapper[GenericQuestionData]
    solution: Optional[DataWrapper[GenericSolution]] = None


QuizQuestion = Union[
    MCQQuizQuestion,
    MMCQQuizQuestion,
    TrueFalseQuizQuestion,
    DescriptiveQuizQuestion,
    FillBlankQuizQuestion,
    MatchingQuizQuestion,
    CodingQuizQuestion,
    FileUploadQuizQuestion,
    FallbackQuizQuestion,
]


class Quiz(BaseModel):
    """Minimal quiz schema - only the ID is needed for evaluation.

    Extra fields from the backend API are ignored to allow schema evolution
    without breaking changes.
    """

    model_config = ConfigDict(extra="ignore")

    id: str


class QuizDetailsResponse(BaseModel):
    quiz: Quiz


class QuizQuestionsResponse(BaseModel):
    data: List[QuizQuestion]


class QuizQuestionResponse(BaseModel):
    data: QuizQuestion


class QuizSettings(BaseModel):
    id: str
    mcqGlobalPartialMarking: bool
    mcqGlobalNegativeMark: Optional[float] = Field(
        default=None,
        ge=0,
        description="Fixed negative marks deducted for incorrect MCQ answers.",
    )
    mcqGlobalNegativePercent: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Negative marking fraction in [0, 1] for incorrect MCQ answers.",
    )
    codingGlobalPartialMarking: bool
    llmEvaluationEnabled: bool
    llmProvider: Optional[str] = None
    llmModelName: Optional[str] = None
    fitbLlmSystemPrompt: Optional[str] = None
    descLlmSystemPrompt: Optional[str] = None


class QuizSettingsResponse(BaseModel):
    settings: QuizSettings


class QuizResponseRecord(BaseModel):
    """Student quiz response schema - only fields needed for evaluation workflow.

    Extra fields from the backend API are ignored to allow schema evolution
    without breaking changes.
    """

    model_config = ConfigDict(extra="ignore")

    quizId: str
    studentId: str
    response: Optional[Dict[str, Any]] = None  # Student answers
    score: Optional[float] = None
    submissionStatus: SubmissionStatus
    evaluationStatus: EvaluationStatus


class QuizStudentResponse(BaseModel):
    response: QuizResponseRecord


class QuizResponsesResponse(BaseModel):
    responses: List[QuizResponseRecord]
