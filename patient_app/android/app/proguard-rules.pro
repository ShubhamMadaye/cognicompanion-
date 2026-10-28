# Flutter Proguard / R8 Rules for Production Builds

# Flutter Engine Keep Rules
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.**  { *; }
-keep class io.flutter.util.**  { *; }
-keep class io.flutter.view.**  { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.**  { *; }

# Keep Flutter TTS native JNI and engine bindings
-keep class com.tundralabs.fluttertts.** { *; }
-dontwarn com.tundralabs.fluttertts.**
-keep class android.speech.tts.** { *; }

# Keep Speech To Text native bindings and recognition service
-keep class com.csdcorp.speech_to_text.** { *; }
-dontwarn com.csdcorp.speech_to_text.**
-keep class android.speech.** { *; }

# Keep Shared Preferences
-keep class io.flutter.plugins.sharedpreferences.** { *; }

# Keep URL Launcher
-keep class io.flutter.plugins.urllauncher.** { *; }

# Keep standard models and JSON annotations
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}
-keepattributes *Annotation*,Signature,InnerClasses,EnclosingMethod

# Allow obfuscation of non-public API
-dontobfuscate
-dontwarn okhttp3.**
-dontwarn okio.**
-dontwarn com.google.android.play.core.**

