# Release builds are shrunk by R8. shared_preferences_android 2.5.x reaches its Kotlin code
# through JNI by method name, and R8 removed SharedPreferencesApiRegistrar.getAll, so the
# release APK failed with NoSuchMethodError (seen on the emulator, 2026-10-19). Keep the
# plugin and the JNI bridge classes as they are.
-keep class io.flutter.plugins.sharedpreferences.** { *; }
-keep class com.github.dart_lang.jni.** { *; }
-keep class kotlin.coroutines.** { *; }
