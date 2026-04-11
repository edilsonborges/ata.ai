from pydantic import BaseModel, Field


class Participant(BaseModel):
    name: str
    role: str | None = None
    type: str | None = None  # condutor|executor|apoio


class Topic(BaseModel):
    title: str
    summary: str
    relevance_pct: int
    quote: str | None = None
    quote_ts: str | None = None  # [MM:SS]


class Decision(BaseModel):
    text: str
    context: str | None = None
    quote_ts: str | None = None


class Finding(BaseModel):
    text: str
    detail: str | None = None


class Action(BaseModel):
    title: str
    owner: str | None = None
    deadline: str | None = None
    priority: str | None = None  # alta|media|baixa
    status: str | None = None


class Risk(BaseModel):
    text: str
    probability: int = Field(ge=1, le=10)
    impact: int = Field(ge=1, le=10)


class TimelineEvent(BaseModel):
    range: str  # MM:SS - MM:SS
    title: str
    tone: str  # positive|neutral|concern|constructive
    summary: str


class Entity(BaseModel):
    name: str
    kind: str  # pessoa|sistema|orgao|tech|ferramenta


class Keyword(BaseModel):
    word: str
    weight: int


class AnalysisResult(BaseModel):
    slug: str
    title: str
    meeting_date: str | None = None
    duration: str  # MM:SS
    summary: str
    participants: list[Participant] = []
    topics: list[Topic] = []
    decisions: list[Decision] = []
    findings: list[Finding] = []
    actions: list[Action] = []
    risks: list[Risk] = []
    timeline: list[TimelineEvent] = []
    entities: list[Entity] = []
    sentiment: str | None = None
    engagement: str | None = None
    keywords: list[Keyword] = []
    insights: list[str] = []
    flow: list[str] = []
