"""
CogniCompanion — PME Intent Detector (Comprehensive Multilingual Edition)
========================================================================
Determines the domain intent and extracts query entities (names, timeframes, timing).
Supports English and all major Indian languages (Hindi, Marathi, Bengali, Tamil,
Telugu, Kannada, Gujarati, Punjabi, Malayalam, Assamese, Nepali, etc.) in both
native scripts and transliterated roman text.
Deterministic, lightweight, and testable without heavy dependencies.
"""

from __future__ import annotations

import enum
import re
import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.ai.memory_engine.query_understanding import ConversationContext

from app.ai.memory_engine.temporal_parser import parse_temporal_context, TemporalContext


class PMEIntent(str, enum.Enum):
    PERSON_LOOKUP = "person_lookup"
    VISIT_RECALL = "visit_recall"
    DAILY_ROUTINE = "daily_routine"
    MEDICATION_ADHERENCE = "medication_adherence"
    MEDICATION_SCHEDULE = "medication_schedule"
    GAME_PROGRESS = "game_progress"
    COGNITIVE_PROGRESS = "cognitive_progress"
    EVENT_LOOKUP = "event_lookup"
    TEMPORAL_RECALL = "temporal_recall"
    GENERAL_CONVERSATION = "general_conversation"
    UNKNOWN = "unknown"


# Stop-words that should terminate an extracted person name (multilingual)
_NAME_STOP_WORDS = {
    # English
    "here", "there", "yesterday", "today", "tomorrow", "this", "last",
    "coming", "came", "come", "visit", "visited", "visiting",
    "when", "was", "is", "are", "were", "that", "over", "by",
    "who", "whom", "whose", "which", "about", "with", "from",
    "in", "at", "to", "for", "and", "or", "please", "morning",
    "afternoon", "evening", "night", "called", "brought", "did",
    # Hindi / Marathi
    "था", "थी", "थे", "है", "हैं", "होता", "होती", "होते", "आहे", "आहेत", "गेला", "आला",
    "आले", "आली", "के", "की", "का", "बारे", "में", "बद्दल", "सांगा", "बताओ", "कोण", "कौन",
    # Bengali
    "কে", "ছিল", "আছে", "সম্পর্কে", "বলো", "এসেছিল",
    # Tamil / Telugu
    "யார்", "வந்தார்", "இருக்கிறார்", "ఎవరు", "వచ్చారు", "ఉన్నారు",
}

# Pronouns and words that must NEVER be extracted as person names
_PRONOUNS_AND_NON_PERSONS = {
    # English
    "you", "who", "what", "where", "when", "why", "how", "someone", "anyone", "everyone",
    "me", "myself", "yourself", "this", "that", "it", "they", "them", "we", "us", "assistant",
    # Hindi / Marathi
    "आप", "तुम", "तू", "तुम्ही", "आपण", "आपने", "तुझे", "तुझा", "तुझी", "तुझे", "तुमचा", "तुमची",
    "कोण", "कौन", "काय", "क्या", "कोणी", "कोई", "कोणाला", "किसको", "किसे", "मला", "मुझे", "मुझसे",
    "खुद", "स्वयं", "इथे", "यहाँ", "तिथे", "वहाँ", "कल", "आज", "काल", "परसों",
    # Bengali
    "আপনি", "তুমি", "তুই", "কে", "কি", "কাকে", "আমাকে", "তোমাকে", "আপনার", "তোমার", "কাল", "আজ",
    # Tamil
    "நீ", "நீங்கள்", "யார்", "என்ன", "என்னை", "உங்களை", "உன்", "உங்கள்",
    # Telugu
    "మీరు", "నువ్వు", "ఎవరు", "ఏమిటి", "నన్ను", "మిమ్మల్ని", "మీ", "నీ",
    # Kannada
    "ನೀವು", "ನೀನು", "ಯಾರು", "ಏನು", "ನನ್ನನ್ನು", "ನಿಮ್ಮನ್ನು", "ನಿಮ್ಮ",
    # Gujarati
    "તમે", "તું", "કોણ", "શું", "મને", "તમને", "તમારું",
    # Punjabi
    "ਤੁਸੀਂ", "ਤੂੰ", "ਕੌਣ", "ਕੀ", "ਮੈਨੂੰ", "ਤੁਹਾਨੂੰ", "ਤੁਹਾਡਾ",
    # Malayalam
    "നിങ്ങൾ", "നീ", "ആര്", "എന്ത്", "എന്നെ", "നിങ്ങളെ",
    # Assamese
    "আপুনি", "তুমি", "কোন", "কি", "মোক", "আপোনাক",
    # Nepali
    "तपाईं", "तिमी", "को", "के", "मलाई", "तपाईंको",
}


def _clean_extracted_name(raw_name: str) -> str:
    """
    Cleans raw captured text to prevent greedily capturing trailing sentences or verbs.
    Supports English, Devanagari, Bengali, Tamil, Telugu, and other Unicode scripts.
    """
    cleaned = raw_name.strip().strip("?,.!'\"।")
    # Remove leading articles/possessives/honorifics
    cleaned = re.sub(
        r"^(my|the|a|an|about|dr\.|mr\.|mrs\.|ms\.|श्री|श्रीमती|डॉ\.|माझा|माझी|मेरा|मेरी|আমার|আমাদের|ನನ್ನ|నా|என்)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    words = cleaned.split()
    name_words: list[str] = []
    for w in words:
        w_lower = re.sub(r"[^\w]", "", w.lower())
        if w_lower in _NAME_STOP_WORDS or w_lower in _PRONOUNS_AND_NON_PERSONS:
            break
        name_words.append(w.strip("?,.!'\"।"))
        if len(name_words) >= 3:
            break

    result = " ".join(name_words).strip("?,.!'\"।")
    return result


def detect_intent(
    query: str,
    reference_date: date | None = None,
    conversation_context: "ConversationContext | None" = None,
) -> tuple[PMEIntent, dict[str, Any]]:
    """
    Analyzes the user query using heuristic pattern matching and entity extraction across
    English and Indian regional languages.
    Returns (PMEIntent, extracted_entities).

    When conversation_context is provided, inherits last_intent and last_referenced_date
    from context if the current query produces UNKNOWN or an empty temporal match.
    This enables bare follow-up queries (rewritten by QU) to correctly route to PME.
    """
    q = query.lower().strip()
    entities: dict[str, Any] = {}

    # Parse central temporal context
    temporal = parse_temporal_context(query, reference_date=reference_date)
    entities["temporal"] = temporal
    timeframe = temporal.timeframe
    timing = temporal.timing
    entities["timeframe"] = timeframe
    entities["timing"] = timing

    # ── 0. General Conversational Queries, Greetings & Emotions (EARLY CHECK) ──
    # Evaluated early so queries like "Who are you?", "आप कौन हैं?", "तुम्ही कोण आहात?",
    # "কেমন আছেন?", or expressions of loneliness/sadness are handled conversationally.
    assistant_queries = [
        # Who are you? / What is your name?
        "who are you", "what is your name", "what are you", "who made you", "what can you do", "help me",
        "tell me about yourself", "can you talk", "talk to me", "speak with me",
        "आप कौन हैं", "आप कौन हो", "तुम कौन हो", "तू कौन है", "आपका नाम क्या है", "तुम क्या कर सकते हो",
        "मेरी मदद करो", "बात करो", "मुझसे बात करो", "कुछ बताओ",
        "तुम्ही कोण आहात", "तू कोण आहेस", "तुमचं नाव काय आहे", "तुम्ही काय करू शकता", "माझ्याशी बोला",
        "मदत करा", "काहीतरी बोला", "कशी आहेस", "कसे आहात",
        "আপনি কে", "আপনার নাম কি", "আপনি কি করতে পারেন", "আমার সাথে কথা বলুন", "আমাকে সাহায্য করুন",
        "நீ யார்", "நீங்கள் யார்", "உங்கள் பெயர் என்ன", "என்னிடம் பேசுங்கள்", "உதவி செய்",
        "మీరు ఎవరు", "మీ పేరు ఏమిటి", "నాతో మాట్లాడండి", "సహాయం చేయండి",
        "ನೀವು ಯಾರು", "ನಿಮ್ಮ ಹೆಸರೇನು", "ನನ್ನೊಂದಿಗೆ ಮಾತನಾಡಿ", "ಸಹಾಯ ಮಾಡಿ",
        "તમે કોણ છો", "તમારું નામ શું છે", "મારી સાથે વાત કરો", "મને મદદ કરો",
        "ਤੁਸੀਂ ਕੌਣ ਹੋ", "ਤੁਹਾਡਾ ਨਾਮ ਕੀ ਹੈ", "ਮੇਰੇ ਨਾਲ ਗੱਲ ਕਰੋ", "ਮੇਰੀ ਮਦਦ ਕਰੋ",
        "നിങ്ങൾ ആരാണ്", "നിങ്ങളുടെ പേരെന്താണ്", "എന്നോട് സംസാരിക്കൂ",
        "আপুনি কোন", "আপোনাৰ নাম কি", "মোৰ লগত কথা কওক",
        "तपाईं को हुनुहुन्छ", "तपाईंको नाम के हो", "मलाई सहयोग गर्नुहोस्",
        # How are you?
        "how are you", "how do you do", "how is everything", "how are you doing",
        "आप कैसे हैं", "आप कैसी हैं", "कैसे हो", "केमन आछो", "কেমন আছেন",
        "எப்படி இருக்கிறீர்கள்", "ఎలా ఉన్నారు", "ಹೇಗಿದ್ದೀರಾ", "કેમ છો", "ਕਿਵੇਂ ਹੋ", "സുഖമാണോ", "খবৰ কি", "कस्तो छ",
        # Emotional / Companion comfort
        "feeling lonely", "i am lonely", "feel alone", "i feel sad", "i am scared", "i feel anxious", "bored",
        "अकेलापन", "अकेला लग रहा", "उदास", "डर लग रहा", "एकटं वाटतंय", "भीती वाटतेय", "মন ভালো নেই", "একাকী",
        "தனிமையாக", "ஒంటరిగా", "ಬೇಸರ", "એકલા",
        # Greetings & pleasantries
        "hello", "namaste", "hi", "hey", "good morning", "good evening", "good afternoon", "good night", "thank you", "thanks",
        "नमस्ते", "नमस्कार", "सुप्रभात", "शुभ संध्या", "शुभ रात्री", "धन्यवाद", "आभार",
        "নমস্কার", "সুপ্রভাত", "ধন্যবাদ", "வணக்கம்", "காலை வணக்கம்", "நன்றி",
        "నమస్కారం", "శుభోదయం", "ధన్యవాదాలు", "ನಮಸ್ಕಾರ", "ಶುಭೋದಯ", "ಧನ್ಯವಾದ",
        "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ", "ખમ્મા ഘણી", "kem cho", "vanakkam", "namaskaram",
        # Northeast language greetings
        "chibai", "khublei", "salam", "kaham", "dakchakaniko", "cognicompanion",
        # Jokes / Stories / Light conversation
        "tell me a joke", "tell me a story", "चुटकुला", "कहानी", "गप्पा", "गोष्ट", "গল্প", "கதை", "కథ"
    ]
    if any(k in q for k in assistant_queries):
        return PMEIntent.GENERAL_CONVERSATION, entities

    # ── 1. Broad Temporal Recall (Daily Activity Summary) ─────────────────────
    temporal_recall_patterns = [
        "what happened", "what did i do", "tell me about yesterday", "tell me about today",
        "how was my day", "what went on", "recap my day", "anything happen yesterday", "anything happen today",
        "summary of yesterday", "summary of today",
        # Hindi / Marathi
        "कल क्या हुआ", "आज क्या हुआ", "काल काय झालं", "आज काय झालं", "दिवस कसा होता", "दिन कैसा रहा",
        "kal kya hua", "aaj kya hua", "kaal kay jhala"
    ]
    is_broad_temporal = any(p in q for p in temporal_recall_patterns)
    has_specific_domain = any(k in q for k in [
        "medicine", "pill", "tablet", "dose", "medication", "game", "games", "appointment",
        "routine", "who is", "who was", "who visited", "score", "reaction",
        "दवा", "औषध", "गोली", "खेल", "खेळ", "डॉक्टर", "भेट"
    ])
    if is_broad_temporal and not has_specific_domain:
        entities["timeframe"] = timeframe or "yesterday"
        entities["subject"] = "patient"
        entities["action"] = "daily_activity"
        return PMEIntent.TEMPORAL_RECALL, entities

    # ── 2. Medication Adherence vs Medication Schedule Intent ──────────────────
    med_keywords = [
        # English
        "medicine", "pill", "tablet", "dose", "medication", "meds", "donepezil", "memantine",
        "aspirin", "vitamin", "prescriptions", "drugs",
        # Hindi / Marathi
        "दवा", "दवाई", "दवाइयां", "औषध", "औषधे", "गोली", "गोळ्या", "डोनेपेजिल", "मेमेंटाइन",
        # Bengali
        "ওষুধ", "ঔষধ", "ট্যাবলেট",
        # Tamil
        "மருந்து", "மாத்திரை",
        # Telugu
        "మందు", "మందులు", "మాత్రలు",
        # Kannada
        "ಔಷಧ", "ಮಾತ್ರೆ",
        # Gujarati
        "દવા", "ગોળી",
        # Punjabi
        "ਦਵਾਈ", "ਗੋਲੀ",
        # Malayalam
        "മരുന്ന്", "ഗുളിക",
        # Assamese / Bengali
        "দৰব", "औषधि", "বড়ি", "ঔষধ",
        # Northeast languages (Mizo, Khasi, Garo, Kokborok, Nagamese)
        "damdawi", "dawai", "sam", "bithiko", "botol sam",
        # Transliterations
        "dawa", "davai", "aushadh", "goli", "marunthu", "mandulu"
    ]
    is_med_query = any(k in q for k in med_keywords)

    if is_med_query:
        # Extract target medication name if mentioned
        for kw in ["donepezil", "memantine", "aspirin", "vitamin b12", "amlodipine", "metformin", "डोनेपेजिल", "मेमेंटाइन"]:
            if kw in q:
                entities["target_medication"] = kw.title()
                entities["target_entity"] = kw.title()
                entities["target_type"] = "medication"
                break

        adherence_cues = [
            # English
            "did i take", "have i taken", "did i have", "taken my", "already taken", "forgot to take",
            # Hindi / Marathi
            "क्या मैंने ली", "ली क्या", "खा ली क्या", "घेतली का", "घेतलं का", "मी औषध घेतले का", "मी गोळी घेतली का",
            # Bengali / Assamese
            "আমি কি নিয়েছি", "খেয়েছি কি", "খালোনে", "খালো নে", "খাইছো নে", "ললোনে", "ললো নে",
            # Northeast languages (Mizo, Khasi)
            "ei tawh em", "ka ei tawh em", "dawai la shim",
            # Tamil / Telugu
            "எடுத்துக்கொண்டேனா", "వేసుకున్నానా",
            # Transliterations
            "kya maine li", "ghetli ka", "khali ka", "leli kya"
        ]
        is_adherence = any(c in q for c in adherence_cues)

        if is_adherence:
            entities["timing"] = timing
            entities["timeframe"] = timeframe or "today"
            return PMEIntent.MEDICATION_ADHERENCE, entities
        elif any(k in q for k in ["when should i take", "what time", "schedule", "routine", "कधी घ्यायची", "कब लेनी है"]):
            entities["timing"] = timing
            return PMEIntent.MEDICATION_SCHEDULE, entities
        elif "take" in q or "लेनी" in q or "घ्यायची" in q:
            entities["timing"] = timing
            entities["timeframe"] = timeframe or "today"
            return PMEIntent.MEDICATION_ADHERENCE, entities
        else:
            entities["timing"] = timing
            return PMEIntent.MEDICATION_SCHEDULE, entities

    # ── 3. Game Progress Intent ───────────────────────────────────────────────
    game_names = ["memory match", "pattern recall", "sequence recall", "picture recall", "object recall", "sudoku", "category sort", "trail path", "word category"]
    has_game_name = any(gn in q for gn in game_names)

    game_keywords = [
        "game", "games", "score", "scores", "accuracy", "reaction time", "performance",
        "खेल", "खेळ", "खेला", "விளையாட்டு", "ఆట", "ಅಂಕ", "ગુણ", "ਪੁਆਇੰਟ"
    ]
    if has_game_name or any(k in q for k in game_keywords):
        if not ("cpi" in q or "getting better" in q or "improving overall" in q or "सुधार" in q):
            matched_g = next((gn for gn in game_names if gn in q), None)
            if matched_g:
                entities["game_name"] = matched_g.title()
                entities["target_entity"] = matched_g.title()
                entities["target_type"] = "game"
            return PMEIntent.GAME_PROGRESS, entities

    # ── 4. Cognitive Progress / CPI Trend Intent ──────────────────────────────
    cognitive_keywords = [
        "cpi", "cognitive", "getting better", "improving", "improvement",
        "progress trend", "overall progress", "daily statistics", "daily stats",
        "memory performance trend", "am i improving", "how am i doing",
        # Multilingual
        "सुधार", "प्रगती", "सुधर रहा", "उन्नति", "முன்னேற்றம்", "పురోగతి"
    ]
    if any(k in q for k in cognitive_keywords) or (("progress" in q or "trend" in q) and "game" not in q):
        return PMEIntent.COGNITIVE_PROGRESS, entities

    # ── 5. Event / Calendar Lookup Intent ─────────────────────────────────────
    event_keywords = [
        "appointment", "doctor appointment", "clinic visit", "outing",
        "calendar event", "events scheduled", "upcoming event", "any events",
        # Multilingual
        "अपॉइंटमेंट", "दवाखाना", "डॉक्टर", "कार्यक्रम", "ভেটি", "நேரம்", "సమావేశం"
    ]
    if any(k in q for k in event_keywords):
        return PMEIntent.EVENT_LOOKUP, entities

    # ── 6. Visit / Social Recall Intent ───────────────────────────────────────
    m_out = re.search(r"did (?:i|we) visit ([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)", query, re.IGNORECASE)
    if m_out:
        target = _clean_extracted_name(m_out.group(1))
        entities["target_name"] = target
        entities["target_entity"] = target
        entities["target_type"] = "location_or_person"
        entities["direction"] = "outgoing"
        entities["subject"] = "patient"
        entities["action"] = "visit"
        entities["timeframe"] = timeframe or "recent"
        return PMEIntent.VISIT_RECALL, entities

    m_in = re.search(r"(?:was|did)\s+([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)\s+(?:here|visit|come)", query, re.IGNORECASE)
    if m_in:
        target = _clean_extracted_name(m_in.group(1))
        if target and target.lower() not in ["i", "we", "someone", "anyone"]:
            entities["target_name"] = target
            entities["target_entity"] = target
            entities["target_type"] = "person"
            entities["direction"] = "incoming"
            entities["subject"] = target
            entities["action"] = "visit"
            entities["timeframe"] = timeframe or "recent"
            return PMEIntent.VISIT_RECALL, entities

    # Indic visit patterns: e.g. "राहुल आया था क्या", "राहुल भेटायला आला होता का", "কে দেখা করতে এসেছিল"
    indic_visit_match = re.search(r"([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)\s+(?:आया था|आए थे|आला होता|आले होते|এসেছিল|வந்தார்|వచ్చారు)", query, re.IGNORECASE)
    if indic_visit_match:
        target = _clean_extracted_name(indic_visit_match.group(1))
        if target and target.lower() not in ["कल", "आज", "काल", "कोण", "कौन", "কে"]:
            entities["target_name"] = target
            entities["target_entity"] = target
            entities["target_type"] = "person"
            entities["direction"] = "incoming"
            entities["subject"] = target
            entities["action"] = "visit"
            entities["timeframe"] = timeframe or "recent"
            return PMEIntent.VISIT_RECALL, entities

    visit_keywords = [
        "visit", "visited", "visiting", "visitor", "visitors",
        "came over", "who was here", "who came", "who dropped by", "come over",
        "anyone come", "someone come",
        # Multilingual visit words
        "कौन आया", "कौन आया था", "कोण आलं", "कोण आले होते", "भेट दिली", "भेटायला",
        "কে এসেছিল", "யார் வந்தார்", "ఎవరు వచ్చారు", "యారు బందరు",
        "আহিছিল", "আহিলে", "দেখা কৰা",
        # Northeast languages (Mizo, Khasi, Garo, Kokborok, Nagamese)
        "tlawh", "wan jngoh", "re·ba", "grongna", "lok paise",
        "kaun aaya", "kon aala", "ke esechhilo"
    ]
    if any(k in q for k in visit_keywords):
        entities["timeframe"] = timeframe or "recent"
        entities["direction"] = "incoming" if any(w in q for w in ["who visited me", "visited me", "came over", "who came", "कौन आया", "कोण आलं"]) else "neutral"
        entities["action"] = "visit"
        return PMEIntent.VISIT_RECALL, entities

    # ── 7. Person / Relationship Lookup Intent ────────────────────────────────
    person_patterns = [
        # English
        r"what do you remember about ([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)",
        r"what can you tell me about ([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)",
        r"tell me about ([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)",
        r"who is ([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)",
        r"do i know ([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)",
        r"what is my relationship with ([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)",
        r"relationship with ([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)",
        r"do you know ([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)",
        # Hindi / Marathi: "राहुल कौन है", "राहुल कोण आहे", "प्रिया बद्दल सांगा", "राहुल के बारे में बताओ"
        r"([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)\s+(?:कौन है|कौन था|कोण आहे|कोण होता|बद्दल सांगा|के बारे में बताओ)",
        r"(?:कौन है|कोण आहे|के बारे में बताओ|बद्दल सांगा)\s+([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)",
        # Bengali: "রাহুল কে", "রাহুল সম্পর্কে বলো"
        r"([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)\s+(?:কে|সম্পর্কে বলো)",
        # Tamil / Telugu
        r"([^\s?,.!।;:\d]+(?:\s+[^\s?,.!।;:\d]+)*)\s+(?:யார்|பற்றி சொல்லு|ఎవరు|గురించి చెప్పు)",
        # Transliterations: "rahul kaun hai", "rahul kon aahe", "rahul ke"
        r"([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+(?:kaun hai|kon aahe|ke aachhe|yaar)",
    ]
    non_person_keywords = {
        "mango", "mangoes", "trip", "vacation", "time", "story", "stories",
        "wedding", "festival", "holiday", "childhood", "college", "school", "house",
        "garden", "photo", "photos", "picture", "pictures", "food", "recipe",
        "picked", "remember", "yesterday", "today", "कल", "आज", "काल"
    }
    for pattern in person_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            raw_name = match.group(1)
            raw_lower = raw_name.lower().strip()
            if any(npk in raw_lower.split() for npk in non_person_keywords) or raw_lower.startswith("the ") or " we " in raw_lower:
                continue
            cleaned_name = _clean_extracted_name(raw_name)
            if cleaned_name and len(cleaned_name) > 1:
                cleaned_lower = cleaned_name.lower()
                if cleaned_lower in _PRONOUNS_AND_NON_PERSONS:
                    return PMEIntent.GENERAL_CONVERSATION, entities
                if any(npk in cleaned_lower.split() for npk in non_person_keywords):
                    continue
                entities["target_name"] = cleaned_name
                entities["target_entity"] = cleaned_name
                entities["target_type"] = "person"
                entities["subject"] = cleaned_name
                return PMEIntent.PERSON_LOOKUP, entities

    # ── 8. Daily Routine Intent ───────────────────────────────────────────────
    routine_keywords = [
        "schedule", "routine", "what should i do", "what do i do", "what is on my plan",
        "what do i have today", "what is next", "what's next", "daily plan", "my plan",
        "what am i doing", "what is planned",
        # Multilingual
        "दिनचर्या", "वेळापत्रक", "आज क्या करना है", "आगे क्या है", "शेड्यूल",
        "आज काय करायचं", "पुढे काय आहे", "রুটিন", "পরিকল্পনা", "திட்டம்", "షెడ్యూల్",
        "dincharya", "velapatrak", "aaj kya karna hai", "kya plan hai"
    ]
    is_routine_query = any(k in q for k in routine_keywords) or (
        ("what" in q or "how" in q or "क्या" in q or "काय" in q) and ("schedule" in q or "routine" in q or "plan" in q or "दिनचर्या" in q or "वेळापत्रक" in q)
    )

    if is_routine_query:
        entities["time_of_day"] = timing or "today"
        entities["target_date"] = timeframe or "today"
        return PMEIntent.DAILY_ROUTINE, entities

    # Fallback short query (<= 2 words) e.g. "hey", "hello", "हाँ", "सुनो"
    if len(q.split()) <= 2:
        # If context has a known intent, inherit it rather than treating this as a greeting
        if conversation_context and conversation_context.last_intent not in (
            None, PMEIntent.GENERAL_CONVERSATION, PMEIntent.UNKNOWN
        ):
            # Inherit temporal reference from context if not already set
            if not entities.get("temporal") or not entities["temporal"].is_bounded:
                if conversation_context.last_referenced_date:
                    inherited = parse_temporal_context(
                        str(conversation_context.last_referenced_date),
                        reference_date=reference_date,
                    )
                    entities["temporal"] = inherited
                    entities["timeframe"] = inherited.timeframe
            return conversation_context.last_intent, entities
        return PMEIntent.GENERAL_CONVERSATION, entities

    # Final fallback — inherit prior intent from context if query has no recognizable pattern
    if conversation_context and conversation_context.last_intent not in (
        None, PMEIntent.GENERAL_CONVERSATION, PMEIntent.UNKNOWN
    ):
        # Only inherit if no strong UNKNOWN signal — we trust QU to have rewritten it
        if not any(k in q for k in ["what", "who", "where", "when", "help", "tell", "show"]):
            return conversation_context.last_intent, entities

    return PMEIntent.UNKNOWN, entities
