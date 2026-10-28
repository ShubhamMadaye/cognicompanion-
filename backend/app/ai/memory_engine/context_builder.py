"""
CogniCompanion — PME Context Builder
====================================
Formats grounded database facts into compassionate, structured prompts for the LLM
and deterministic template fallbacks.

CRITICAL SAFETY RULES:
  - NEVER infer absence from missing data.
    * NO visit record -> "I couldn't find a visit recorded for yesterday."
      (NEVER: "You had a peaceful time at home and no visitors came.")
    * NO medication record -> "I couldn't find any medications recorded for that time."
    * NO game session record -> "I couldn't find any recorded game sessions for yesterday."
      (NEVER: "You didn't play any games.")
    * NO routine record -> "I couldn't find any routines or scheduled events recorded for this morning."
  - NEVER let LLM guess or hallucinate unrecorded personal details or medical facts.
  - CPI DISCLAIMER: Always frame CPI strictly as an assistive progress indicator, never a medical diagnosis.
"""

from typing import Any
from app.ai.memory_engine.intent_detector import PMEIntent


class ContextBuilder:
    @staticmethod
    def build_context(
        intent: PMEIntent,
        retrieved_data: dict[str, Any],
        patient_name: str = "Shanti ji",
        language_code: str = "en",
    ) -> dict[str, Any]:
        """
        Builds grounded context facts, system instructions, and deterministic fallback responses.
        """
        deterministic_reply = ""
        facts_summary: list[str] = []

        unified_memories = retrieved_data.get("unified_memories", [])

        # ── 1. PERSON LOOKUP / NARRATIVE MEMORY ───────────────────────────────
        if intent == PMEIntent.PERSON_LOOKUP:
            matched_person = retrieved_data.get("matched_person")
            query_name = retrieved_data.get("query_name") or "this person"
            exact_match = retrieved_data.get("exact_match", False)

            if matched_person and exact_match:
                rel = f"your {matched_person.relationship}" if matched_person.relationship else "a beloved person in your life"
                desc = f" {matched_person.description}" if matched_person.description else ""

                memory_notes = ""
                if unified_memories:
                    top_m = unified_memories[0]["memory"]
                    m_date = top_m.event_date.strftime("%B %d, %Y")
                    memory_notes = f" One memory with them: {top_m.title} from {m_date}."
                    facts_summary.append(f"Memory with {matched_person.name}: {top_m.title} ({m_date}) - {top_m.description or ''}")

                deterministic_reply = f"{matched_person.name} is {rel}.{desc}{memory_notes}"
                facts_summary.append(
                    f"Person: {matched_person.name}, Relationship: {matched_person.relationship or 'None'}, Notes: {matched_person.description or 'None'}"
                )
            elif unified_memories:
                top_match = unified_memories[0]["memory"]
                p_names = ", ".join(p.name for p in top_match.people) if top_match.people else ""
                with_str = f" with {p_names}" if p_names else ""
                date_str = top_match.event_date.strftime("%B %d, %Y")
                desc = f" {top_match.description}" if top_match.description else ""
                deterministic_reply = f"I found this memory about {query_name}: {top_match.title} from {date_str}{with_str}.{desc}"
                facts_summary.append(f"Semantic Memory: {top_match.title} ({date_str}) - {top_match.description or ''}")
            else:
                deterministic_reply = f"I couldn't find any information recorded for '{query_name}'. Your caregiver can add more details to your photo album."
                facts_summary.append(f"No person or memory records found for '{query_name}'.")

        # ── 2. VISIT RECALL ────────────────────────────────────────────────────
        elif intent == PMEIntent.VISIT_RECALL:
            memories = retrieved_data.get("memories", [])
            events = retrieved_data.get("timeline_events", [])
            timeframe = retrieved_data.get("timeframe", "recently")
            timeframe_str = "yesterday" if timeframe == "yesterday" else ("today" if timeframe == "today" else "recently")
            target_name = retrieved_data.get("target_name")
            direction = retrieved_data.get("direction")

            if memories:
                latest = memories[0]
                people_names = ", ".join(p.name for p in latest.people) if latest.people else "your family"
                date_str = latest.event_date.strftime("%A, %B %d")
                desc = f" {latest.description}" if latest.description else ""

                if timeframe == "yesterday":
                    deterministic_reply = f"{people_names} visited you yesterday. {latest.title}.{desc}"
                elif timeframe == "today":
                    deterministic_reply = f"{people_names} visited you today. {latest.title}.{desc}"
                else:
                    deterministic_reply = f"{people_names} visited you on {date_str}. {latest.title}.{desc}"

                facts_summary.append(f"Visit: {latest.title} on {date_str} with {people_names}. Details: {latest.description or 'None'}")
            elif events:
                latest_ev = events[0]
                time_str = latest_ev.start_time.strftime("%I:%M %p").lstrip("0")
                deterministic_reply = f"You had a visit recorded for {latest_ev.title} {timeframe_str} at {time_str}."
                facts_summary.append(f"Event: {latest_ev.title} at {time_str}")
            elif unified_memories:
                top_match = unified_memories[0]["memory"]
                p_names = ", ".join(p.name for p in top_match.people) if top_match.people else "your family"
                date_str = top_match.event_date.strftime("%B %d, %Y")
                desc = f" {top_match.description}" if top_match.description else ""
                deterministic_reply = f"I found this past visit memory: {top_match.title} on {date_str} with {p_names}.{desc}"
                facts_summary.append(f"Semantic Visit: {top_match.title} on {date_str} with {p_names}")
            else:
                if target_name and direction == "outgoing":
                    deterministic_reply = f"I couldn't find a record showing that you visited {target_name} {timeframe_str}."
                    facts_summary.append(f"No records found showing patient visited {target_name} {timeframe_str}.")
                elif target_name:
                    deterministic_reply = f"I couldn't find a record of {target_name} visiting you {timeframe_str}."
                    facts_summary.append(f"No visit records found for {target_name} {timeframe_str}.")
                else:
                    deterministic_reply = f"I couldn't find a visit recorded for {timeframe_str}."
                    facts_summary.append(f"No visit records found for {timeframe_str}.")

        # ── 3. MEDICATION ADHERENCE ────────────────────────────────────────────
        elif intent == PMEIntent.MEDICATION_ADHERENCE:
            items = retrieved_data.get("items", [])
            timing_hint = retrieved_data.get("timing_hint") or "today"
            target_med = retrieved_data.get("target_medication")
            has_meds = retrieved_data.get("has_medications", False)
            all_taken = retrieved_data.get("all_taken", False)
            any_taken = retrieved_data.get("any_taken", False)

            if not has_meds:
                if target_med:
                    deterministic_reply = (
                        f"I couldn't find any record for {target_med} scheduled for {timing_hint}. "
                        "Please check with your caregiver before taking any medication."
                    )
                    facts_summary.append(f"No active record found for {target_med} ({timing_hint}).")
                else:
                    deterministic_reply = f"I couldn't find any {timing_hint} medication scheduled in your records."
                    facts_summary.append(f"No medications scheduled for {timing_hint}.")
            elif all_taken:
                med_names = ", ".join(it["medication"].name for it in items)
                deterministic_reply = f"Yes, your {timing_hint} medication ({med_names}) is recorded as taken. You have already taken it and are all set!"
                facts_summary.append(f"All {timing_hint} medications marked as taken ({med_names}).")
            elif any_taken:
                taken = [it["medication"].name for it in items if it["is_taken"]]
                pending = [it["medication"].name for it in items if not it["is_taken"]]
                deterministic_reply = (
                    f"You have taken {', '.join(taken)}, but your {', '.join(pending)} is still pending for this {timing_hint}."
                )
                facts_summary.append(f"Partially taken: {', '.join(taken)} taken. {', '.join(pending)} pending.")
            else:
                med_names = ", ".join(it["medication"].name for it in items)
                deterministic_reply = (
                    f"I don't have a record of your {timing_hint} medication ({med_names}) being taken yet today. "
                    "Please check with your caregiver before taking any dose."
                )
                facts_summary.append(f"{timing_hint} medications ({med_names}) are pending / not marked as taken.")

        # ── 4. MEDICATION SCHEDULE (NEW) ──────────────────────────────────────
        elif intent == PMEIntent.MEDICATION_SCHEDULE:
            medications = retrieved_data.get("medications", [])
            timing_hint = retrieved_data.get("timing_hint")
            has_meds = retrieved_data.get("has_medications", False)

            if has_meds:
                med_lines = []
                for m in medications:
                    timing_str = m.timing.value if hasattr(m.timing, "value") else str(m.timing)
                    med_lines.append(f"{m.name} ({m.dosage or 'standard dose'}, {timing_str})")
                    facts_summary.append(f"Medication: {m.name}, Dosage: {m.dosage or 'None'}, Timing: {timing_str}")

                slot_str = f" for {timing_hint}" if timing_hint else ""
                deterministic_reply = f"Your recorded medication schedule{slot_str} includes: {'; '.join(med_lines)}."
            else:
                slot_str = f" for {timing_hint}" if timing_hint else ""
                deterministic_reply = f"I couldn't find any medications recorded in your schedule{slot_str}."
                facts_summary.append(f"No active medications found in schedule{slot_str}.")

        # ── 5. GAME PROGRESS (NEW) ────────────────────────────────────────────
        elif intent == PMEIntent.GAME_PROGRESS:
            sessions = retrieved_data.get("sessions", [])
            has_sessions = retrieved_data.get("has_sessions", False)
            temporal = retrieved_data.get("temporal")
            timeframe_str = temporal.timeframe if (temporal and temporal.timeframe != "all") else "recently"

            if has_sessions:
                count = len(sessions)
                avg_acc = retrieved_data.get("avg_accuracy")
                avg_rt = retrieved_data.get("avg_reaction_time_ms")

                session_details = []
                for s in sessions[:3]:
                    g_name = s.game.name if (s.game and hasattr(s.game, "name")) else "Cognitive Game"
                    acc_pct = f"{int(s.accuracy * 100)}%" if s.accuracy is not None else "N/A"
                    rt_s = f"{round(s.reaction_time_ms / 1000, 1)}s" if s.reaction_time_ms else "N/A"
                    session_details.append(f"{g_name} (accuracy: {acc_pct}, reaction: {rt_s})")
                    facts_summary.append(f"Game Session: {g_name}, Accuracy: {acc_pct}, Reaction: {rt_s}, Score: {s.score or 0}")

                acc_summary = f" with an average accuracy of {int(avg_acc * 100)}%" if avg_acc is not None else ""
                rt_summary = f" and reaction time of {round(avg_rt / 1000, 1)} seconds" if avg_rt is not None else ""

                deterministic_reply = (
                    f"You completed {count} cognitive game session{'s' if count > 1 else ''} {timeframe_str}{acc_summary}{rt_summary}. "
                    f"Sessions: {'; '.join(session_details)}."
                )
            else:
                # SAFETY: Never say "You didn't play any games"
                game_name = retrieved_data.get("game_name")
                if game_name:
                    deterministic_reply = f"I couldn't find any recorded sessions for {game_name} {timeframe_str}."
                    facts_summary.append(f"No game sessions recorded for {game_name} {timeframe_str}.")
                else:
                    deterministic_reply = f"I couldn't find any recorded game sessions for {timeframe_str}."
                    facts_summary.append(f"No game sessions recorded for {timeframe_str}.")

        # ── 6. COGNITIVE PROGRESS & CPI TREND (NEW) ───────────────────────────
        elif intent == PMEIntent.COGNITIVE_PROGRESS:
            metrics = retrieved_data.get("cognitive_metrics", [])
            daily_stats = retrieved_data.get("daily_stats", [])
            has_data = retrieved_data.get("has_data", False)
            trend = retrieved_data.get("cpi_trend", "stable")
            latest_cpi = retrieved_data.get("latest_cpi")
            cpi_delta = retrieved_data.get("cpi_delta")

            if has_data and latest_cpi is not None:
                delta_str = f" ({cpi_delta:+.1f} vs previous)" if cpi_delta is not None else ""
                deterministic_reply = (
                    f"Your recorded Cognitive Performance Index (CPI) is currently {int(latest_cpi)}, "
                    f"showing a {trend} trend{delta_str} across recent sessions. "
                    "Please note that CPI is an assistive progress indicator, not a medical diagnosis."
                )
                facts_summary.append(
                    f"Cognitive Index: {int(latest_cpi)}, Trend: {trend}, Delta: {cpi_delta or 0:+.1f}. "
                    "CPI is an assistive performance indicator, not a medical diagnosis."
                )
            elif has_data and daily_stats:
                ds = daily_stats[0]
                deterministic_reply = (
                    f"In your recent daily activity, you completed {ds.games_completed} out of {ds.games_total} cognitive games "
                    f"and took {ds.medications_taken} of your scheduled medications. Keep up the wonderful routine!"
                )
                facts_summary.append(f"Daily activity: {ds.games_completed}/{ds.games_total} games, {ds.medications_taken}/{ds.medications_scheduled} medications.")
            else:
                deterministic_reply = "I couldn't find any cognitive progress statistics recorded yet."
                facts_summary.append("No cognitive metrics or daily statistics found.")

        # ── 7. EVENT / CALENDAR LOOKUP (NEW) ──────────────────────────────────
        elif intent == PMEIntent.EVENT_LOOKUP:
            events = retrieved_data.get("events", [])
            has_events = retrieved_data.get("has_events", False)

            if has_events:
                event_items = []
                for ev in events[:4]:
                    t_str = ev.start_time.strftime("%A, %b %d at %I:%M %p")
                    loc_str = f" ({ev.location})" if ev.location else ""
                    event_items.append(f"{ev.title} on {t_str}{loc_str}")
                    facts_summary.append(f"Event: {ev.title} on {t_str}{loc_str}")

                deterministic_reply = f"Here are your upcoming scheduled events: {'; '.join(event_items)}."
            else:
                deterministic_reply = "I couldn't find any upcoming appointments or events recorded in your calendar."
                facts_summary.append("No upcoming events found.")

        # ── 8. DAILY ROUTINE ───────────────────────────────────────────────────
        elif intent == PMEIntent.DAILY_ROUTINE:
            routines = retrieved_data.get("routines", [])
            events = retrieved_data.get("events", [])
            time_of_day = retrieved_data.get("time_of_day") or "day"

            items_list = []
            for r in routines:
                t_str = r.scheduled_time.strftime("%I:%M %p").lstrip("0")
                items_list.append(f"{r.title} at {t_str}")
                facts_summary.append(f"Routine: {r.title} at {t_str} ({r.category.value if hasattr(r.category, 'value') else r.category})")

            for ev in events:
                t_str = ev.start_time.strftime("%I:%M %p").lstrip("0")
                items_list.append(f"{ev.title} at {t_str}")
                facts_summary.append(f"Scheduled Event: {ev.title} at {t_str}")

            if items_list:
                plan_str = ", ".join(items_list)
                deterministic_reply = f"For this {time_of_day}, your schedule has: {plan_str}."
            else:
                # SAFETY: Never infer that patient had a relaxed time or nothing happened
                deterministic_reply = f"I couldn't find any routines or scheduled events recorded for this {time_of_day}."
                facts_summary.append(f"No routines or events found for this {time_of_day}.")

        # ── 9. BROAD TEMPORAL RECALL (What happened yesterday?) ─────────────────
        elif intent == PMEIntent.TEMPORAL_RECALL:
            memories = retrieved_data.get("memories", [])
            events = retrieved_data.get("events", [])
            sessions = retrieved_data.get("game_sessions", [])
            med_logs = retrieved_data.get("medication_logs", [])
            has_data = retrieved_data.get("has_data", False)
            temporal = retrieved_data.get("temporal")
            timeframe_str = temporal.timeframe if (temporal and temporal.timeframe != "all") else "yesterday"

            if has_data:
                summary_parts = []
                if memories:
                    m = memories[0]
                    p_names = ", ".join(p.name for p in m.people) if m.people else "family"
                    summary_parts.append(f"{p_names} visited you ({m.title})")
                    facts_summary.append(f"Visit: {m.title} with {p_names}")
                if events:
                    ev = events[0]
                    summary_parts.append(f"you had an event: {ev.title}")
                    facts_summary.append(f"Event: {ev.title}")
                if sessions:
                    g_count = len(sessions)
                    summary_parts.append(f"you completed {g_count} cognitive game session{'s' if g_count > 1 else ''}")
                    facts_summary.append(f"Game Sessions: {g_count} played")
                if med_logs:
                    taken_count = sum(1 for log in med_logs if log.taken)
                    summary_parts.append(f"you took {taken_count} scheduled medication{'s' if taken_count > 1 else ''}")
                    facts_summary.append(f"Medications Taken: {taken_count}")

                recap_str = "; ".join(summary_parts)
                deterministic_reply = f"Looking at your records for {timeframe_str}: {recap_str}."
            else:
                deterministic_reply = f"I couldn't find any activities, visits, or medication logs recorded for {timeframe_str}."
                facts_summary.append(f"No daily activity records found for {timeframe_str}.")

        # ── 9. GENERAL COMPANION CONVERSATION ──────────────────────────────────
        lang_names = {
            "hi": "Hindi (हिन्दी)",
            "mr": "Marathi (मराठी)",
            "bn": "Bengali (বাংলা)",
            "ta": "Tamil (தமிழ்)",
            "te": "Telugu (తెలుగు)",
            "kn": "Kannada (ಕನ್ನಡ)",
            "gu": "Gujarati (ગુજરાતી)",
            "pa": "Punjabi (ਪੰਜਾਬੀ)",
            "ml": "Malayalam (മലയാളം)",
            "as": "Assamese (অসমীয়া)",
            "ne": "Nepali (नेपाली)",
            "brx": "Bodo (बड़ो)",
            "mni": "Meitei / Manipuri (ꯃৈতৈ)",
            "lus": "Mizo (Mizo ṭawng)",
            "kha": "Khasi (Ka Ktien Khasi)",
            "grt": "Garo (A·chik)",
            "trp": "Kokborok (Kokborok)",
            "nag": "Naga / Nagamese (Nagamese)",
            "njz": "Nyishi (Nyishi)",
            "pbv": "Pnar (Pnar)",
        }
        lang_prefix = language_code.split("-")[0].lower()
        target_lang = lang_names.get(lang_prefix, "English")

        if intent == PMEIntent.GENERAL_CONVERSATION:
            greetings_by_lang = {
                "hi": f"नमस्ते {patient_name}! मैं आपकी साथी CogniCompanion हूँ। मैं आपके साथ हूँ, बताइए आज मैं आपकी क्या मदद कर सकती हूँ?",
                "mr": f"नमस्कार {patient_name}! मी तुमची साथीदार CogniCompanion आहे. मी सदैव तुमच्या सोबत आहे, सांगा आज मी कशी मदत करू?",
                "bn": f"নমস্কার {patient_name}! আমি আপনার সহায়ক CogniCompanion। আমি আপনার পাশেই আছি, বলুন আজ আমি কীভাবে সাহায্য করতে পারি?",
                "ta": f"வணக்கம் {patient_name}! நான் உங்கள் CogniCompanion. நான் உங்களுடன் இருக்கிறேன், இன்று உங்களுக்கு எவ்வாறு உதவ முடியும்?",
                "te": f"నమస్కారం {patient_name}! నేను మీ CogniCompanion. నేను మీతోనే ఉన్నాను, ఈ రోజు మీకు ఎలా సహాయపడగలను?",
                "kn": f"ನಮಸ್ಕಾರ {patient_name}! ನಾನು ನಿಮ್ಮ CogniCompanion. ನಾನು ನಿಮ್ಮೊಂದಿಗಿದ್ದೇನೆ, ಇಂದು ನಾನು ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
                "gu": f"નમસ્તે {patient_name}! હું તમારી સહાયક CogniCompanion છું. હું તમારી સાથે જ છું, કહો આજે હું તમારી કેવી રીતે મદદ કરું?",
                "pa": f"ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ {patient_name}! ਮੈਂ ਤੁਹਾਡੀ ਸਾਥੀ CogniCompanion ਹਾਂ। ਮੈਂ ਤੁਹਾਡੇ ਨਾਲ ਹਾਂ, ਦੱਸੋ ਅੱਜ ਮੈਂ ਤੁਹਾਡੀ ਕੀ ਮਦਦ ਕਰ ਸਕਦੀ ਹਾਂ?",
                "ml": f"നമസ്കാരം {patient_name}! ഞാൻ നിങ്ങളുടെ സഹായിയായ CogniCompanion ആണ്. ഞാൻ കൂടെയുണ്ട്, ഇന്ന് എങ്ങനെ സഹായിക്കണം?",
                "as": f"নমস্কাৰ {patient_name}! মই আপোনাৰ সহায়ক CogniCompanion। মই আপোনাৰ লগতে আছোঁ, কওক আজি মই কেনেকৈ সহায় কৰিব পাৰোঁ?",
                "ne": f"नमस्ते {patient_name}! म तपाईंको सहयोगी CogniCompanion हुँ। म तपाईंसँगै छु, भन्नुहोस् आज म कसरी मद्दत गर्न सक्छु?",
                "lus": f"Chibai {patient_name}! Kei hi i thian CogniCompanion ka ni e. I kiangah ka awm reng a, vawiinah eng nge ka puih theih che?",
                "kha": f"Khublei {patient_name}! Nga dei ka CogniCompanion, i paralok jong phi. Nga don ryngkat bad phi, kumno nga lah ban iarap ia phi mynta ka sngi?",
                "grt": f"Salam {patient_name}! Anga na·arangni CogniCompanion ripeng ong·a. Anga na·ani sepangon donga, da·alo mai dakchakaniko nanga?",
                "trp": f"Kaham {patient_name}! Ang nini CogniCompanion logi. Ang nini logi-o tongo, tabuk tamo sanani nango?",
                "nag": f"Namaskar {patient_name}! Moi apnar CogniCompanion sathi ase. Moi apnar logot ase, aji ki modot koribo paribo?",
            }
            deterministic_reply = greetings_by_lang.get(
                lang_prefix,
                f"Hello {patient_name}! I am CogniCompanion, your personal memory assistant. I am right here with you. How can I help you today?"
            )
            facts_summary.append("General companion interaction.")

        elif intent == PMEIntent.UNKNOWN:
            if unified_memories:
                top_m = unified_memories[0]["memory"]
                d_str = top_m.event_date.strftime("%B %d, %Y")
                deterministic_reply = f"I found this memory: {top_m.title} from {d_str}. {top_m.description or ''}"
                facts_summary.append(f"Memory: {top_m.title} ({d_str}) - {top_m.description or ''}")
            else:
                unknown_by_lang = {
                    "hi": f"मैं हमेशा आपके साथ हूँ, {patient_name}। आप मुझसे अपने परिवार, तस्वीरों, दवाइयों या दिनचर्या के बारे में कुछ भी पूछ सकते हैं।",
                    "mr": f"मी नेहमी तुमच्या सोबत आहे, {patient_name}। तुम्ही मला तुमचे कुटुंब, आठवणी, औषधे किंवा दिनचर्येबद्दल विचारू शकता.",
                    "bn": f"আমি সর্বদা আপনার সাথে আছি, {patient_name}। আপনি পরিবার, স্মৃতি, ওষুধ বা রুটিন সম্পর্কে যেকোনো প্রশ্ন করতে পারেন।",
                    "ta": f"நான் உங்களுடன் இருக்கிறேன், {patient_name}. உங்கள் குடும்பம், நினைவுகள், மருந்துகள் அல்லது அட்டவணை பற்றி என்னிடம் கேட்கலாம்.",
                    "te": f"నేను మీతోనే ఉన్నాను, {patient_name}. మీ కుటుంబం, జ్ఞాపకాలు, మందులు లేదా దినచర్య గురించి నన్ను అడగవచ్చు.",
                    "kn": f"ನಾನು ನಿಮ್ಮೊಂದಿಗಿದ್ದೇನೆ, {patient_name}. ನಿಮ್ಮ ಕುಟುಂಬ, ನೆನಪುಗಳು, ಔಷಧ ಅಥವಾ ವೇಳಾಪಟ್ಟಿ ಬಗ್ಗೆ ಕೇಳಬಹುದು.",
                    "gu": f"હું હંમેશા તમારી સાથે છું, {patient_name}. તમે મને તમારા પરિવાર, દવાઓ કે દિનચર્યા વિશે પૂછી શકો છો.",
                    "pa": f"ਮੈਂ ਹਮੇਸ਼ਾ ਤੁਹਾਡੇ ਨਾਲ ਹਾਂ, {patient_name}। ਤੁਸੀਂ ਆਪਣੇ ਪਰਿਵਾਰ, ਦਵਾਈਆਂ ਜਾਂ ਸਮਾਂ-ਸਾਰਣੀ ਬਾਰੇ ਪੁੱਛ ਸਕਦੇ ਹੋ।",
                    "as": f"মই আপোনাৰ লগতে আছোঁ, {patient_name}। আপুনি আপোনাৰ পৰিয়াল, স্মৃতি, ঔষধ বা দিনচৰ্যাৰ বিষয়ে সুধিব পাৰে।",
                    "ne": f"म सधैं तपाईंसँगै छु, {patient_name}। तपाईं परिवार, सम्झना, औषधि वा तालिका बारे सोध्न सक्नुहुन्छ।",
                    "lus": f"I kiangah ka awm reng e, {patient_name}. I chhungte, thlalak, damdawi, emaw i hun hman dan chungchang min zawt thei ang.",
                    "kha": f"Nga don ryngkat bad phi, {patient_name}. Phi lah ban kylli shaphang ka iing ka sem, ki dur, ki dawai, lane ki kam ba man ka sngi.",
                    "grt": f"Anga na·ani sepangon donga, {patient_name}. Na·a no-nokdang, sam-bithiko ba salanti re·rurana kamo ma·sina sing·na man·a.",
                    "trp": f"Ang nini logi-o tongo, {patient_name}. Nwng nini nukhung, botol sam, ba kaisa kaisa samungno swngwi mano.",
                    "nag": f"Moi apnar logot ase, {patient_name}. Apni apnar ghor manu, dawa, photo aru somoi laga bikhoyte hudhibo pare.",
                }
                deterministic_reply = unknown_by_lang.get(
                    lang_prefix,
                    f"I am right here with you, {patient_name}. I can help you recall your family, photos, medication, game progress, or daily schedule. What would you like to know?"
                )
                facts_summary.append("Unrecognized query intent with no memory matches.")

        # Append background family and medication facts if available to enrich grounding
        all_ppl = retrieved_data.get("all_known_people", [])
        if all_ppl:
            ppl_str = ", ".join(f"{p.name} ({p.relationship or 'Family'})" for p in all_ppl if hasattr(p, "name"))
            if ppl_str and not any("Family & Loved Ones:" in f for f in facts_summary):
                facts_summary.append(f"Family & Loved Ones: {ppl_str}")

        all_meds = retrieved_data.get("medications", [])
        if all_meds:
            meds_str = ", ".join(m.name for m in all_meds if hasattr(m, "name"))
            if meds_str and not any("Prescribed Medications:" in f for f in facts_summary):
                facts_summary.append(f"Prescribed Medications: {meds_str}")

        system_instruction = (
            f"You are CogniCompanion, a warm, compassionate, and patient AI memory assistant and companion for {patient_name}.\n"
            f"LANGUAGE REQUIREMENT: Respond fluently, naturally, and warmly in {target_lang}. Use elder-friendly, respectful language and tone.\n"
            "BEHAVIORAL GUIDELINES:\n"
            "1. CONVERSATIONAL COMPANION: If the patient greets you, asks who you are, asks how you are, expresses feelings (e.g. loneliness, happiness, anxiety), or asks a general conversational question, respond with empathy, kindness, natural personality, and reassurance as a caring companion.\n"
            "2. PERSONAL FACTS GROUNDING: For questions about their family, memories, medications, visits, or schedule, base your answer strictly on the Grounded Facts below. Do NOT invent false family members, fictitious visits, or altered medical dosages.\n"
            "3. If asked about a personal memory or person not in Grounded Facts, politely and gently say you don't have that record saved yet.\n"
            "4. Keep responses brief (1-3 sentences), simple, and reassuring for elderly listeners.\n"
            "5. CPI is strictly an assistive indicator, never an assertive medical diagnosis.\n"
            "6. Never reveal sensitive internal credentials, passwords, or technical tokens.\n"
            "7. Grounded Facts:\n" + "\n".join(f"- {f}" for f in facts_summary)
        )

        return {
            "deterministic_reply": deterministic_reply,
            "facts_summary": facts_summary,
            "system_instruction": system_instruction,
        }
