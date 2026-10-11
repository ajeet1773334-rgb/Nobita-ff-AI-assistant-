# Nobita FF project generator. Chalane par saari files bana deta hai.
import os
FILES = {}
FILES['app/build.gradle.kts'] = r'''plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.nobita.ff"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.nobita.ff"
        minSdk = 29
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}
'''
FILES['app/src/main/AndroidManifest.xml'] = r'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.READ_CONTACTS" />
    <uses-permission android:name="android.permission.CALL_PHONE" />
    <uses-permission android:name="com.android.alarm.permission.SET_ALARM" />

    <queries>
        <intent>
            <action android:name="android.intent.action.MAIN" />
            <category android:name="android.intent.category.LAUNCHER" />
        </intent>
        <intent>
            <action android:name="android.speech.RecognitionService" />
        </intent>
        <intent>
            <action android:name="android.intent.action.TTS_SERVICE" />
        </intent>
        <package android:name="com.whatsapp" />
        <package android:name="com.whatsapp.w4b" />
        <package android:name="com.google.android.youtube" />
    </queries>

    <application
        android:allowBackup="false"
        android:icon="@drawable/ic_launcher"
        android:label="@string/app_name"
        android:theme="@android:style/Theme.Material.NoActionBar">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:screenOrientation="portrait">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <service
            android:name=".NobitaService"
            android:exported="true"
            android:label="@string/service_label"
            android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE">
            <intent-filter>
                <action android:name="android.accessibilityservice.AccessibilityService" />
            </intent-filter>
            <meta-data
                android:name="android.accessibilityservice"
                android:resource="@xml/accessibility_config" />
        </service>
    </application>
</manifest>
'''
FILES['app/src/main/java/com/nobita/ff/CommandProcessor.kt'] = r'''package com.nobita.ff

import android.Manifest
import android.accessibilityservice.AccessibilityService
import android.app.Activity
import android.app.SearchManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.media.AudioManager
import android.net.Uri
import android.provider.AlarmClock
import android.provider.ContactsContract
import android.provider.Settings
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

/**
 * Nobita ka dimaag: bole gaye text ko samajhkar kaam karta hai.
 * Har raaste par say(...) zaroor bulaya jaata hai taaki assistant jawab de.
 */
class CommandProcessor(private val act: Activity, private val say: (String) -> Unit) {

    private data class Contact(val name: String, val number: String)

    private val prefs = act.getSharedPreferences("nobita", Context.MODE_PRIVATE)

    // ---------- shabd-suchiyan ----------

    private val wakeWords = listOf(
        "hey nobita", "ok nobita", "हे नोबिता", "ओके नोबिता",
        "nobita", "नोबिता", "नोबीता", "नोबिटा", "नोबीटा"
    )

    private val waVariants = listOf(
        "व्हाट्स ऐप", "व्हाट्स एप", "वाट्स ऐप", "वाट्स एप", "वॉट्स ऐप", "whats app",
        "व्हाट्सएप्प", "व्हाट्सऐप", "व्हाट्सएप", "व्हॉट्सऐप", "व्हॉट्सएप", "व्हाट्सअप",
        "वाट्सएप", "वाट्सऐप", "वाट्सअप", "वॉट्सऐप", "वॉट्सएप", "वट्सऐप", "वट्सएप"
    )

    private val numberWords: Map<String, Int> = mapOf(
        "एक" to 1, "ek" to 1, "one" to 1,
        "दो" to 2, "do" to 2, "two" to 2,
        "तीन" to 3, "teen" to 3, "three" to 3,
        "चार" to 4, "char" to 4, "four" to 4,
        "पांच" to 5, "पाँच" to 5, "paanch" to 5, "panch" to 5, "five" to 5,
        "छह" to 6, "छः" to 6, "छे" to 6, "chhe" to 6, "six" to 6,
        "सात" to 7, "saat" to 7, "seven" to 7,
        "आठ" to 8, "aath" to 8, "eight" to 8,
        "नौ" to 9, "nau" to 9, "nine" to 9,
        "दस" to 10, "das" to 10, "ten" to 10,
        "ग्यारह" to 11, "gyarah" to 11, "eleven" to 11,
        "बारह" to 12, "barah" to 12, "twelve" to 12
    )

    private val appAliases: Map<String, String> = mapOf(
        "फ्री फायर मैक्स" to "free fire max", "फ्री फायर" to "free fire", "फ्री फ़ायर" to "free fire",
        "फ्रीफायर" to "free fire", "free fire" to "free fire",
        "यूट्यूब" to "youtube", "यू ट्यूब" to "youtube",
        "फेसबुक" to "facebook", "इंस्टाग्राम" to "instagram", "इंस्टा" to "instagram",
        "क्रोम" to "chrome", "गूगल मैप्स" to "maps", "गूगल मैप" to "maps", "मैप्स" to "maps",
        "गूगल" to "google", "कैमरा" to "camera", "गैलरी" to "gallery", "सेटिंग्स" to "settings",
        "सेटिंग" to "settings", "कैलकुलेटर" to "calculator", "कैलेंडर" to "calendar",
        "घड़ी" to "clock", "प्ले स्टोर" to "play store", "प्लेस्टोर" to "play store",
        "स्नैपचैट" to "snapchat", "टेलीग्राम" to "telegram", "पेटीएम" to "paytm",
        "फोनपे" to "phonepe", "फोन पे" to "phonepe", "जीमेल" to "gmail",
        "स्पॉटिफाई" to "spotify", "नेटफ्लिक्स" to "netflix", "ट्विटर" to "twitter",
        "बीजीएमआई" to "bgmi", "फाइल्स" to "files", "संपर्क" to "contacts", "कॉन्टैक्ट्स" to "contacts",
        "मैसेज" to "messages", "व्हाट्सएप" to "whatsapp"
    )

    private val openVerbsStrong = listOf("open", "kholo", "खोलो", "खोल दो", "खोलिए", "खोलिये", "khol do", "launch", "लॉन्च")
    private val openVerbsWeak = listOf("start", "चालू करो", "शुरू करो", "चलाओ", "chalao", "chalu")

    private val fillWords = setOf(
        "karo", "करो", "kar", "कर", "do", "दो", "ko", "को", "app", "ऐप", "एप", "एप्प", "please", "plz",
        "प्लीज", "na", "न", "zara", "जरा", "ज़रा", "ek", "एक", "mere", "मेरे", "meri", "मेरी", "mera", "मेरा",
        "ji", "जी", "se", "से", "pe", "par", "पर", "पे", "me", "mein", "में", "ki", "की", "ka", "का", "ke", "के"
    )

    // ---------- mukhya function ----------

    fun handle(raw: String) {
        val t = normalize(raw)
        if (t.isEmpty()) {
            say("मैंने कुछ सुना नहीं।")
            return
        }
        try {
            route(t)
        } catch (e: Exception) {
            say("कुछ गड़बड़ हो गई, फिर से कोशिश कीजिए।")
        }
    }

    private fun route(t: String) {
        // 1) WhatsApp message (pehle, taaki message ke andar "lock" jaise shabd se phone lock na ho)
        if (tryWhatsApp(t)) return
        // 2) Unlock (Android allow nahi karta)
        if (has(t, "unlock", "अनलॉक", "अन लॉक", "अनलोक", "अन्लॉक")) {
            say("माफ़ कीजिए, Android की सुरक्षा की वजह से कोई भी ऐप फ़ोन अनलॉक नहीं कर सकता। आप पिन या फ़िंगरप्रिंट से खुद खोल लीजिए।")
            return
        }
        // 3) Lock
        if (hasWord(t, "lock") || has(t, "लॉक", "ताला", "screen off", "स्क्रीन बंद", "स्क्रीन ऑफ", "स्क्रीन आफ")) {
            lockPhone()
            return
        }
        // 4) Call
        if (tryCall(t)) return
        // 5) Alarm / Timer
        if (tryAlarmOrTimer(t)) return
        // 6) Torch
        if (has(t, "torch", "टॉर्च", "टोर्च", "टार्च", "flashlight", "flash light", "फ्लैशलाइट", "फ्लैश लाइट", "बत्ती")) {
            torch(!has(t, "off", "बंद", "band", "बुझा", "ऑफ", "आफ"))
            return
        }
        // 7) Volume
        if (has(t, "volume", "वॉल्यूम", "वोल्यूम", "वाल्यूम", "आवाज")) {
            volume(t)
            return
        }
        // 8) System buttons
        if (trySystemButtons(t)) return
        // 9) Settings panels
        if (trySettingsPanels(t)) return
        // 10) Time / date
        if (has(t, "कितने बजे", "टाइम क्या", "समय क्या", "what time", "time kya", "time batao", "टाइम बताओ", "समय बताओ")) {
            tellTime()
            return
        }
        if (has(t, "तारीख", "date kya", "date batao", "आज क्या दिन", "today date", "डेट क्या", "डेट बताओ")) {
            tellDate()
            return
        }
        // 11) App kholna
        if (tryOpenApp(t)) return
        // 12) Maps
        if (has(t, "navigate", "नेविगेट", "रास्ता", "directions", "नक्शा", "मैप पर", "map par", "map pe")) {
            maps(t)
            return
        }
        // 13) YouTube / gaana
        if (has(t, "youtube", "यूट्यूब", "यू ट्यूब", "play ", "प्ले ", "bajao", "बजाओ", "gana", "गाना", "गाने", "gaane", "song", "सॉन्ग", "सोंग", "music", "म्यूजिक")) {
            music(t)
            return
        }
        // 14) Google search
        if (has(t, "search", "सर्च", "google par", "google pe", "गूगल पर", "खोजो", "ढूंढो", "ढूँढो", "dhundo", "khojo")) {
            webSearch(t)
            return
        }
        // 15) Baaki sab kuch - Claude se poochho
        askClaude(t)
    }

    // ---------- helpers ----------

    private fun has(t: String, vararg words: String): Boolean = words.any { t.contains(it) }

    /** Poora English shabd match karta hai (jaise "lock" to match, par "block" ya "clock" nahi). */
    private fun hasWord(t: String, w: String): Boolean =
        Regex("(^|[^a-z])" + Regex.escape(w) + "([^a-z]|$)").containsMatchIn(t)

    private fun tokens(t: String): List<String> = t.split(" ").filter { it.isNotBlank() }

    private fun normalize(raw: String): String {
        var s = raw.lowercase(Locale.ROOT)
        val sb = StringBuilder()
        for (ch in s) {
            if (ch in '०'..'९') {
                sb.append('0' + (ch - '०'))
            } else {
                sb.append(ch)
            }
        }
        s = sb.toString()
        s = s.replace(Regex("[,.!?।\"']"), " ")
        for (v in waVariants) s = s.replace(v, " whatsapp ")
        s = s.replace(Regex("\\s+"), " ").trim()
        var changed = true
        while (changed) {
            changed = false
            for (w in wakeWords) {
                if (s == w) {
                    s = ""
                    changed = true
                } else if (s.startsWith("$w ")) {
                    s = s.substring(w.length).trim()
                    changed = true
                }
            }
        }
        return s
    }

    private fun openSettingsScreen(action: String) {
        act.startActivity(Intent(action))
    }

    private fun globalNav(action: Int, okMsg: String) {
        if (NobitaService.instance == null) {
            say("पहले Accessibility सेटिंग में Nobita FF चालू कीजिए।")
            openSettingsScreen(Settings.ACTION_ACCESSIBILITY_SETTINGS)
            return
        }
        say(okMsg)
        act.window.decorView.postDelayed({ NobitaService.globalAction(action) }, 900)
    }

    // ---------- lock ----------

    private fun lockPhone() {
        globalNav(AccessibilityService.GLOBAL_ACTION_LOCK_SCREEN, "फ़ोन लॉक कर रहा हूँ।")
    }

    // ---------- system buttons ----------

    private fun trySystemButtons(t: String): Boolean {
        when {
            has(t, "screenshot", "स्क्रीनशॉट", "स्क्रीन शॉट", "screen shot") ->
                globalNav(AccessibilityService.GLOBAL_ACTION_TAKE_SCREENSHOT, "स्क्रीनशॉट ले रहा हूँ।")
            has(t, "go home", "home screen", "होम स्क्रीन", "होम पर", "होम जाओ", "ghar jao") ->
                globalNav(AccessibilityService.GLOBAL_ACTION_HOME, "होम स्क्रीन पर जा रहा हूँ।")
            t == "home" || t == "होम" ->
                globalNav(AccessibilityService.GLOBAL_ACTION_HOME, "होम स्क्रीन पर जा रहा हूँ।")
            has(t, "go back", "पीछे जाओ", "वापस जाओ", "बैक", "peeche", "piche") || t == "back" ->
                globalNav(AccessibilityService.GLOBAL_ACTION_BACK, "पीछे जा रहा हूँ।")
            has(t, "recent", "रीसेंट", "रिसेंट") ->
                globalNav(AccessibilityService.GLOBAL_ACTION_RECENTS, "हाल के ऐप दिखा रहा हूँ।")
            has(t, "notification", "नोटिफिकेशन", "नोटिफ़िकेशन") ->
                globalNav(AccessibilityService.GLOBAL_ACTION_NOTIFICATIONS, "नोटिफिकेशन खोल रहा हूँ।")
            has(t, "quick settings", "क्विक सेटिंग") ->
                globalNav(AccessibilityService.GLOBAL_ACTION_QUICK_SETTINGS, "क्विक सेटिंग खोल रहा हूँ।")
            else -> return false
        }
        return true
    }

    // ---------- settings panels ----------

    private fun trySettingsPanels(t: String): Boolean {
        val action: String
        val msg: String
        when {
            has(t, "wifi", "wi fi", "वाईफाई", "वाइफाई", "वाई फाई", "वाई-फाई", "इंटरनेट", "internet") -> {
                action = Settings.Panel.ACTION_INTERNET_CONNECTIVITY
                msg = "इंटरनेट की सेटिंग खोल रहा हूँ। Android ऐप को सीधे वाई-फाई चालू या बंद करने नहीं देता, यहाँ से आप कर सकते हैं।"
            }
            has(t, "bluetooth", "ब्लूटूथ", "ब्लूटुथ") -> {
                action = Settings.ACTION_BLUETOOTH_SETTINGS
                msg = "ब्लूटूथ सेटिंग खोल रहा हूँ।"
            }
            has(t, "hotspot", "हॉटस्पॉट", "हॉट स्पॉट") -> {
                action = "android.settings.TETHER_SETTINGS"
                msg = "हॉटस्पॉट सेटिंग खोल रहा हूँ।"
            }
            has(t, "airplane", "flight mode", "एयरप्लेन", "फ्लाइट मोड") -> {
                action = Settings.ACTION_AIRPLANE_MODE_SETTINGS
                msg = "एयरप्लेन मोड की सेटिंग खोल रहा हूँ।"
            }
            has(t, "location", "लोकेशन") -> {
                action = Settings.ACTION_LOCATION_SOURCE_SETTINGS
                msg = "लोकेशन सेटिंग खोल रहा हूँ।"
            }
            has(t, "brightness", "ब्राइटनेस") -> {
                action = Settings.ACTION_DISPLAY_SETTINGS
                msg = "डिस्प्ले सेटिंग खोल रहा हूँ।"
            }
            else -> return false
        }
        say(msg)
        openSettingsScreen(action)
        return true
    }

    // ---------- torch / volume ----------

    private fun torch(on: Boolean) {
        val cm = act.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val id = cm.cameraIdList.firstOrNull {
            cm.getCameraCharacteristics(it).get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
        }
        if (id == null) {
            say("इस फ़ोन में टॉर्च नहीं मिली।")
            return
        }
        cm.setTorchMode(id, on)
        say(if (on) "टॉर्च चालू कर दी।" else "टॉर्च बंद कर दी।")
    }

    private fun volume(t: String) {
        val am = act.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val stream = AudioManager.STREAM_MUSIC
        when {
            has(t, "full", "फुल", "max", "मैक्स", "पूरी") -> {
                am.setStreamVolume(stream, am.getStreamMaxVolume(stream), AudioManager.FLAG_SHOW_UI)
                say("वॉल्यूम फुल कर दिया।")
            }
            has(t, "mute", "म्यूट", "zero", "जीरो", "बंद", "band") -> {
                am.setStreamVolume(stream, 0, AudioManager.FLAG_SHOW_UI)
                say("आवाज़ बंद कर दी।")
            }
            has(t, "kam", "कम", "down", "घटा", "ghata", "decrease", "low", "धीमा", "dheema") -> {
                repeat(3) { am.adjustStreamVolume(stream, AudioManager.ADJUST_LOWER, AudioManager.FLAG_SHOW_UI) }
                say("वॉल्यूम कम कर दिया।")
            }
            has(t, "badha", "बढ़ा", "बढा", "up", "zyada", "ज्यादा", "ज़्यादा", "increase", "तेज", "tez", "high") -> {
                repeat(3) { am.adjustStreamVolume(stream, AudioManager.ADJUST_RAISE, AudioManager.FLAG_SHOW_UI) }
                say("वॉल्यूम बढ़ा दिया।")
            }
            else -> {
                am.adjustStreamVolume(stream, AudioManager.ADJUST_SAME, AudioManager.FLAG_SHOW_UI)
                say("वॉल्यूम बढ़ाना है या कम करना है?")
            }
        }
    }

    // ---------- time / date ----------

    private fun tellTime() {
        val c = Calendar.getInstance()
        val h24 = c.get(Calendar.HOUR_OF_DAY)
        val min = c.get(Calendar.MINUTE)
        val period = when (h24) {
            in 4..11 -> "सुबह"
            in 12..15 -> "दोपहर"
            in 16..19 -> "शाम"
            else -> "रात"
        }
        val h12 = if (h24 % 12 == 0) 12 else h24 % 12
        say("अभी $period के $h12 बजकर $min मिनट हुए हैं।")
    }

    private fun tellDate() {
        val f = SimpleDateFormat("d MMMM yyyy, EEEE", Locale("hi", "IN"))
        say("आज " + f.format(Date()) + " है।")
    }

    // ---------- contacts ----------

    private fun loadContacts(): List<Contact> {
        if (act.checkSelfPermission(Manifest.permission.READ_CONTACTS) != PackageManager.PERMISSION_GRANTED) {
            return emptyList()
        }
        val list = ArrayList<Contact>()
        val cursor = act.contentResolver.query(
            ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
            arrayOf(
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                ContactsContract.CommonDataKinds.Phone.NUMBER
            ),
            null, null, null
        )
        cursor?.use { c ->
            while (c.moveToNext()) {
                val n = c.getString(0)
                val p = c.getString(1)
                if (n != null && p != null) list.add(Contact(n, p))
            }
        }
        return list
    }

    private fun findContact(spoken: List<String>): Contact? {
        val contacts = loadContacts()
        if (contacts.isEmpty()) return null
        val full = Translit.skeleton(spoken.joinToString(""))
        val toks = spoken.map { Translit.skeleton(it) }.filter { it.isNotEmpty() }
        var best: Contact? = null
        var bestScore = 0
        for (c in contacts) {
            val cFull = Translit.skeleton(c.name)
            val cToks = c.name.split(" ", "-", "_")
                .filter { it.isNotBlank() }
                .map { Translit.skeleton(it) }
                .filter { it.isNotEmpty() }
            var score = 0
            if (cFull.isNotEmpty() && cFull == full) score += 100
            for (tk in toks) {
                if (cToks.contains(tk)) {
                    score += 10
                } else if (tk.length >= 2 && cToks.any { it.length >= 2 && (it.startsWith(tk) || tk.startsWith(it)) }) {
                    score += 4
                }
            }
            if (score > bestScore) {
                bestScore = score
                best = c
            }
        }
        return best
    }

    private fun contactsPermissionOk(): Boolean {
        if (act.checkSelfPermission(Manifest.permission.READ_CONTACTS) == PackageManager.PERMISSION_GRANTED) return true
        say("कॉन्टैक्ट देखने की अनुमति चाहिए। ऐप की सेटिंग में Contacts की अनुमति दे दीजिए।")
        act.requestPermissions(arrayOf(Manifest.permission.READ_CONTACTS), 2)
        return false
    }

    // ---------- WhatsApp ----------

    private val nameStop = setOf(
        "mere", "मेरे", "meri", "मेरी", "mera", "मेरा", "dost", "दोस्त", "friend", "ke", "के", "ka", "का",
        "ko", "को", "send", "bhejo", "भेजो", "message", "मैसेज", "मेसेज", "msg", "ji", "जी", "ek", "एक",
        "ye", "ये", "wo", "वो", "usko", "उसको", "unko", "उनको", "se", "से",
        "pe", "par", "पर", "पे", "me", "mein", "में"
    )

    private val msgLeadFill = setOf(
        "par", "pe", "पर", "पे", "me", "mein", "में", "message", "मैसेज", "मेसेज", "msg", "ki", "की", "कि",
        "ye", "ये", "kaho", "कहो", "bolo", "बोलो", "likho", "लिखो", "bhejo", "भेजो", "send", "ke", "के", "liye", "लिए",
        "karo", "करो", "ki", "that"
    )

    private val msgTailVerbs = setOf(
        "bhejo", "भेजो", "bhej", "भेज", "do", "दो", "dena", "देना", "de", "दे", "karo", "करो", "kar", "कर",
        "likho", "लिखो", "send", "bolo", "बोलो", "kaho", "कहो", "please", "plz", "प्लीज", "na", "न",
        "bhijwao", "भिजवाओ", "dijiye", "दीजिए", "kijiye", "कीजिए"
    )

    private val msgSeparators = setOf("message", "मैसेज", "मेसेज", "msg", "bolo", "बोलो", "kaho", "कहो", "likho", "लिखो")

    private fun tryWhatsApp(t: String): Boolean {
        if (!t.contains("whatsapp")) return false
        val toks = tokens(t)
        val wi = toks.indexOf("whatsapp")
        if (wi < 0) return false
        val before = toks.subList(0, wi).toMutableList()
        val after = toks.subList(wi + 1, toks.size).toMutableList()

        val nameToks: MutableList<String>
        val msgToks: MutableList<String>

        if (before.isNotEmpty() && (before.last() == "ko" || before.last() == "को")) {
            // "Rahul ko whatsapp pe hello bhejo"
            before.removeAt(before.size - 1)
            nameToks = before
            msgToks = after
        } else {
            val sep = after.indexOfFirst { it in msgSeparators }
            val koIdx = after.indexOfFirst { it == "ko" || it == "को" }
            if (koIdx > 0 && (sep <= 0 || koIdx < sep)) {
                // "whatsapp pe Rahul ko hello bhejo"
                nameToks = after.subList(0, koIdx).toMutableList()
                msgToks = after.subList(koIdx + 1, after.size).toMutableList()
            } else if (sep > 0) {
                // "whatsapp Rahul message hello"
                nameToks = after.subList(0, sep).toMutableList()
                msgToks = after.subList(sep + 1, after.size).toMutableList()
            } else {
                return false
            }
        }

        val cleanName = nameToks.filter { it !in nameStop }
        while (msgToks.isNotEmpty() && msgToks.first() in msgLeadFill) msgToks.removeAt(0)
        while (msgToks.isNotEmpty() && msgToks.last() in msgTailVerbs) msgToks.removeAt(msgToks.size - 1)
        val message = msgToks.joinToString(" ").trim()

        if (cleanName.isEmpty()) {
            say("किसको मैसेज भेजना है? ऐसे बोलिए: राहुल को व्हाट्सएप पर हेलो भेजो।")
            return true
        }
        if (message.isEmpty()) {
            say("क्या मैसेज भेजना है? ऐसे बोलिए: राहुल को व्हाट्सएप पर हेलो भेजो।")
            return true
        }
        if (!contactsPermissionOk()) return true

        val contact = findContact(cleanName)
        if (contact == null) {
            say("${cleanName.joinToString(" ")} नाम का कॉन्टैक्ट नहीं मिला।")
            return true
        }

        var phone = contact.number.filter { it.isDigit() }
        if (phone.length == 10) phone = "91$phone"
        if (phone.length == 11 && phone.startsWith("0")) phone = "91" + phone.substring(1)

        val uri = Uri.parse("https://api.whatsapp.com/send?phone=$phone&text=" + Uri.encode(message))
        val serviceOn = NobitaService.instance != null
        if (serviceOn) NobitaService.markPendingSend()

        var launched = false
        for (pkg in listOf("com.whatsapp", "com.whatsapp.w4b")) {
            try {
                act.startActivity(Intent(Intent.ACTION_VIEW, uri).setPackage(pkg))
                launched = true
                break
            } catch (e: Exception) {
                // agla package try karo
            }
        }
        if (!launched) {
            NobitaService.pendingSendUntil = 0L
            say("WhatsApp नहीं मिला। क्या यह फ़ोन में इंस्टॉल है?")
            return true
        }
        if (serviceOn) {
            say("${contact.name} को मैसेज भेज रहा हूँ।")
        } else {
            say("${contact.name} का चैट खोल दिया है। अपने आप भेजने के लिए Accessibility में Nobita FF चालू कीजिए, अभी सेंड दबा दीजिए।")
        }
        return true
    }

    // ---------- call ----------

    private val callWords = setOf(
        "call", "कॉल", "dial", "डायल", "phone", "फोन", "फ़ोन", "lagao", "लगाओ", "laga", "लगा", "milao", "मिलाओ",
        "number", "नंबर", "नम्बर", "karo", "करो", "kar", "कर", "do", "दो", "ko", "को", "dost", "दोस्त",
        "mere", "मेरे", "ek", "एक", "pe", "par", "पर", "please", "plz", "प्लीज", "ji", "जी", "ke", "के"
    )

    private fun tryCall(t: String): Boolean {
        if (!has(t, "call", "कॉल", "फोन करो", "फ़ोन करो", "phone karo", "फोन लगाओ", "phone lagao", "dial", "डायल")) return false
        val rest = tokens(t).filter { it !in callWords }
        val digits = rest.joinToString("").filter { it.isDigit() }
        if (digits.length >= 6) {
            say("$digits पर कॉल कर रहा हूँ।")
            placeCall(digits)
            return true
        }
        if (rest.isEmpty()) {
            say("किसको कॉल करना है?")
            return true
        }
        if (!contactsPermissionOk()) return true
        val contact = findContact(rest)
        if (contact == null) {
            say("${rest.joinToString(" ")} नाम का कॉन्टैक्ट नहीं मिला।")
            return true
        }
        say("${contact.name} को कॉल कर रहा हूँ।")
        placeCall(contact.number)
        return true
    }

    private fun placeCall(number: String) {
        val uri = Uri.fromParts("tel", number, null)
        if (act.checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
            act.startActivity(Intent(Intent.ACTION_CALL, uri))
        } else {
            act.startActivity(Intent(Intent.ACTION_DIAL, uri))
        }
    }

    // ---------- alarm / timer ----------

    private fun findNumber(t: String): Int? {
        val m = Regex("\\d+").find(t)
        if (m != null) return m.value.toInt()
        for (tok in tokens(t)) {
            val v = numberWords[tok]
            if (v != null) return v
        }
        return null
    }

    private fun tryAlarmOrTimer(t: String): Boolean {
        if (has(t, "timer", "टाइमर")) {
            val n = findNumber(t)
            if (n == null) {
                say("कितने समय का टाइमर लगाना है?")
                return true
            }
            val seconds = when {
                has(t, "second", "सेकंड", "सेकण्ड", "sec") -> n
                has(t, "hour", "घंटा", "घंटे", "ghante", "ghanta") -> n * 3600
                else -> n * 60
            }
            val i = Intent(AlarmClock.ACTION_SET_TIMER)
                .putExtra(AlarmClock.EXTRA_LENGTH, seconds)
                .putExtra(AlarmClock.EXTRA_MESSAGE, "Nobita")
                .putExtra(AlarmClock.EXTRA_SKIP_UI, true)
            act.startActivity(i)
            say("टाइमर लगा दिया।")
            return true
        }
        if (has(t, "alarm", "अलार्म", "अलारम")) {
            var hour: Int
            var minute = 0
            val m = Regex("(\\d{1,2})(?:[: ](\\d{2}))?\\b").find(t)
            if (m != null) {
                hour = m.groupValues[1].toInt()
                if (m.groupValues[2].isNotEmpty()) minute = m.groupValues[2].toInt()
            } else {
                val w = tokens(t).firstNotNullOfOrNull { numberWords[it] }
                if (w == null) {
                    say("किस समय का अलार्म लगाना है? जैसे: सुबह 7 बजे का अलार्म लगाओ।")
                    return true
                }
                hour = w
            }
            if (hour > 23 || minute > 59) {
                say("समय सही नहीं लगा, फिर से बोलिए।")
                return true
            }
            val pm = hasWord(t, "pm") || Regex("\\dpm").containsMatchIn(t) ||
                has(t, "शाम", "रात", "दोपहर", "dopahar", "sham", "raat", "evening", "night", "afternoon")
            val am = hasWord(t, "am") || Regex("\\dam").containsMatchIn(t) ||
                has(t, "सुबह", "subah", "morning")
            if (pm && hour in 1..11) hour += 12
            if (am && hour == 12) hour = 0
            val i = Intent(AlarmClock.ACTION_SET_ALARM)
                .putExtra(AlarmClock.EXTRA_HOUR, hour)
                .putExtra(AlarmClock.EXTRA_MINUTES, minute)
                .putExtra(AlarmClock.EXTRA_MESSAGE, "Nobita")
                .putExtra(AlarmClock.EXTRA_SKIP_UI, true)
            act.startActivity(i)
            say("अलार्म लगा दिया, " + String.format(Locale.US, "%02d:%02d", hour, minute) + " बजे के लिए।")
            return true
        }
        return false
    }

    // ---------- app kholna ----------

    private fun tryOpenApp(t: String): Boolean {
        val strong = openVerbsStrong.firstOrNull { t.contains(it) }
        val weak = if (strong == null) openVerbsWeak.firstOrNull { t.contains(it) } else null
        val verb = strong ?: weak ?: return false

        var name = t
        for (v in openVerbsStrong + openVerbsWeak) name = name.replace(v, " ")
        val nameToks = tokens(name).filter { it !in fillWords }
        if (nameToks.isEmpty()) {
            if (strong != null) say("कौन सा ऐप खोलना है?")
            return strong != null
        }
        val query = nameToks.joinToString(" ")
        val pkg = findAppPackage(query)
        if (pkg == null) {
            if (verb == strong) {
                say("$query नाम का ऐप नहीं मिला।")
                return true
            }
            return false
        }
        val launch = act.packageManager.getLaunchIntentForPackage(pkg)
        if (launch == null) {
            say("$query खोल नहीं पाया।")
            return true
        }
        say("$query खोल रहा हूँ।")
        act.startActivity(launch)
        return true
    }

    private fun findAppPackage(spoken: String): String? {
        var q = spoken.lowercase(Locale.ROOT)
        for ((k, v) in appAliases.entries.sortedByDescending { it.key.length }) q = q.replace(k, v)
        q = q.trim()
        if (q.isEmpty()) return null
        val qSkel = Translit.skeleton(q)

        val pm = act.packageManager
        val main = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val apps = pm.queryIntentActivities(main, 0)
        var bestPkg: String? = null
        var bestScore = 0
        for (ri in apps) {
            val label = ri.loadLabel(pm).toString().lowercase(Locale.ROOT)
            val lSkel = Translit.skeleton(label)
            var score = 0
            if (label == q) score = 100
            else if (label.startsWith(q) || q.startsWith(label) && label.length >= 3) score = 60
            else if (label.contains(q) || q.contains(label) && label.length >= 3) score = 40
            else if (qSkel.isNotEmpty() && lSkel == qSkel) score = 45
            else if (qSkel.length >= 3 && lSkel.length >= 3 && (lSkel.contains(qSkel) || qSkel.contains(lSkel))) score = 20
            // Free Fire MAX ko normal Free Fire par tarjeeh na mile jab MAX bola gaya ho
            if (score > 0 && q.contains("max") && label.contains("max")) score += 5
            if (score > bestScore) {
                bestScore = score
                bestPkg = ri.activityInfo.packageName
            }
        }
        return bestPkg
    }

    // ---------- maps / music / search ----------

    private val mapWords = setOf(
        "navigate", "नेविगेट", "रास्ता", "directions", "दिखाओ", "dikhao", "batao", "बताओ", "map", "मैप", "नक्शा",
        "par", "pe", "पर", "पे", "ka", "का", "ke", "के", "liye", "लिए", "karo", "करो", "mujhe", "मुझे", "tak", "तक",
        "jane", "जाने", "jana", "जाना", "hai", "है", "chahiye", "चाहिए", "ko", "को"
    )

    private fun maps(t: String) {
        val q = tokens(t).filter { it !in mapWords }.joinToString(" ")
        if (q.isEmpty()) {
            say("कहाँ जाना है?")
            return
        }
        say("$q का रास्ता खोल रहा हूँ।")
        act.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("google.navigation:q=" + Uri.encode(q))))
    }

    private val musicWords = setOf(
        "youtube", "यूट्यूब", "यू", "ट्यूब", "play", "प्ले", "bajao", "बजाओ", "chalao", "चलाओ", "gana", "गाना", "gaana",
        "गाने", "gaane", "song", "सॉन्ग", "सोंग", "music", "म्यूजिक", "par", "pe", "पर", "पे", "ka", "का", "ke", "के",
        "ki", "की", "karo", "करो", "kholo", "खोलो", "search", "सर्च", "mere", "मेरे", "ek", "एक", "ko", "को", "se", "से",
        "लगाओ", "lagao", "सुनाओ", "sunao"
    )

    private fun music(t: String) {
        val q = tokens(t).filter { it !in musicWords }.joinToString(" ")
        if (q.isEmpty()) {
            say("क्या बजाना है? जैसे: यूट्यूब पर अरिजीत के गाने बजाओ।")
            return
        }
        say("यूट्यूब पर $q ढूंढ रहा हूँ।")
        try {
            act.startActivity(
                Intent(Intent.ACTION_SEARCH).setPackage("com.google.android.youtube").putExtra("query", q)
            )
        } catch (e: Exception) {
            act.startActivity(
                Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse("https://www.youtube.com/results?search_query=" + Uri.encode(q))
                )
            )
        }
    }

    private val searchWords = setOf(
        "search", "सर्च", "google", "गूगल", "par", "pe", "पर", "पे", "karo", "करो", "khojo", "खोजो", "dhundo",
        "ढूंढो", "ढूँढो", "kar", "कर", "do", "दो", "ke", "के", "baare", "बारे", "me", "mein", "में", "ki", "की", "ka", "का"
    )

    private fun webSearch(t: String) {
        val q = tokens(t).filter { it !in searchWords }.joinToString(" ")
        if (q.isEmpty()) {
            say("क्या सर्च करना है?")
            return
        }
        say("$q सर्च कर रहा हूँ।")
        act.startActivity(Intent(Intent.ACTION_WEB_SEARCH).putExtra(SearchManager.QUERY, q))
    }

    // ---------- Claude se jawab (optional) ----------

    private fun askClaude(q: String) {
        val key = prefs.getString("api_key", "") ?: ""
        if (key.isBlank()) {
            say("यह कमांड मुझे समझ नहीं आई। हर सवाल का जवाब पाने के लिए ऐप में Claude API Key डाल दीजिए।")
            return
        }
        Thread {
            try {
                val body = JSONObject()
                    .put("model", "claude-haiku-5-5")
                    .put("max_tokens", 300)
                    .put(
                        "system",
                        "You are Nobita, a friendly voice assistant on an Android phone. " +
                            "Reply in short, simple Hindi (Devanagari script), at most 3 sentences, no markdown, no emojis."
                    )
                    .put(
                        "messages",
                        JSONArray().put(JSONObject().put("role", "user").put("content", q))
                    )
                val conn = URL("https://api.anthropic.com/v1/messages").openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.setRequestProperty("x-api-key", key)
                conn.setRequestProperty("anthropic-version", "2023-06-01")
                conn.setRequestProperty("content-type", "application/json")
                conn.doOutput = true
                conn.connectTimeout = 15000
                conn.readTimeout = 30000
                conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
                val code = conn.responseCode
                val stream = if (code in 200..299) conn.inputStream else conn.errorStream
                val text = stream.bufferedReader(Charsets.UTF_8).use { it.readText() }
                if (code in 200..299) {
                    val ans = JSONObject(text).getJSONArray("content").getJSONObject(0).getString("text")
                    act.runOnUiThread { say(ans) }
                } else {
                    act.runOnUiThread { say("Claude से जवाब नहीं मिला। API Key जाँच लीजिए। कोड $code।") }
                }
            } catch (e: Exception) {
                act.runOnUiThread { say("इंटरनेट में कुछ दिक्कत है।") }
            }
        }.start()
    }
}
'''
FILES['app/src/main/java/com/nobita/ff/MainActivity.kt'] = r'''package com.nobita.ff

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import java.util.Locale

class MainActivity : Activity(), TextToSpeech.OnInitListener {

    private lateinit var tts: TextToSpeech
    private var ttsReady = false
    private var recognizer: SpeechRecognizer? = null
    private var listening = false
    private var continuous = false
    private var inForeground = false
    private val handler = Handler(Looper.getMainLooper())

    private lateinit var statusView: TextView
    private lateinit var logView: TextView
    private lateinit var scroll: ScrollView
    private lateinit var processor: CommandProcessor

    private val logLines = ArrayList<String>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        processor = CommandProcessor(this) { speak(it) }
        tts = TextToSpeech(this, this)
        requestPermissions(
            arrayOf(
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.READ_CONTACTS,
                Manifest.permission.CALL_PHONE
            ),
            1
        )
    }

    override fun onResume() {
        super.onResume()
        inForeground = true
        refreshStatus()
        if (continuous) handler.postDelayed({ startListening() }, 600)
    }

    override fun onPause() {
        super.onPause()
        inForeground = false
        handler.removeCallbacksAndMessages(null)
        recognizer?.cancel()
        listening = false
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
        recognizer?.destroy()
        if (::tts.isInitialized) {
            tts.stop()
            tts.shutdown()
        }
    }

    // ---------- awaaz bolna (TTS) ----------

    override fun onInit(status: Int) {
        if (status != TextToSpeech.SUCCESS) {
            addLog("(आवाज़ वाला इंजन चालू नहीं हो पाया)")
            return
        }
        val r = tts.setLanguage(Locale("hi", "IN"))
        if (r == TextToSpeech.LANG_MISSING_DATA || r == TextToSpeech.LANG_NOT_SUPPORTED) {
            tts.setLanguage(Locale.US)
            addLog("(हिंदी आवाज़ नहीं मिली। Google Text-to-speech में हिंदी वॉइस डाउनलोड कर लीजिए)")
        }
        tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) {
                runOnUiThread { afterSpeech() }
            }

            @Deprecated("Deprecated in Java")
            override fun onError(utteranceId: String?) {
                runOnUiThread { afterSpeech() }
            }
        })
        ttsReady = true
        speak("नमस्ते, मैं नोबिता हूँ। बोलिए, मैं क्या करूँ?")
    }

    private fun speak(text: String) {
        runOnUiThread {
            addLog("नोबिता: $text")
            if (ttsReady) {
                tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "nobita")
            } else {
                afterSpeech()
            }
        }
    }

    private fun afterSpeech() {
        if (continuous && inForeground) {
            handler.postDelayed({ startListening() }, 300)
        }
    }

    // ---------- sunna (Speech-to-text) ----------

    private val listener = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {
            setStatus("सुन रहा हूँ…")
        }

        override fun onBeginningOfSpeech() {}
        override fun onRmsChanged(rmsdB: Float) {}
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() {
            setStatus("समझ रहा हूँ…")
        }

        override fun onError(error: Int) {
            listening = false
            refreshStatus()
            val retry = error == SpeechRecognizer.ERROR_NO_MATCH ||
                error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT ||
                error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY
            if (continuous && inForeground && retry) {
                handler.postDelayed({ startListening() }, 600)
            } else if (error != SpeechRecognizer.ERROR_CLIENT) {
                addLog("(सुनने में दिक्कत, कोड $error)")
            }
        }

        override fun onResults(results: Bundle?) {
            listening = false
            refreshStatus()
            val text = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
            if (text.isNullOrBlank()) {
                afterSpeech()
                return
            }
            addLog("आप: $text")
            onHeard(text)
        }

        override fun onPartialResults(partialResults: Bundle?) {}
        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

    private fun onHeard(text: String) {
        val low = text.lowercase(Locale.ROOT)
        if (low.contains("stop listening") || low.contains("सुनना बंद") || low.contains("sunna band") ||
            low.contains("अलविदा") || low.contains("bye")
        ) {
            continuous = false
            findViewById<Switch>(SWITCH_ID)?.isChecked = false
            speak("ठीक है, अब मैं नहीं सुन रहा। फिर मिलेंगे।")
            return
        }
        processor.handle(text)
    }

    private fun startListening() {
        if (listening) return
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 1)
            Toast.makeText(this, "माइक की अनुमति दीजिए", Toast.LENGTH_SHORT).show()
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            addLog("(इस फ़ोन में Google की वॉइस सर्विस नहीं मिली)")
            return
        }
        if (recognizer == null) {
            recognizer = SpeechRecognizer.createSpeechRecognizer(this)
            recognizer?.setRecognitionListener(listener)
        }
        val i = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, packageName)
        }
        listening = true
        recognizer?.startListening(i)
    }

    // ---------- screen ----------

    private val SWITCH_ID = 7001

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

    private fun roundBg(color: String, radiusDp: Int): GradientDrawable =
        GradientDrawable().apply {
            cornerRadius = dp(radiusDp).toFloat()
            setColor(Color.parseColor(color))
        }

    private fun smallButton(label: String, onClick: () -> Unit): Button =
        Button(this).apply {
            text = label
            textSize = 13f
            isAllCaps = false
            setTextColor(Color.WHITE)
            background = roundBg("#21262D", 12)
            setOnClickListener { onClick() }
            layoutParams = LinearLayout.LayoutParams(0, dp(48), 1f).apply {
                marginStart = dp(4)
                marginEnd = dp(4)
            }
        }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#0D1117"))
            setPadding(dp(20), dp(36), dp(20), dp(16))
            gravity = Gravity.CENTER_HORIZONTAL
        }

        val title = TextView(this).apply {
            text = "NOBITA FF"
            textSize = 32f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#FFC107"))
            gravity = Gravity.CENTER
        }
        root.addView(title, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        val sub = TextView(this).apply {
            text = "आपका वॉइस असिस्टेंट"
            textSize = 14f
            setTextColor(Color.parseColor("#8B949E"))
            gravity = Gravity.CENTER
        }
        root.addView(sub, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        statusView = TextView(this).apply {
            textSize = 14f
            setTextColor(Color.parseColor("#58A6FF"))
            gravity = Gravity.CENTER
            setPadding(0, dp(12), 0, dp(12))
        }
        root.addView(statusView, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        val mic = Button(this).apply {
            text = "🎤  बोलिए"
            textSize = 20f
            isAllCaps = false
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#0D1117"))
            background = roundBg("#FFC107", 20)
            setOnClickListener { startListening() }
        }
        root.addView(mic, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(72)))

        val sw = Switch(this).apply {
            id = SWITCH_ID
            text = "लगातार सुनो (ऐप खुला रहे)"
            setTextColor(Color.WHITE)
            setPadding(0, dp(14), 0, dp(14))
            setOnCheckedChangeListener { _, checked ->
                continuous = checked
                if (checked) startListening() else recognizer?.cancel()
                if (!checked) listening = false
            }
        }
        root.addView(sw, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        scroll = ScrollView(this).apply {
            background = roundBg("#161B22", 12)
            setPadding(dp(12), dp(10), dp(12), dp(10))
        }
        logView = TextView(this).apply {
            textSize = 15f
            setTextColor(Color.parseColor("#E6EDF3"))
            setLineSpacing(0f, 1.15f)
        }
        scroll.addView(logView)
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, dp(12), 0, 0)
        }
        row.addView(smallButton("Accessibility") {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        })
        row.addView(smallButton("API Key") { showApiKeyDialog() })
        row.addView(smallButton("Commands") { showCommands() })
        root.addView(row, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        setContentView(root)
        refreshStatus()
    }

    private fun setStatus(s: String) {
        runOnUiThread { statusView.text = s }
    }

    private fun refreshStatus() {
        val acc = if (NobitaService.instance != null) "Accessibility: चालू ✅" else "Accessibility: बंद ❌ (लॉक और WhatsApp के लिए चालू करें)"
        val mode = if (listening) "सुन रहा हूँ…" else "तैयार"
        setStatus("$mode\n$acc")
    }

    private fun addLog(line: String) {
        runOnUiThread {
            logLines.add(line)
            while (logLines.size > 40) logLines.removeAt(0)
            logView.text = logLines.joinToString("\n\n")
            scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
        }
    }

    private fun showApiKeyDialog() {
        val prefs = getSharedPreferences("nobita", Context.MODE_PRIVATE)
        val input = EditText(this).apply {
            hint = "sk-ant-..."
            setText(prefs.getString("api_key", ""))
            setSingleLine(true)
        }
        AlertDialog.Builder(this)
            .setTitle("Claude API Key (ज़रूरी नहीं)")
            .setMessage("यह सिर्फ़ तब चाहिए जब आप Nobita से हर तरह के सवाल पूछना चाहें। बाकी सारे कमांड बिना Key के चलते हैं। Key आपके फ़ोन में ही रहती है।")
            .setView(input)
            .setPositiveButton("सेव") { _, _ ->
                prefs.edit().putString("api_key", input.text.toString().trim()).apply()
                Toast.makeText(this, "सेव हो गया", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("रद्द", null)
            .show()
    }

    private fun showCommands() {
        val msg = "• फ़ोन लॉक करो\n" +
            "• राहुल को व्हाट्सएप पर हेलो भेजो\n" +
            "• मम्मी को कॉल करो\n" +
            "• यूट्यूब खोलो / फ्री फायर खोलो\n" +
            "• सुबह 7 बजे का अलार्म लगाओ\n" +
            "• 5 मिनट का टाइमर लगाओ\n" +
            "• टॉर्च चालू करो / बंद करो\n" +
            "• वॉल्यूम बढ़ाओ / कम करो / म्यूट\n" +
            "• स्क्रीनशॉट लो, होम, पीछे जाओ\n" +
            "• वाईफाई / ब्लूटूथ (सेटिंग खुलती है)\n" +
            "• कितने बजे हैं / आज की तारीख\n" +
            "• यूट्यूब पर अरिजीत के गाने बजाओ\n" +
            "• गूगल पर ... सर्च करो\n" +
            "• ... का रास्ता दिखाओ\n" +
            "• बाकी कुछ भी पूछो (Claude API Key चाहिए)\n\n" +
            "रोकने के लिए: \"सुनना बंद\" बोलिए।"
        AlertDialog.Builder(this)
            .setTitle("क्या-क्या बोल सकते हैं")
            .setMessage(msg)
            .setPositiveButton("ठीक है", null)
            .show()
    }
}
'''
FILES['app/src/main/java/com/nobita/ff/NobitaService.kt'] = r'''package com.nobita.ff

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

/**
 * Accessibility Service:
 *  1) Phone lock / home / back / screenshot jaise global actions karta hai.
 *  2) WhatsApp me jab Nobita ne message taiyaar kiya ho, tab "Send" button dabata hai.
 * Ye sirf WhatsApp ki screen dekhta hai (accessibility_config.xml me packageNames).
 */
class NobitaService : AccessibilityService() {

    companion object {
        @Volatile
        var instance: NobitaService? = null

        @Volatile
        var pendingSendUntil: Long = 0L

        fun markPendingSend() {
            pendingSendUntil = System.currentTimeMillis() + 25_000L
        }

        fun globalAction(action: Int): Boolean {
            return instance?.performGlobalAction(action) ?: false
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onUnbind(intent: Intent?): Boolean {
        instance = null
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        instance = null
        super.onDestroy()
    }

    override fun onInterrupt() {}

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        if (System.currentTimeMillis() > pendingSendUntil) return
        val pkg = event.packageName?.toString() ?: return
        if (pkg != "com.whatsapp" && pkg != "com.whatsapp.w4b") return
        val root = rootInActiveWindow ?: return
        val node = findSendButton(root) ?: return
        if (clickNode(node)) {
            pendingSendUntil = 0L
        }
    }

    private fun findSendButton(root: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        val byId = root.findAccessibilityNodeInfosByViewId(root.packageName.toString() + ":id/send")
        if (!byId.isNullOrEmpty()) return byId[0]
        return findByDescription(root, 0)
    }

    private fun findByDescription(node: AccessibilityNodeInfo?, depth: Int): AccessibilityNodeInfo? {
        if (node == null || depth > 25) return null
        val d = node.contentDescription?.toString()?.trim()?.lowercase()
        if (d != null && (d == "send" || d == "भेजें" || d == "भेजे")) return node
        for (i in 0 until node.childCount) {
            val r = findByDescription(node.getChild(i), depth + 1)
            if (r != null) return r
        }
        return null
    }

    private fun clickNode(node: AccessibilityNodeInfo): Boolean {
        var n: AccessibilityNodeInfo? = node
        while (n != null) {
            if (n.isClickable) {
                return n.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            }
            n = n.parent
        }
        return false
    }
}
'''
FILES['app/src/main/java/com/nobita/ff/Translit.kt'] = r'''package com.nobita.ff

/**
 * Hindi (Devanagari) aur English naam ko ek "skeleton" me badalta hai taaki
 * "राहुल" aur "Rahul" ek jaise match ho sakein.
 */
object Translit {
    private val map: Map<Char, String> = mapOf(
        'क' to "k", 'ख' to "k", 'ग' to "g", 'घ' to "g", 'ङ' to "n",
        'च' to "c", 'छ' to "c", 'ज' to "j", 'झ' to "j", 'ञ' to "n",
        'ट' to "t", 'ठ' to "t", 'ड' to "d", 'ढ' to "d", 'ण' to "n",
        'त' to "t", 'थ' to "t", 'द' to "d", 'ध' to "d", 'न' to "n",
        'प' to "p", 'फ' to "f", 'ब' to "b", 'भ' to "b", 'म' to "m",
        'य' to "y", 'र' to "r", 'ल' to "l", 'व' to "v", 'श' to "s",
        'ष' to "s", 'स' to "s", 'ळ' to "l", 'ं' to "n", 'ँ' to "n",
        'क़' to "k", 'ख़' to "k", 'ग़' to "g", 'ज़' to "j",
        'ड़' to "r", 'ढ़' to "r", 'फ़' to "f", 'य़' to "y"
    )
    private val dupRegex = Regex("(.)\\1+")
    private val vowelRegex = Regex("[aeiou]")

    fun skeleton(input: String): String {
        val sb = StringBuilder()
        for (ch in input.lowercase()) {
            val m = map[ch]
            if (m != null) {
                sb.append(m)
            } else if (ch in 'a'..'z') {
                sb.append(ch)
            }
        }
        var t = sb.toString()
        t = t.replace("ph", "f").replace("sh", "s").replace("ch", "c")
        t = t.replace("h", "").replace("w", "v").replace("z", "j").replace("q", "k").replace("x", "ks")
        t = vowelRegex.replace(t, "")
        t = dupRegex.replace(t, "\$1")
        return t
    }
}
'''
FILES['app/src/main/res/drawable/ic_launcher.xml'] = r'''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#FFC107"
        android:pathData="M0,0h108v108h-108z" />
    <path
        android:fillColor="#212121"
        android:pathData="M54,28a11,11 0 0,1 11,11v16a11,11 0 0,1 -22,0v-16a11,11 0 0,1 11,-11z" />
    <path
        android:fillColor="#00000000"
        android:strokeColor="#212121"
        android:strokeWidth="4"
        android:pathData="M39,52v3a15,15 0 0,0 30,0v-3" />
    <path
        android:fillColor="#00000000"
        android:strokeColor="#212121"
        android:strokeWidth="4"
        android:pathData="M54,70v12M44,82h20" />
</vector>
'''
FILES['app/src/main/res/values/strings.xml'] = r'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Nobita FF</string>
    <string name="service_label">Nobita FF Assistant</string>
    <string name="accessibility_desc">Nobita FF आपकी आवाज़ से फ़ोन लॉक करने, होम/बैक जैसे बटन दबाने और WhatsApp मैसेज भेजने में मदद करता है। यह सिर्फ़ WhatsApp की स्क्रीन देखता है, और किसी की जानकारी कहीं नहीं भेजता।</string>
</resources>
'''
FILES['app/src/main/res/xml/accessibility_config.xml'] = r'''<?xml version="1.0" encoding="utf-8"?>
<accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:description="@string/accessibility_desc"
    android:accessibilityEventTypes="typeWindowStateChanged|typeWindowContentChanged"
    android:accessibilityFeedbackType="feedbackGeneric"
    android:accessibilityFlags="flagReportViewIds|flagRetrieveInteractiveWindows"
    android:canRetrieveWindowContent="true"
    android:notificationTimeout="200"
    android:packageNames="com.whatsapp,com.whatsapp.w4b" />
'''
FILES['build.gradle.kts'] = r'''plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
}
'''
FILES['gradle.properties'] = r'''org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.nonTransitiveRClass=true
kotlin.code.style=official
'''
FILES['settings.gradle.kts'] = r'''pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "NobitaFF"
include(":app")
'''

for path, content in FILES.items():
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
print('Project files ban gayi:', len(FILES))
