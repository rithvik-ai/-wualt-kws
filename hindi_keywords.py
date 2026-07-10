"""
Comprehensive Hindi emergency lexicon (Devanagari + romanized), grouped by intent.
Pure data (no enum imports) so safety_ring_audio_classifier can merge it into
KEYWORD_SEVERITY / KEYWORD_LANGUAGE / LABEL_CATEGORY and the keyword head can pull
the phrases. state: 'distress' | 'stress'. category: violence / medical / fall /
fire / accident / environment, or None (generic cry).

Each entry:  key -> (phrases[], state, severity, category)

NOTE: bare "मम्मी/पापा/माँ" (calling parents) are marked STRESS not DISTRESS — on
their own they're too common to alarm; the fused system escalates them with
prosody/fear context. Romanizations avoid English collisions (no bare "no"/"are"/
"oh"); Devanagari is matched as a substring.
"""

HINDI_EMERGENCY_RAW = {
    # 1. Help requests
    "hi_save_me": (["बचाओ", "मुझे बचाओ", "bachao", "mujhe bachao"], "distress", 90, None),
    "hi_help": (["मदद करो", "मेरी मदद करो", "प्लीज़ मदद करो", "जल्दी मदद करो", "madad karo",
                 "meri madad karo", "madad"], "distress", 88, None),
    "hi_anyone_there": (["कोई है", "koi hai"], "distress", 78, None),
    "hi_come_quick": (["जल्दी आओ", "किसी को बुलाओ", "jaldi aao", "kisi ko bulao"], "distress", 85, None),
    # 2. Physical assault  (+ 9. sexual assault overlap)
    "hi_let_go": (["छोड़ दो", "छोड़िए", "मुझे छोड़ दो", "मुझे जाने दो", "प्लीज़ छोड़ दो",
                   "chhod do", "mujhe chhod do", "mujhe jaane do"], "distress", 90, "violence"),
    "hi_dont_touch": (["हाथ मत लगाओ", "मत छुओ", "haath mat lagao", "mat chhuo"], "distress", 90, "violence"),
    "hi_stay_away": (["दूर रहो", "दूर हटो", "पीछे हटो", "हटो", "door raho", "door hato", "peeche hato"],
                     "distress", 82, "violence"),
    "hi_dont_do": (["मत करो", "mat karo"], "distress", 72, "violence"),
    "hi_no": (["नहीं", "nahin", "nahi"], "stress", 45, None),
    # 3. Robbery / theft
    "hi_thief": (["चोर", "चोरी", "chor", "chori"], "distress", 85, "violence"),
    "hi_my_stuff": (["मेरा बैग", "मेरा फोन", "mera bag", "mera phone"], "stress", 65, "violence"),
    "hi_catch_them": (["पकड़ो", "कोई रोकिए", "pakdo", "koi rokiye"], "distress", 80, "violence"),
    # 4. Fire
    "hi_fire": (["आग लग गई", "आग", "aag lag gayi", "aag"], "distress", 92, "fire"),
    "hi_smoke": (["धुआँ", "dhuaan"], "distress", 85, "fire"),
    "hi_get_out": (["बाहर निकलो", "जल्दी भागो", "bahar niklo", "jaldi bhago"], "distress", 85, "fire"),
    # 5. Medical emergency
    "hi_pain": (["मुझे दर्द हो रहा है", "दर्द हो रहा है", "dard ho raha hai"], "distress", 85, "medical"),
    "hi_cant_breathe": (["साँस नहीं आ रही", "saans nahin aa rahi", "saans nahi aa rahi"], "distress", 95, "medical"),
    "hi_dizzy": (["मुझे चक्कर आ रहा है", "चक्कर आ रहा है", "chakkar aa raha hai"], "distress", 85, "medical"),
    "hi_call_doctor": (["डॉक्टर बुलाओ", "doctor bulao"], "distress", 90, "medical"),
    "hi_call_ambulance": (["एम्बुलेंस बुलाओ", "ambulance bulao"], "distress", 92, "medical"),
    "hi_fell": (["मैं गिर गया", "गिर गया", "main gir gaya"], "distress", 82, "fall"),
    "hi_passing_out": (["मैं बेहोश हो रहा हूँ", "बेहोश", "behosh ho raha hoon"], "distress", 90, "medical"),
    # 6. Accident
    "hi_accident": (["एक्सीडेंट हो गया", "टक्कर हो गई", "accident ho gaya", "takkar ho gayi"],
                    "distress", 88, "accident"),
    "hi_injured": (["कोई घायल है", "घायल", "koi ghayal hai"], "distress", 88, "accident"),
    # 7. Child distress (parent-calls = STRESS; fear = DISTRESS)
    "hi_mother": (["मम्मी", "माँ", "mummy", "maa"], "stress", 55, None),
    "hi_father": (["पापा", "papa"], "stress", 55, None),
    "hi_go_home": (["मुझे घर जाना है", "ghar jana hai"], "stress", 60, None),
    # 8. Fear / panic
    "hi_scared": (["मुझे डर लग रहा है", "मैं डर गया", "dar lag raha hai", "dar gaya"], "distress", 78, None),
    "hi_what_do": (["क्या करूँ", "kya karun"], "stress", 55, None),
    "hi_oh_god": (["हे भगवान", "हाय राम", "भगवान", "hey bhagwan", "hai ram"], "stress", 48, None),
    "hi_oh_no": (["अरे नहीं", "arre nahin"], "stress", 45, None),
    # 10. Domestic violence
    "hi_dont_hit": (["मुझे मत मारो", "मत मारो", "मत पीटो", "mat maaro", "mujhe mat maaro", "mat peeto"],
                    "distress", 90, "violence"),
    "hi_stop_it": (["बस करो", "bas karo"], "distress", 70, "violence"),
    "hi_listen_to_me": (["मेरी बात सुनो", "meri baat suno"], "stress", 55, None),
    # 11. Panic exclamations
    "hi_exclaim": (["अरे बाप रे", "बाप रे", "अरे", "ओह", "arre baap re", "baap re"], "stress", 42, None),
}
