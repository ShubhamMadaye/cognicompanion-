package com.cognicompanion.patient.sync

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.cognicompanion.patient.data.local.PendingMedLogDao
import com.cognicompanion.patient.data.remote.CogniCompanionApi
import com.cognicompanion.patient.data.model.LogMedicationRequest
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import retrofit2.HttpException

/**
 * Background worker that drains the offline outbox of pending medication logs.
 * Runs when the device has network connectivity (see WorkManager constraints in
 * [com.cognicompanion.patient.CogniCompanionApp]).
 */
@HiltWorker
class OutboxWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted workerParams: WorkerParameters,
    private val pendingMedLogDao: PendingMedLogDao,
    private val api: CogniCompanionApi
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        val pending = pendingMedLogDao.getAll()
        if (pending.isEmpty()) return Result.success()

        // patientId comes from the input data set by the enqueuer
        val patientId = inputData.getString(KEY_PATIENT_ID)
            ?: return Result.failure()

        for (log in pending) {
            try {
                api.logMedication(
                    patientId = patientId,
                    medicationId = log.medicationId,
                    request = LogMedicationRequest(logDate = log.logDate, taken = log.taken)
                )
                pendingMedLogDao.delete(log)
            } catch (e: HttpException) {
                // 4xx → bad request, won't succeed on retry, discard
                if (e.code() in 400..499) pendingMedLogDao.delete(log)
                else return Result.retry()
            } catch (_: Exception) {
                // Network error → retry later
                return Result.retry()
            }
        }
        return Result.success()
    }

    companion object {
        const val KEY_PATIENT_ID = "patient_id"
    }
}
