package com.cognicompanion.patient.data.local

import androidx.room.*
import com.cognicompanion.patient.data.model.CachedTimelineEntity
import com.cognicompanion.patient.data.model.PendingMedicationLog
import kotlinx.coroutines.flow.Flow

// ── DAOs ──────────────────────────────────────────────────────────────────────

@Dao
interface TimelineCacheDao {
    @Query("SELECT * FROM cached_timeline ORDER BY timestamp ASC")
    fun observeTimeline(): Flow<List<CachedTimelineEntity>>

    @Query("SELECT * FROM cached_timeline ORDER BY timestamp ASC")
    suspend fun getTimeline(): List<CachedTimelineEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(entries: List<CachedTimelineEntity>)

    @Query("DELETE FROM cached_timeline")
    suspend fun clearAll()
}

@Dao
interface PendingMedLogDao {
    @Query("SELECT * FROM pending_medication_logs ORDER BY createdAt ASC")
    suspend fun getAll(): List<PendingMedicationLog>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(log: PendingMedicationLog)

    @Delete
    suspend fun delete(log: PendingMedicationLog)

    @Query("SELECT COUNT(*) FROM pending_medication_logs")
    fun countPending(): Flow<Int>
}

// ── Database ──────────────────────────────────────────────────────────────────

@Database(
    entities = [CachedTimelineEntity::class, PendingMedicationLog::class],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun timelineCacheDao(): TimelineCacheDao
    abstract fun pendingMedLogDao(): PendingMedLogDao
}
