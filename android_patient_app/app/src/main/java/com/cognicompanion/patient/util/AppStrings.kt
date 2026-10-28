package com.cognicompanion.patient.util

/**
 * CogniCompanion Multilingual UI String Repository
 * Provides localized interface strings mapped to BCP-47 language codes
 * (e.g. "en-IN", "as-IN", "hi-IN", "mni-IN", "kha-IN").
 */
object AppStrings {

    fun get(key: String, languageCode: String = "en-IN"): String {
        val lang = languageCode.split("-").first().lowercase()
        val langMap = translations[lang] ?: translations["en"] ?: emptyMap()
        return langMap[key] ?: (translations["en"]?.get(key) ?: key)
    }

    private val en = mapOf(
        "nav_home" to "Home",
        "nav_today" to "Today",
        "nav_voice" to "Assistant",
        "nav_games" to "Games",
        "nav_memories" to "Memories",
        "nav_profile" to "Profile",

        "greeting_morning" to "Good morning,",
        "greeting_afternoon" to "Good afternoon,",
        "greeting_evening" to "Good evening,",

        "todays_overview" to "Today's Overview",
        "todays_schedule" to "Today's Schedule",
        "view_daily_plan" to "View full daily plan",
        "medications" to "Medications",
        "routines" to "Routines",
        "taken" to "Taken",
        "pending" to "Pending",
        "total" to "Total",
        "done" to "Done",
        "take_dose" to "Take",
        "dose_taken" to "Taken",

        "cognitive_status" to "Cognitive Status",
        "needs_attention" to "Needs Attention",
        "no_scheduled" to "Nothing scheduled for today.",

        "voice_assistant" to "Voice Assistant",
        "continuous_mode" to "Continuous Voice (Hands-Free)",
        "tap_to_talk" to "Hold to Speak",
        "listening" to "Listening...",
        "processing" to "Thinking...",
        "speaking" to "Speaking...",
        "barge_in_hint" to "Speak anytime to interrupt",

        "accessibility" to "Accessibility",
        "simple_mode" to "Simple Mode",
        "simple_mode_desc" to "Larger text and simplified cards for easy reading",
        "text_size" to "Text Size",
        "high_contrast" to "High Contrast",
        "emergency_contact" to "Emergency Contact",
        "call" to "Call",
        "language" to "Language",
        "logout" to "Log out",

        "memories_title" to "Memories",
        "people_title" to "People",
        "no_memories" to "No memories recorded yet.",
        "cognitive_games" to "Cognitive Games"
    )

    private val asLang = mapOf(
        "nav_home" to "গৃহ",
        "nav_today" to "আজি",
        "nav_voice" to "সহায়ক",
        "nav_games" to "খেল",
        "nav_memories" to "স্মৃতি",
        "nav_profile" to "প্ৰফাইল",

        "greeting_morning" to "সুপ্ৰভাত,",
        "greeting_afternoon" to "শুভ অপৰাহ্ন,",
        "greeting_evening" to "শুভ সন্ধিয়া,",

        "todays_overview" to "আজিৰ পৰ্যালোচনা",
        "todays_schedule" to "আজিৰ কাৰ্যসূচী",
        "view_daily_plan" to "সম্পূৰ্ণ দিনটোৰ পৰিকল্পনা চাওক",
        "medications" to "ঔষধ",
        "routines" to "দৈনন্দিন নিয়ম",
        "taken" to "লোৱা হ'ল",
        "pending" to "বাকী আছে",
        "total" to "মুঠ",
        "done" to "সম্পূৰ্ণ",
        "take_dose" to "লওক",
        "dose_taken" to "লোৱা হৈছে",

        "cognitive_status" to "মানসিক স্থিতি",
        "needs_attention" to "মনোযোগৰ প্ৰয়োজন",
        "no_scheduled" to "আজিৰ বাবে কোনো কাৰ্যসূচী নাই।",

        "voice_assistant" to "কণ্ঠ সহায়ক",
        "continuous_mode" to "নিৰন্তৰ কণ্ঠ সহায় (হাত নলগোৱাকৈ)",
        "tap_to_talk" to "ক'বলৈ ধৰি ৰাখক",
        "listening" to "শুনি থকা হৈছে...",
        "processing" to "চিন্তা কৰি থকা হৈছে...",
        "speaking" to "উত্তৰ দি থকা হৈছে...",
        "barge_in_hint" to "মাজতে ৰখাবলৈ যেতিয়াই মন কথা কওক",

        "accessibility" to "সুলভ সুবিধা",
        "simple_mode" to "সহজ ৰূপ (Simple Mode)",
        "simple_mode_desc" to "সহজে পঢ়িবলৈ ডাঙৰ আখৰ আৰু সহজ কাৰ্ড",
        "text_size" to "আখৰৰ আকাৰ",
        "high_contrast" to "স্পষ্ট ৰং",
        "emergency_contact" to "জৰুৰীকালীন যোগাযোগ",
        "call" to "ফোন কৰক",
        "language" to "ভাষা",
        "logout" to "লগ আউট",

        "memories_title" to "স্মৃতিসমূহ",
        "people_title" to "আপোনজন",
        "no_memories" to "এতিয়ালৈকে কোনো স্মৃতি নথিভুক্ত হোৱা নাই।",
        "cognitive_games" to "স্মৃতি বিকাশৰ খেল"
    )

    private val hi = mapOf(
        "nav_home" to "होम",
        "nav_today" to "आज",
        "nav_voice" to "सहायक",
        "nav_games" to "खेल",
        "nav_memories" to "यादें",
        "nav_profile" to "प्रोफ़ाइल",

        "greeting_morning" to "सुप्रभात,",
        "greeting_afternoon" to "शुभ दोपहर,",
        "greeting_evening" to "शुभ संध्या,",

        "todays_overview" to "आज का सारांश",
        "todays_schedule" to "आज की दिनचर्या",
        "view_daily_plan" to "पूरा दैनिक प्लान देखें",
        "medications" to "दवाइयाँ",
        "routines" to "दैनिक नियम",
        "taken" to "ली गई",
        "pending" to "बाकी",
        "total" to "कुल",
        "done" to "पूर्ण",
        "take_dose" to "दवा लें",
        "dose_taken" to "ली जा चुकी",

        "cognitive_status" to "मानसिक स्थिति",
        "needs_attention" to "ध्यान देने योग्य",
        "no_scheduled" to "आज के लिए कोई कार्यक्रम नहीं है।",

        "voice_assistant" to "वॉइस असिस्टेंट",
        "continuous_mode" to "हैंड्स-फ्री निरंतर आवाज़",
        "tap_to_talk" to "बोलने के लिए दबाएं",
        "listening" to "सुन रहा हूँ...",
        "processing" to "सोच रहा हूँ...",
        "speaking" to "बोल रहा हूँ...",
        "barge_in_hint" to "रोकने के लिए कभी भी बोलें",

        "accessibility" to "सुलभता",
        "simple_mode" to "सरल मोड (Simple Mode)",
        "simple_mode_desc" to "आसानी से पढ़ने हेतु बड़े अक्षर और सरल कार्ड",
        "text_size" to "अक्षरों का आकार",
        "high_contrast" to "हाई कंट्रास्ट",
        "emergency_contact" to "आपातकालीन संपर्क",
        "call" to "कॉल करें",
        "language" to "भाषा",
        "logout" to "लॉग आउट",

        "memories_title" to "यादें",
        "people_title" to "अपने लोग",
        "no_memories" to "अभी तक कोई यादें दर्ज नहीं हैं।",
        "cognitive_games" to "दिमागी कसरत के खेल"
    )

    private val mni = mapOf(
        "nav_home" to "ꯌꯨꯝ",
        "nav_today" to "ꯉꯁꯤ",
        "nav_voice" to "ꯃꯇꯦꯡ ꯄꯥꯡꯕ",
        "nav_games" to "ꯁꯥꯟꯅꯄꯣꯠ",
        "nav_memories" to "ꯅꯤꯡꯁꯤꯡꯕ",
        "nav_profile" to "ꯄ꯭ꯔꯣꯐꯥꯏꯜ",

        "greeting_morning" to "ꯑꯌꯨꯛꯀꯤ ꯈꯨꯔꯨꯝꯖꯔꯤ,",
        "greeting_afternoon" to "ꯅꯨꯃꯤꯗꯥꯡꯋꯥꯏꯒꯤ ꯈꯨꯔꯨꯝꯖꯔꯤ,",
        "greeting_evening" to "ꯅꯨꯃꯤꯗꯥꯡꯒꯤ ꯈꯨꯔꯨꯝꯖꯔꯤ,",

        "todays_overview" to "ꯉꯁꯤꯒꯤ ꯑꯄꯨꯅꯕ",
        "todays_schedule" to "ꯉꯁꯤꯒꯤ ꯊꯧꯔꯥꯡ",
        "view_daily_plan" to "ꯉꯁꯤꯒꯤ ꯊꯧꯔꯥꯡ ꯄꯨꯝꯅꯃꯛ ꯌꯦꯡꯕꯤꯌꯨ",
        "medications" to "ꯍꯤꯗꯥꯛ",
        "take_dose" to "ꯂꯧꯕꯤꯌꯨ",
        "emergency_contact" to "ꯑꯀꯅꯕ ꯃꯇꯝꯗ ꯄꯥꯎ ꯐꯥꯎꯅꯐꯝ",
        "call" to "ꯀꯣꯜ ꯇꯧꯕꯤꯌꯨ",
        "language" to "ꯂꯣꯟ",
        "logout" to "ꯂꯣꯒ ꯑꯥꯎꯠ"
    )

    private val kha = mapOf(
        "nav_home" to "Ing",
        "nav_today" to "Mynta",
        "nav_voice" to "Nongiarap",
        "nav_games" to "Giem",
        "nav_memories" to "Kynmaw",
        "nav_profile" to "Profile",

        "greeting_morning" to "Khublei mynstep,",
        "greeting_afternoon" to "Khublei mynsngi,",
        "greeting_evening" to "Khublei janmiet,",

        "todays_overview" to "Ka jingthoh mynta ka sngi",
        "todays_schedule" to "Ka prokram mynta ka sngi",
        "view_daily_plan" to "Peit lut ia ka prokram baroh",
        "medications" to "Dawai",
        "take_dose" to "Dih",
        "emergency_contact" to "Jingtip kyrkieh",
        "call" to "Phone",
        "language" to "Ktien",
        "logout" to "Mih noh"
    )

    private val translations: Map<String, Map<String, String>> = mapOf(
        "en" to en,
        "as" to asLang,
        "hi" to hi,
        "mni" to mni,
        "kha" to kha
    )
}
