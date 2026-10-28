package com.cognicompanion.patient.di

import android.content.Context
import androidx.room.Room
import com.cognicompanion.patient.BuildConfig
import com.cognicompanion.patient.data.local.AppDatabase
import com.cognicompanion.patient.data.local.PendingMedLogDao
import com.cognicompanion.patient.data.local.TimelineCacheDao
import com.cognicompanion.patient.data.remote.CogniCompanionApi
import com.cognicompanion.patient.data.remote.TokenStore
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.runBlocking
import okhttp3.Authenticator
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideMoshi(): Moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    @Provides
    @Singleton
    fun provideOkHttpClient(tokenStore: TokenStore): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.ENABLE_HTTP_LOGGING)
                HttpLoggingInterceptor.Level.BODY
            else
                HttpLoggingInterceptor.Level.NONE
        }

        // Authenticator: handles 401 → token refresh → retry once
        val authenticator = Authenticator { _, response ->
            // Prevent infinite loops: don't retry if refresh itself 401s
            if (response.request.header("X-Retry-After-Refresh") != null) return@Authenticator null

            val refreshToken = runBlocking { tokenStore.getRefreshToken() }
                ?: return@Authenticator null

            // Build a one-shot Retrofit just for the refresh call to avoid circular dep
            val refreshMoshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
            val refreshClient = OkHttpClient.Builder().build()
            val refreshRetrofit = Retrofit.Builder()
                .baseUrl(runBlocking { tokenStore.getBaseUrl() } ?: BuildConfig.BASE_URL)
                .client(refreshClient)
                .addConverterFactory(MoshiConverterFactory.create(refreshMoshi))
                .build()
            val refreshApi = refreshRetrofit.create(CogniCompanionApi::class.java)

            return@Authenticator try {
                val newToken = runBlocking {
                    refreshApi.refreshToken(
                        com.cognicompanion.patient.data.model.RefreshRequest(refreshToken)
                    )
                }
                runBlocking { tokenStore.saveNewAccessToken(newToken.accessToken) }
                response.request.newBuilder()
                    .header("Authorization", "Bearer ${newToken.accessToken}")
                    .header("X-Retry-After-Refresh", "1")
                    .build()
            } catch (e: Exception) {
                // Refresh failed — clear session so app routes to login
                runBlocking { tokenStore.clearSession() }
                null
            }
        }

        return OkHttpClient.Builder()
            .addInterceptor(logging)
            .addInterceptor { chain ->
                val token = runBlocking { tokenStore.getAccessToken() }
                val request = if (token != null) {
                    chain.request().newBuilder()
                        .addHeader("Authorization", "Bearer $token")
                        .build()
                } else {
                    chain.request()
                }
                chain.proceed(request)
            }
            .authenticator(authenticator)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)   // Voice responses can take longer
            .writeTimeout(60, TimeUnit.SECONDS)
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient, moshi: Moshi, tokenStore: TokenStore): Retrofit {
        // Prefer URL saved by the user in the login screen; fall back to build-time default.
        val baseUrl = runBlocking { tokenStore.getBaseUrl() } ?: BuildConfig.BASE_URL
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
    }

    @Provides
    @Singleton
    fun provideApi(retrofit: Retrofit): CogniCompanionApi =
        retrofit.create(CogniCompanionApi::class.java)
}

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, "cognicompanion.db")
            .fallbackToDestructiveMigration(dropAllTables = true)
            .build()

    @Provides
    fun provideTimelineCacheDao(db: AppDatabase): TimelineCacheDao = db.timelineCacheDao()

    @Provides
    fun providePendingMedLogDao(db: AppDatabase): PendingMedLogDao = db.pendingMedLogDao()
}
