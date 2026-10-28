# Moshi
-keepclassmembers class * {
    @com.squareup.moshi.FromJson *;
    @com.squareup.moshi.ToJson *;
}
-keep class com.cognicompanion.patient.data.model.** { *; }

# Retrofit
-keepattributes Signature
-keepattributes *Annotation*
-keep class retrofit2.** { *; }
-keepclassmembers class * {
    @retrofit2.http.* <methods>;
}

# OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**

# Hilt
-keep class dagger.hilt.** { *; }
-keep class javax.inject.** { *; }

# Retrofit/Moshi model adapters are generated and referenced reflectively by Moshi.
-keep class com.cognicompanion.patient.data.model.**JsonAdapter { *; }
-keep class com.cognicompanion.patient.data.model.** { *; }
