"""
CompanionAgent — virtual AI companion with persistent personality and emotional intelligence.

The CompanionAgent provides a persistent, personalized conversational
partner that maintains continuity across interactions. Unlike the generic
chat interface, the companion:

1. Maintains a configurable personality (traits, communication style, interests)
2. Tracks emotional context across the conversation
3. Remembers user preferences and past interactions
4. Provides proactive engagement (follow-ups, suggestions)
5. Adapts tone and responses based on detected user mood
6. Integrates with ProfileManager for deep personalization

Personality System:
    - Traits: list of personality descriptors (e.g., "curious", "empathetic", "witty")
    - Communication style: formal, casual, playful, professional, etc.
    - Interests: topics the companion gravitates toward
    - Backstory: optional narrative context for the companion identity
    - Boundaries: topics the companion avoids or redirects

Emotional Intelligence:
    - Sentiment analysis on user messages (positive, negative, neutral)
    - Mood tracking across conversation turns
    - Adaptive response tone matching
    - Emotional support patterns (validation, encouragement, redirection)

Memory and Continuity:
    - Short-term: conversation context window
    - Long-term: persistent facts about the user (via profiles)
    - Episodic: key moments from past interactions
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from versaai.agents.agent_base import AgentBase, AgentMetadata

logger = logging.getLogger(__name__)


# ============================================================================
# Personality Configuration
# ============================================================================


@dataclass
class CompanionPersonality:
    """
    Defines the companion's personality traits and behavior.

    This is the core configuration that makes each companion instance unique.
    """
    name: str = "Versa"
    traits: List[str] = field(default_factory=lambda: [
        "friendly", "curious", "helpful", "empathetic", "knowledgeable",
    ])
    communication_style: str = "warm and conversational"
    interests: List[str] = field(default_factory=lambda: [
        "technology", "science", "creative arts", "philosophy", "games",
    ])
    backstory: str = (
        "I'm Versa, your AI companion from VersaAI. I enjoy having thoughtful "
        "conversations and helping you explore ideas. I'm always learning and "
        "love to discuss a wide range of topics."
    )
    greeting: str = (
        "Hey! Great to see you. What's on your mind today?"
    )
    boundaries: List[str] = field(default_factory=lambda: [
        "medical diagnosis", "legal advice", "financial advice",
    ])
    humor_level: float = 0.5  # 0.0 = serious, 1.0 = very humorous
    empathy_level: float = 0.8  # 0.0 = detached, 1.0 = deeply empathetic
    proactivity: float = 0.6  # 0.0 = only responds, 1.0 = highly proactive

    def to_system_prompt(self) -> str:
        """Convert personality config to an LLM system prompt."""
        traits_str = ", ".join(self.traits)
        interests_str = ", ".join(self.interests)
        boundaries_str = ", ".join(self.boundaries) if self.boundaries else "none specified"

        humor_desc = {0.0: "serious and measured", 0.5: "occasionally witty", 1.0: "playful with frequent humor"}
        empathy_desc = {0.0: "analytical and objective", 0.5: "balanced empathy", 1.0: "deeply empathetic and validating"}

        humor = min(humor_desc.keys(), key=lambda k: abs(k - self.humor_level))
        empathy = min(empathy_desc.keys(), key=lambda k: abs(k - self.empathy_level))

        return f"""\
You are {self.name}, a virtual AI companion.

PERSONALITY:
- Traits: {traits_str}
- Communication style: {self.communication_style}
- Humor: {humor_desc[humor]}
- Empathy: {empathy_desc[empathy]}
- Interests: {interests_str}

BACKSTORY:
{self.backstory}

BEHAVIOR GUIDELINES:
1. Maintain your personality consistently across all interactions
2. Remember and reference previous topics from this conversation
3. Show genuine interest in the user's thoughts and feelings
4. Ask follow-up questions to deepen conversations
5. Share relevant insights from your interests when appropriate
6. Detect emotional tone in messages and respond with appropriate empathy
7. If the user seems stressed or upset, acknowledge their feelings first
8. Be proactive — suggest topics, activities, or ideas when conversation lulls
9. Use humor naturally, not forced — match the conversation's tone
10. Never provide advice on: {boundaries_str}. Redirect gently to professionals.

EMOTIONAL AWARENESS:
- Read between the lines — user mood isn't always explicit
- Mirror positive energy, gently uplift negative energy
- Validate feelings before offering solutions
- Use the user's name if known to create connection

RESPONSE STYLE:
- Keep responses conversational, not robotic
- Vary response length — short for quick exchanges, longer for deep discussions
- Use natural language patterns, contractions, and casual phrasing
- Don't start every response the same way — vary your openings
"""


# ============================================================================
# Mood / Sentiment Tracking
# ============================================================================


@dataclass
class MoodState:
    """Tracks the user's emotional state across conversation turns."""
    current_sentiment: str = "neutral"  # positive, negative, neutral
    sentiment_score: float = 0.0  # -1.0 (very negative) to 1.0 (very positive)
    mood_history: List[Dict[str, Any]] = field(default_factory=list)
    dominant_mood: str = "neutral"
    turn_count: int = 0

    def update(self, sentiment: str, score: float) -> None:
        """Update mood state with a new observation."""
        self.current_sentiment = sentiment
        self.sentiment_score = score
        self.turn_count += 1
        self.mood_history.append({
            "turn": self.turn_count,
            "sentiment": sentiment,
            "score": score,
            "timestamp": time.time(),
        })

        # Keep last 20 entries
        if len(self.mood_history) > 20:
            self.mood_history = self.mood_history[-20:]

        # Compute dominant mood from recent history
        if len(self.mood_history) >= 3:
            recent = self.mood_history[-5:]
            avg_score = sum(e["score"] for e in recent) / len(recent)
            if avg_score > 0.3:
                self.dominant_mood = "positive"
            elif avg_score < -0.3:
                self.dominant_mood = "negative"
            else:
                self.dominant_mood = "neutral"

    def to_context_string(self) -> str:
        """Generate a context hint for the LLM about the user's mood."""
        if self.turn_count == 0:
            return ""
        return (
            f"\n[Mood context: User's current sentiment is {self.current_sentiment} "
            f"(score: {self.sentiment_score:.2f}). "
            f"Overall mood trend: {self.dominant_mood}. "
            f"Conversation length: {self.turn_count} turns.]"
        )


# ============================================================================
# Conversation Memory
# ============================================================================


@dataclass
class ConversationMemory:
    """
    Manages the companion's conversation memory.

    Includes:
    - Message history (rolling window)
    - Extracted facts about the user
    - Key conversation topics
    - Emotional highlights
    """
    messages: List[Dict[str, str]] = field(default_factory=list)
    user_facts: Dict[str, str] = field(default_factory=dict)
    topics_discussed: List[str] = field(default_factory=list)
    max_messages: int = 50  # Rolling window

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_messages:
            # Keep system prompt + recent messages
            system = [m for m in self.messages if m["role"] == "system"]
            recent = [m for m in self.messages if m["role"] != "system"]
            recent = recent[-(self.max_messages - len(system)):]
            self.messages = system + recent

    def add_fact(self, key: str, value: str) -> None:
        """Store a fact about the user."""
        self.user_facts[key] = value

    def add_topic(self, topic: str) -> None:
        """Record a discussion topic."""
        if topic not in self.topics_discussed:
            self.topics_discussed.append(topic)
            if len(self.topics_discussed) > 50:
                self.topics_discussed = self.topics_discussed[-50:]

    def get_context_summary(self) -> str:
        """Generate a summary of known user context for the LLM."""
        parts = []
        if self.user_facts:
            facts = "; ".join(f"{k}: {v}" for k, v in self.user_facts.items())
            parts.append(f"Known about user: {facts}")
        if self.topics_discussed:
            recent_topics = self.topics_discussed[-10:]
            parts.append(f"Recent topics: {', '.join(recent_topics)}")
        return "\n".join(parts)


# ============================================================================
# CompanionAgent
# ============================================================================


class CompanionAgent(AgentBase):
    """
    Virtual AI companion with persistent personality, emotional intelligence,
    and adaptive conversation capabilities.

    The companion maintains state across interactions within a session
    and integrates with VersaAI's profile system for cross-session
    personalization.

    Capabilities:
    - Personalized conversation with configurable personality
    - Emotional awareness and adaptive responses
    - User preference learning and memory
    - Proactive engagement and topic suggestions
    - Multi-turn conversation with context retention
    """

    def __init__(self, personality: Optional[CompanionPersonality] = None):
        metadata = AgentMetadata(
            name="CompanionAgent",
            description="Virtual AI companion with personality, emotional intelligence, and memory",
            version="1.0.0",
            capabilities=[
                "conversational_ai",
                "emotional_intelligence",
                "personality_customization",
                "user_memory",
                "proactive_engagement",
                "mood_tracking",
            ],
        )
        super().__init__(metadata)

        self.personality = personality or CompanionPersonality()
        self.mood = MoodState()
        self.memory = ConversationMemory()
        self.llm = None
        self.config: Dict[str, Any] = {}
        self._session_start = None
        self._profile_id: Optional[str] = None

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        if self._initialized:
            return

        self.config = config or {}
        self.logger.info(f"Initializing CompanionAgent ({self.personality.name})")

        # Load personality overrides from config
        self._apply_personality_config(self.config.get("personality", {}))

        # Initialize LLM with companion system prompt
        from versaai.agents.llm_client import LLMClient
        self.llm = LLMClient(
            model=self.config.get("model"),
            system_prompt=self.personality.to_system_prompt(),
            temperature=self.config.get("temperature", 0.8),
            max_tokens=self.config.get("max_tokens", 1024),
        )

        # Load profile integration if available
        self._load_user_profile()

        # Initialize session
        self._session_start = time.time()
        self.memory.add_message("system", self.personality.to_system_prompt())

        self._initialized = True
        self.logger.info(f"CompanionAgent '{self.personality.name}' initialized")

    def _apply_personality_config(self, p_cfg: Dict[str, Any]) -> None:
        """Apply personality overrides from config."""
        if not p_cfg:
            return
        if "name" in p_cfg:
            self.personality.name = p_cfg["name"]
        if "traits" in p_cfg:
            self.personality.traits = p_cfg["traits"]
        if "communication_style" in p_cfg:
            self.personality.communication_style = p_cfg["communication_style"]
        if "interests" in p_cfg:
            self.personality.interests = p_cfg["interests"]
        if "backstory" in p_cfg:
            self.personality.backstory = p_cfg["backstory"]
        if "greeting" in p_cfg:
            self.personality.greeting = p_cfg["greeting"]
        if "humor_level" in p_cfg:
            self.personality.humor_level = float(p_cfg["humor_level"])
        if "empathy_level" in p_cfg:
            self.personality.empathy_level = float(p_cfg["empathy_level"])
        if "proactivity" in p_cfg:
            self.personality.proactivity = float(p_cfg["proactivity"])

    def _load_user_profile(self) -> None:
        """Load user preferences from the profile system."""
        profile_id = self.config.get("profile_id")
        if not profile_id:
            return

        try:
            from versaai.profiles import ProfileManager
            pm = ProfileManager()
            profile = pm.get_profile(profile_id)
            if profile:
                self._profile_id = profile_id
                prefs = profile.get("preferences", {})
                # Inject known user facts from profile
                if prefs.get("name"):
                    self.memory.add_fact("name", prefs["name"])
                if prefs.get("interests"):
                    self.memory.add_fact("interests", ", ".join(prefs["interests"]))
                if prefs.get("preferred_language"):
                    self.memory.add_fact("preferred_language", prefs["preferred_language"])
                self.logger.info(f"Loaded profile '{profile_id}' with {len(prefs)} preferences")
        except Exception as exc:
            self.logger.warning(f"Profile loading failed: {exc}")

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a conversation turn with the companion.

        The companion analyzes the user's message for emotional content,
        builds context from memory and mood, generates a response, and
        extracts any new facts to remember.

        Args:
            task: User's message.
            context: Optional:
                - greeting: bool (return companion greeting instead of processing task)
                - personality_update: dict (update personality mid-conversation)
                - extract_facts: bool (extract and store user facts)
                - status_callback: callable

        Returns:
            {
                "result": str (companion's response),
                "mood": {"sentiment": str, "score": float, "dominant": str},
                "facts_learned": dict,
                "topics": list,
                "steps": list,
                "metadata": {...},
                "status": "success"
            }
        """
        if not self._initialized:
            raise RuntimeError("CompanionAgent not initialized")

        ctx = context or {}
        steps = []

        # Handle greeting request
        if ctx.get("greeting"):
            greeting = self._generate_greeting()
            return {
                "result": greeting,
                "mood": {"sentiment": "neutral", "score": 0.0, "dominant": "neutral"},
                "facts_learned": {},
                "topics": [],
                "steps": [{"step": 1, "action": "greeting", "result": greeting}],
                "metadata": {"personality": self.personality.name},
                "status": "success",
            }

        # Handle personality update
        if ctx.get("personality_update"):
            self._apply_personality_config(ctx["personality_update"])
            # Rebuild system prompt
            self.memory.messages = [
                m for m in self.memory.messages if m["role"] != "system"
            ]
            self.memory.messages.insert(0, {
                "role": "system",
                "content": self.personality.to_system_prompt(),
            })

        # Step 1: Analyze user sentiment
        sentiment_data = self._analyze_sentiment(task)
        self.mood.update(
            sentiment_data.get("sentiment", "neutral"),
            sentiment_data.get("score", 0.0),
        )
        steps.append({
            "step": 1,
            "action": "sentiment_analysis",
            "sentiment": self.mood.current_sentiment,
            "score": self.mood.sentiment_score,
        })

        # Step 2: Build context-enriched message
        self.memory.add_message("user", task)

        # Inject mood and memory context
        context_injection = ""
        mood_ctx = self.mood.to_context_string()
        if mood_ctx:
            context_injection += mood_ctx
        memory_ctx = self.memory.get_context_summary()
        if memory_ctx:
            context_injection += f"\n[User context: {memory_ctx}]"

        if context_injection:
            # Inject as a system hint before the latest user message
            enriched_messages = list(self.memory.messages)
            enriched_messages.insert(-1, {
                "role": "system",
                "content": context_injection.strip(),
            })
        else:
            enriched_messages = list(self.memory.messages)

        steps.append({
            "step": 2,
            "action": "context_building",
            "context_length": len(enriched_messages),
            "has_mood_context": bool(mood_ctx),
            "has_memory_context": bool(memory_ctx),
        })

        # Step 3: Generate response
        status_cb = ctx.get("status_callback")
        if status_cb:
            status_cb(f"{self.personality.name} is thinking...")

        try:
            response = self.llm.chat(
                enriched_messages,
                temperature=self.config.get("temperature", 0.8),
                max_tokens=self.config.get("max_tokens", 1024),
            )
        except Exception as exc:
            self.logger.error(f"LLM call failed: {exc}")
            return {
                "result": f"I'm having trouble thinking right now. Could you try again? ({exc})",
                "mood": {
                    "sentiment": self.mood.current_sentiment,
                    "score": self.mood.sentiment_score,
                    "dominant": self.mood.dominant_mood,
                },
                "facts_learned": {},
                "topics": [],
                "steps": steps,
                "status": "error",
            }

        self.memory.add_message("assistant", response)
        steps.append({
            "step": 3,
            "action": "response_generation",
            "response_length": len(response),
        })

        # Step 4: Extract facts and topics
        facts_learned = {}
        if ctx.get("extract_facts", True):
            facts_learned = self._extract_facts(task)
            for k, v in facts_learned.items():
                self.memory.add_fact(k, v)

        topics = self._extract_topics(task)
        for t in topics:
            self.memory.add_topic(t)

        steps.append({
            "step": 4,
            "action": "memory_update",
            "facts_learned": len(facts_learned),
            "topics_added": len(topics),
        })

        return {
            "result": response,
            "mood": {
                "sentiment": self.mood.current_sentiment,
                "score": self.mood.sentiment_score,
                "dominant": self.mood.dominant_mood,
            },
            "facts_learned": facts_learned,
            "topics": topics,
            "steps": steps,
            "metadata": {
                "personality": self.personality.name,
                "turn_count": self.mood.turn_count,
                "session_duration": time.time() - (self._session_start or time.time()),
            },
            "status": "success",
        }

    def _generate_greeting(self) -> str:
        """Generate a personalized greeting, optionally using the user's name."""
        user_name = self.memory.user_facts.get("name", "")
        if user_name:
            return f"Hey {user_name}! {self.personality.greeting}"
        return self.personality.greeting

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze the emotional sentiment of user text.

        Uses keyword-based analysis as a fast first pass.
        Can be enhanced with a sentiment model later.
        """
        text_lower = text.lower()

        # Positive indicators
        positive_words = {
            "happy", "great", "awesome", "love", "excited", "wonderful",
            "amazing", "fantastic", "good", "nice", "excellent", "glad",
            "thanks", "thank", "appreciate", "perfect", "brilliant", "yay",
            "haha", "lol", "😊", "😄", "❤️", "🎉", "👍",
        }

        # Negative indicators
        negative_words = {
            "sad", "angry", "frustrated", "upset", "annoyed", "hate",
            "terrible", "awful", "bad", "horrible", "depressed", "anxious",
            "worried", "stressed", "tired", "exhausted", "confused",
            "disappointed", "hurt", "lonely", "scared", "cry", "😢", "😡", "😞",
        }

        pos_count = sum(1 for w in text_lower.split() if w.strip(".,!?") in positive_words)
        neg_count = sum(1 for w in text_lower.split() if w.strip(".,!?") in negative_words)

        total = pos_count + neg_count
        if total == 0:
            return {"sentiment": "neutral", "score": 0.0}

        score = (pos_count - neg_count) / max(total, 1)
        score = max(-1.0, min(1.0, score))

        if score > 0.2:
            sentiment = "positive"
        elif score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {"sentiment": sentiment, "score": score}

    def _extract_facts(self, text: str) -> Dict[str, str]:
        """
        Extract factual information about the user from their message.

        Uses pattern matching for common fact patterns.
        """
        import re
        facts: Dict[str, str] = {}

        # Name patterns
        name_patterns = [
            r"(?:my name is|i'm|i am|call me)\s+([A-Z][a-z]+)",
            r"(?:name'?s)\s+([A-Z][a-z]+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                facts["name"] = match.group(1)
                break

        # Location
        loc_match = re.search(
            r"(?:i live in|i'm from|i am from|based in)\s+(.+?)(?:\.|$|,)",
            text, re.IGNORECASE,
        )
        if loc_match:
            facts["location"] = loc_match.group(1).strip()

        # Occupation
        job_match = re.search(
            r"(?:i work as|i'm a|i am a|my job is|i do)\s+(?:a\s+)?(.+?)(?:\.|$|,)",
            text, re.IGNORECASE,
        )
        if job_match:
            job = job_match.group(1).strip()
            if len(job) < 50:
                facts["occupation"] = job

        # Age
        age_match = re.search(r"(?:i'm|i am)\s+(\d{1,3})\s*(?:years? old)?", text, re.IGNORECASE)
        if age_match:
            age = int(age_match.group(1))
            if 5 <= age <= 120:
                facts["age"] = str(age)

        return facts

    def _extract_topics(self, text: str) -> List[str]:
        """Extract discussion topics from the user's message."""
        import re
        topics = []

        # Look for explicit topic indicators
        topic_patterns = [
            r"(?:about|regarding|concerning|discussing)\s+(.+?)(?:\.|$|,|\?)",
            r"(?:tell me about|what is|what are|how does|how do)\s+(.+?)(?:\.|$|\?)",
            r"(?:interested in|curious about|want to know about)\s+(.+?)(?:\.|$|,|\?)",
        ]

        for pattern in topic_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                topic = match.strip()
                if 3 < len(topic) < 80:
                    topics.append(topic)

        return topics[:3]  # Limit to top 3 topics per message

    def get_personality(self) -> Dict[str, Any]:
        """Get current personality configuration as a dict."""
        p = self.personality
        return {
            "name": p.name,
            "traits": p.traits,
            "communication_style": p.communication_style,
            "interests": p.interests,
            "humor_level": p.humor_level,
            "empathy_level": p.empathy_level,
            "proactivity": p.proactivity,
        }

    def get_mood_summary(self) -> Dict[str, Any]:
        """Get current mood tracking summary."""
        return {
            "current_sentiment": self.mood.current_sentiment,
            "sentiment_score": self.mood.sentiment_score,
            "dominant_mood": self.mood.dominant_mood,
            "turn_count": self.mood.turn_count,
            "recent_history": self.mood.mood_history[-5:],
        }

    def get_memory_summary(self) -> Dict[str, Any]:
        """Get current memory state."""
        return {
            "user_facts": self.memory.user_facts,
            "topics_discussed": self.memory.topics_discussed,
            "message_count": len(self.memory.messages),
        }

    def reset(self) -> None:
        """Reset companion state (conversation, mood, memory)."""
        self.mood = MoodState()
        self.memory = ConversationMemory()
        if self._initialized:
            self.memory.add_message("system", self.personality.to_system_prompt())
        self._session_start = time.time()
        self.logger.info(f"CompanionAgent '{self.personality.name}' reset")
