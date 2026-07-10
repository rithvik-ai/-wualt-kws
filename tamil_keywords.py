"""
Comprehensive Tamil emergency lexicon (script + romanized), grouped by intent.
Pure data (no enum imports) so safety_ring_audio_classifier can merge it into
KEYWORD_SEVERITY / KEYWORD_LANGUAGE / LABEL_CATEGORY and the keyword head can
pull the phrases. state: 'distress' | 'stress'. category: one of violence /
medical / fall / fire / accident / environment, or None (generic cry).

Each entry:  key -> (phrases[], state, severity, category)
"""

TAMIL_EMERGENCY_RAW = {
    # 1. Direct cries for help
    "ta_help": (["உதவி", "உதவுங்கள்", "உதவுங்க", "உதவி பண்ணுங்க", "ஹெல்ப்", "ஹெல்ப் பண்ணுங்க",
                 "udhavi", "uthavi", "udhavunga", "udhavi pannunga", "help pannunga"],
                "distress", 88, None),
    "ta_save_me": (["காப்பாத்துங்க", "காப்பாற்றுங்கள்", "காப்பாத்து", "காப்பாற்று",
                    "என்னைக் காப்பாத்துங்க", "என்னைக் காப்பாற்றுங்க", "save me",
                    "kaapathunga", "kappathunga", "kaapaatru", "enna kaapathunga"],
                   "distress", 90, None),
    "ta_sos": (["SOS", "please help", "pls help"], "distress", 90, None),
    "ta_anyone_help": (["யாராவது உதவுங்க", "யாராவது காப்பாத்துங்க", "யாராச்சும் உதவுங்க",
                        "யாராச்சும் வாங்க", "yaaravathu help", "yaarachum help", "yaarachum vaanga"],
                       "distress", 88, None),
    # 2. Emergency
    "ta_emergency": (["அவசரம்", "எமர்ஜென்சி", "emergency"], "distress", 85, None),
    "ta_danger": (["ஆபத்து", "பெரும் ஆபத்து", "உயிர் ஆபத்து", "உயிருக்கு ஆபத்து", "ஆபத்துல இருக்கேன்",
                   "ஆபத்தா இருக்கு", "aabathu", "uyiruku aabathu", "aabathula iruken"],
                  "distress", 88, None),
    "ta_trouble": (["பிரச்சனை", "பெரிய பிரச்சனை", "சிக்கல்", "கஷ்டம்", "மோசமா இருக்கு"],
                   "stress", 55, None),
    # 3. Someone attacking
    "ta_hitting": (["அடிக்கிறாங்க", "அடிக்கிறார்", "அடிக்குறாங்க", "அடிச்சுட்டாங்க", "அடிச்சாங்க",
                    "என்னை அடிக்கிறாங்க", "adikiranga", "adikuranga", "enna adikuranga", "enna adikiraanga"],
                   "distress", 90, "violence"),
    "ta_attacking": (["தாக்குறாங்க", "தாக்குறார்", "தாக்கிட்டாங்க", "thaakkuranga", "thaakuranga"],
                     "distress", 90, "violence"),
    "ta_kill": (["கொல்ல வராங்க", "கொல்லுறாங்க", "கொலை பண்ணுறாங்க", "கொலை செய்யுறாங்க",
                 "வெட்டுறாங்க", "குத்துறாங்க", "kolraanga", "kolla varanga", "kolluranga"],
                "distress", 95, "violence"),
    "ta_shoot": (["சுடுறாங்க", "சுட்டாங்க", "suduranga"], "distress", 95, "violence"),
    # 4. Kidnap / forced
    "ta_kidnap": (["கடத்துறாங்க", "கடத்திட்டாங்க", "பிடிச்சுட்டாங்க", "பிடிச்சாங்க",
                   "kadathuranga", "kadathitanga", "pidichanga"], "distress", 92, "violence"),
    "ta_forced": (["வலுக்கட்டாயம்", "கட்டிப்போட்டாங்க", "பூட்டிட்டாங்க", "பூட்டி வைச்சிருக்காங்க",
                   "வெளியே விட மாட்டாங்க", "தப்பிக்க முடியல", "வெளியே போக முடியல", "சிறை வைத்திருக்காங்க"],
                  "distress", 90, "violence"),
    # 5. Robbery
    "ta_robbery": (["திருடுறாங்க", "கொள்ளையடிக்கிறாங்க", "கொள்ளை", "பறிச்சுட்டாங்க", "பணம் எடுத்துட்டாங்க",
                    "போன் எடுத்துட்டாங்க", "பை எடுத்துட்டாங்க", "thiruduranga", "kollai"],
                   "distress", 82, "violence"),
    "ta_threaten": (["மிரட்டுறாங்க", "மிரட்டல்", "miraturanga"], "distress", 85, "violence"),
    "ta_knife": (["கத்தி காட்டுறாங்க", "கத்தி", "kathi vechirukanga", "kathi"], "distress", 88, "violence"),
    "ta_gun": (["துப்பாக்கி காட்டுறாங்க", "துப்பாக்கி", "thupaki"], "distress", 90, "violence"),
    # 6. Fire
    "ta_fire": (["தீ பிடிச்சிருக்கு", "தீப்பிடிச்சு", "தீ", "நெருப்பு", "எரியுது", "எரிகிறது",
                 "வீடு எரியுது", "புகை நிறைய இருக்கு", "புகை", "fire accident", "neruppu", "eriyuthu", "pugai"],
                "distress", 92, "fire"),
    # 7. Medical
    "ta_cant_breathe": (["மூச்சு விட முடியல", "மூச்சு திணறுது", "மூச்சு அடைக்குது", "சுவாசிக்க முடியல",
                         "moochu vida mudiyala", "moochu thinaruthu"], "distress", 95, "medical"),
    "ta_faint": (["மயங்கி விழுந்துட்டேன்", "மயக்கம்", "mayakkam"], "distress", 85, "medical"),
    "ta_bleeding": (["ரத்தம் நிறைய வருது", "ரத்தம் வருது", "இரத்தம்", "ratham varuthu"], "distress", 90, "medical"),
    "ta_dying": (["உயிர் போகுது", "சாகப்போறேன்", "சாகுறேன்", "uyir poguthu"], "distress", 97, "medical"),
    "ta_chest_pain": (["இதயம் வலிக்குது", "மார்பு வலி", "நெஞ்சு வலி", "nenju vali"], "distress", 93, "medical"),
    "ta_severe_pain": (["வலி தாங்க முடியல", "கை கால அசையல", "vali thanga mudiyala"], "distress", 85, "medical"),
    # 8. Accident
    "ta_accident": (["விபத்து", "ஆக்சிடென்ட்", "கார் மோதி", "பைக் மோதி", "லாரி மோதி", "மோதிட்டாங்க",
                     "accident", "vibathu"], "distress", 88, "accident"),
    "ta_fell_down": (["கீழே விழுந்துட்டேன்", "keezhe vizhunthutten"], "distress", 82, "fall"),
    # 9. Lost
    "ta_lost": (["வழி தெரியல", "தொலைஞ்சுட்டேன்", "காணாம போயிட்டேன்", "வழி சொல்லுங்க", "என் குழந்தை காணோம்",
                 "காணவில்லை", "vazhi theriyala", "kaanaama poyitten", "help me find"], "stress", 60, "environment"),
    # 10. Stuck
    "ta_stuck": (["மாட்டிக்கிட்டேன்", "சிக்கிக்கிட்டேன்", "வெளியே வர முடியல", "கதவு திறக்கல",
                  "லிப்ட்ல மாட்டிக்கிட்டேன்", "உள்ளே பூட்டிட்டாங்க", "சிக்கி இருக்கேன்",
                  "maatikiten", "sikkikiten", "veliya vara mudiyala"], "distress", 78, "accident"),
    # 11. Flood / disaster
    "ta_disaster": (["வெள்ளம்", "தண்ணீர் ஏறுது", "புயல்", "சூறாவளி", "மழைல மாட்டிக்கிட்டேன்", "நிலச்சரிவு",
                     "பூகம்பம்", "earthquake", "cyclone", "vellam", "puyal"], "distress", 85, "environment"),
    # 12. Domestic violence
    "ta_domestic": (["வீட்டுல அடிக்கிறாங்க", "கணவர் அடிக்கிறார்", "மனைவி அடிக்கிறாங்க", "அப்பா அடிக்கிறார்",
                     "அம்மா அடிக்கிறாங்க", "வீட்டுல சண்டை", "குடும்ப வன்முறை", "கொடுமை", "துன்புறுத்துறாங்க",
                     "துன்புறுத்தல்", "abuse", "violence"], "distress", 88, "violence"),
    # 13. Sexual danger
    "ta_sexual": (["பாலியல் தொல்லை", "கற்பழிப்பு", "பலாத்காரம்", "கையை பிடிச்சாங்க", "தவறா தொடுறாங்க",
                   "பின்தொடருறாங்க", "தொந்தரவு", "stalking", "harassment", "molest", "rape", "assault"],
                  "distress", 93, "violence"),
    # 14. Fear
    "ta_fear": (["ரொம்ப பயமா இருக்கு", "பயமா இருக்கு", "பயந்துட்டேன்", "என்ன பண்ணறது தெரியல",
                 "bayama iruku", "bayanthutten"], "distress", 80, None),
    # 15. Calling someone
    "ta_police": (["போலீஸ் கூப்பிடுங்க", "போலீஸை கூப்பிடுங்க", "காவல்துறை", "போலீஸ்", "police"],
                  "distress", 90, None),
    "ta_ambulance": (["ஆம்புலன்ஸ்", "ambulance", "டாக்டர்", "doctor", "108", "fire service"],
                     "distress", 92, "medical"),
}
