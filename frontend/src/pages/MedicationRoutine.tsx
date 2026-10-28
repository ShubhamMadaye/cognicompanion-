import React, { useState } from 'react';
import {
    CalendarDays,
    Check,
    ChevronDown,
    Edit3,
    Pill,
    Plus,
    Trash2,
    X,
} from 'lucide-react';

type MedicationFrequency =
    | 'ONCE_DAILY'
    | 'TWICE_DAILY'
    | 'THREE_TIMES_DAILY'
    | 'FOUR_TIMES_DAILY'
    | 'WEEKLY'
    | 'AS_NEEDED';

type MedicationTiming =
    | 'BEFORE_BREAKFAST'
    | 'AFTER_BREAKFAST'
    | 'BEFORE_LUNCH'
    | 'AFTER_LUNCH'
    | 'BEFORE_DINNER'
    | 'AFTER_DINNER'
    | 'BEDTIME'
    | 'SPECIFIC_TIME';

type RoutineCategory =
    | 'MORNING'
    | 'AFTERNOON'
    | 'EVENING'
    | 'EXERCISE'
    | 'MEAL'
    | 'HYGIENE'
    | 'SOCIAL'
    | 'COGNITIVE'
    | 'GENERAL';

export interface MedicationRecord {
    id: string;
    name: string;
    dosage?: string | null;
    frequency?: MedicationFrequency | string | null;
    timing?: MedicationTiming | string | null;
    scheduled_time?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    notes?: string | null;
    is_active?: boolean;
}

export interface RoutineRecord {
    id: string;
    title: string;
    description?: string | null;
    category?: RoutineCategory | string | null;
    scheduled_time?: string | null;
    days_of_week?: number | null;
    icon_emoji?: string | null;
    is_active?: boolean;
}

export interface MedicationFormData {
    name: string;
    dosage: string;
    frequency: MedicationFrequency;
    timing: MedicationTiming;
    scheduled_time: string;
    start_date: string;
    end_date: string;
    notes: string;
}

export interface RoutineFormData {
    title: string;
    description: string;
    category: RoutineCategory;
    scheduled_time: string;
    days_of_week: number;
    icon_emoji?: string;
}

interface MedicationRoutineProps {
    patientName: string;

    medications: MedicationRecord[];
    routines: RoutineRecord[];

    onCreateMedication: (
        data: MedicationFormData
    ) => Promise<void>;

    onUpdateMedication?: (
        id: string,
        data: Partial<MedicationFormData>
    ) => Promise<void>;

    onDeleteMedication?: (
        id: string
    ) => Promise<void>;

    onCreateRoutine: (
        data: RoutineFormData
    ) => Promise<void>;

    onUpdateRoutine?: (
        id: string,
        data: Partial<RoutineFormData>
    ) => Promise<void>;

    onDeleteRoutine?: (
        id: string
    ) => Promise<void>;
}

const DAYS = [
    { label: 'M', name: 'Monday', value: 1 },
    { label: 'T', name: 'Tuesday', value: 2 },
    { label: 'W', name: 'Wednesday', value: 4 },
    { label: 'T', name: 'Thursday', value: 8 },
    { label: 'F', name: 'Friday', value: 16 },
    { label: 'S', name: 'Saturday', value: 32 },
    { label: 'S', name: 'Sunday', value: 64 },
];

const FREQUENCIES = [
    ['ONCE_DAILY', 'Once daily'],
    ['TWICE_DAILY', 'Twice daily'],
    ['THREE_TIMES_DAILY', 'Three times daily'],
    ['FOUR_TIMES_DAILY', 'Four times daily'],
    ['WEEKLY', 'Weekly'],
    ['AS_NEEDED', 'As needed'],
] as const;

const TIMINGS = [
    ['BEFORE_BREAKFAST', 'Before breakfast'],
    ['AFTER_BREAKFAST', 'After breakfast'],
    ['BEFORE_LUNCH', 'Before lunch'],
    ['AFTER_LUNCH', 'After lunch'],
    ['BEFORE_DINNER', 'Before dinner'],
    ['AFTER_DINNER', 'After dinner'],
    ['BEDTIME', 'Bedtime'],
    ['SPECIFIC_TIME', 'Specific time'],
] as const;

const CATEGORIES = [
    ['MORNING', 'Morning'],
    ['AFTERNOON', 'Afternoon'],
    ['EVENING', 'Evening'],
    ['EXERCISE', 'Exercise'],
    ['MEAL', 'Meal'],
    ['HYGIENE', 'Hygiene'],
    ['SOCIAL', 'Social'],
    ['COGNITIVE', 'Cognitive'],
    ['GENERAL', 'General'],
] as const;

const inputClass =
    'w-full px-3 py-2.5 border border-stone-200 rounded-md bg-white text-sm text-stone-900 outline-none focus:border-[#184e5a] focus:ring-1 focus:ring-[#184e5a]/20';

function formatTime(value?: string | null) {
    if (!value) return 'Not set';

    const [hourString, minute] = value.split(':');

    const hour = Number(hourString);

    if (Number.isNaN(hour)) return value;

    const suffix = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;

    return `${displayHour}:${minute || '00'} ${suffix}`;
}

function labelFromValue(
    value: string | null | undefined,
    options: readonly (readonly [string, string])[]
) {
    if (!value) return 'Not set';

    return (
        options.find(([key]) => key === value)?.[1] ||
        value.replaceAll('_', ' ')
    );
}

function daysToMask(days: number[]) {
    return days.reduce(
        (mask, value) => mask | value,
        0
    );
}

function maskToDays(mask?: number | null) {
    if (!mask) return [];

    return DAYS.filter(
        (day) => (mask & day.value) !== 0
    ).map((day) => day.value);
}

function formatDays(mask?: number | null) {
    if (!mask) return 'No days selected';

    if (mask === 127) return 'Every day';

    return DAYS.filter(
        (day) => (mask & day.value) !== 0
    )
        .map((day) => day.name)
        .join(', ');
}

const MedicationRoutine: React.FC<
    MedicationRoutineProps
> = ({
    patientName,
    medications,
    routines,
    onCreateMedication,
    onUpdateMedication,
    onDeleteMedication,
    onCreateRoutine,
    onUpdateRoutine,
    onDeleteRoutine,
}) => {
        const [tab, setTab] = useState<
            'medications' | 'routines'
        >('medications');

        const [medicationModal, setMedicationModal] =
            useState(false);

        const [routineModal, setRoutineModal] =
            useState(false);

        const [editingMedication, setEditingMedication] =
            useState<MedicationRecord | null>(null);

        const [editingRoutine, setEditingRoutine] =
            useState<RoutineRecord | null>(null);

        const [saving, setSaving] = useState(false);
        const [error, setError] = useState('');

        const [medicationForm, setMedicationForm] =
            useState<MedicationFormData>({
                name: '',
                dosage: '',
                frequency: 'ONCE_DAILY',
                timing: 'AFTER_BREAKFAST',
                scheduled_time: '',
                start_date: '',
                end_date: '',
                notes: '',
            });

        const [routineForm, setRoutineForm] =
            useState<RoutineFormData>({
                title: '',
                description: '',
                category: 'GENERAL',
                scheduled_time: '',
                days_of_week: 127,
                icon_emoji: '',
            });

        const activeMedications = medications.filter(
            (item) => item.is_active !== false
        );

        const activeRoutines = routines.filter(
            (item) => item.is_active !== false
        );

        const openAddMedication = () => {
            setEditingMedication(null);

            setMedicationForm({
                name: '',
                dosage: '',
                frequency: 'ONCE_DAILY',
                timing: 'AFTER_BREAKFAST',
                scheduled_time: '',
                start_date: '',
                end_date: '',
                notes: '',
            });

            setError('');
            setMedicationModal(true);
        };

        const openEditMedication = (
            medication: MedicationRecord
        ) => {
            setEditingMedication(medication);

            setMedicationForm({
                name: medication.name || '',
                dosage: medication.dosage || '',
                frequency:
                    (medication.frequency as MedicationFrequency) ||
                    'ONCE_DAILY',
                timing:
                    (medication.timing as MedicationTiming) ||
                    'AFTER_BREAKFAST',
                scheduled_time:
                    medication.scheduled_time || '',
                start_date:
                    medication.start_date || '',
                end_date:
                    medication.end_date || '',
                notes: medication.notes || '',
            });

            setError('');
            setMedicationModal(true);
        };

        const saveMedication = async (
            event: React.FormEvent
        ) => {
            event.preventDefault();

            if (!medicationForm.name.trim()) {
                setError('Medication name is required.');
                return;
            }

            if (
                medicationForm.timing ===
                'SPECIFIC_TIME' &&
                !medicationForm.scheduled_time
            ) {
                setError(
                    'Scheduled time is required when using specific time.'
                );
                return;
            }

            setSaving(true);
            setError('');

            try {
                if (editingMedication) {
                    if (!onUpdateMedication) {
                        throw new Error(
                            'Medication update is unavailable.'
                        );
                    }

                    await onUpdateMedication(
                        editingMedication.id,
                        medicationForm
                    );
                } else {
                    await onCreateMedication(
                        medicationForm
                    );
                }

                setMedicationModal(false);
                setEditingMedication(null);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : 'Failed to save medication.'
                );
            } finally {
                setSaving(false);
            }
        };

        const deactivateMedication = async (
            medication: MedicationRecord
        ) => {
            if (!onDeleteMedication) return;

            const confirmed = window.confirm(
                `Deactivate ${medication.name} for ${patientName}?`
            );

            if (!confirmed) return;

            try {
                await onDeleteMedication(
                    medication.id
                );
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : 'Failed to deactivate medication.'
                );
            }
        };

        const openAddRoutine = () => {
            setEditingRoutine(null);

            setRoutineForm({
                title: '',
                description: '',
                category: 'GENERAL',
                scheduled_time: '',
                days_of_week: 127,
                icon_emoji: '',
            });

            setError('');
            setRoutineModal(true);
        };

        const openEditRoutine = (
            routine: RoutineRecord
        ) => {
            setEditingRoutine(routine);

            setRoutineForm({
                title: routine.title || '',
                description:
                    routine.description || '',
                category:
                    (routine.category as RoutineCategory) ||
                    'GENERAL',
                scheduled_time:
                    routine.scheduled_time || '',
                days_of_week:
                    routine.days_of_week ?? 127,
                icon_emoji:
                    routine.icon_emoji || '',
            });

            setError('');
            setRoutineModal(true);
        };

        const toggleDay = (value: number) => {
            const selected = maskToDays(
                routineForm.days_of_week
            );

            const next = selected.includes(value)
                ? selected.filter(
                    (day) => day !== value
                )
                : [...selected, value];

            setRoutineForm((current) => ({
                ...current,
                days_of_week:
                    daysToMask(next),
            }));
        };

        const saveRoutine = async (
            event: React.FormEvent
        ) => {
            event.preventDefault();

            if (!routineForm.title.trim()) {
                setError('Routine name is required.');
                return;
            }

            if (!routineForm.scheduled_time) {
                setError('Routine time is required.');
                return;
            }

            if (routineForm.days_of_week === 0) {
                setError(
                    'Select at least one day.'
                );
                return;
            }

            setSaving(true);
            setError('');

            try {
                if (editingRoutine) {
                    if (!onUpdateRoutine) {
                        throw new Error(
                            'Routine update is unavailable.'
                        );
                    }

                    await onUpdateRoutine(
                        editingRoutine.id,
                        routineForm
                    );
                } else {
                    await onCreateRoutine(
                        routineForm
                    );
                }

                setRoutineModal(false);
                setEditingRoutine(null);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : 'Failed to save routine.'
                );
            } finally {
                setSaving(false);
            }
        };

        const deactivateRoutine = async (
            routine: RoutineRecord
        ) => {
            if (!onDeleteRoutine) return;

            const confirmed = window.confirm(
                `Deactivate "${routine.title}" for ${patientName}?`
            );

            if (!confirmed) return;

            try {
                await onDeleteRoutine(routine.id);
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : 'Failed to deactivate routine.'
                );
            }
        };

        return (
            <>
                <section className="bg-white border border-[#e8e4dc] rounded-md overflow-hidden">
                    <div className="px-5 py-4 border-b border-[#e8e4dc]">
                        <div className="flex items-center justify-between gap-4">
                            <div>
                                <div className="flex items-center gap-2">
                                    <div className="w-7 h-7 rounded-md bg-[#184e5a]/10 flex items-center justify-center text-[#184e5a]">
                                        <Pill className="w-4 h-4" />
                                    </div>

                                    <h2 className="text-base font-bold text-stone-900">
                                        Medications & Routines
                                    </h2>
                                </div>

                                <p className="mt-1 text-xs text-stone-500">
                                    Manage the care schedule for{' '}
                                    <span className="font-semibold text-stone-700">
                                        {patientName}
                                    </span>
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={
                                    tab === 'medications'
                                        ? openAddMedication
                                        : openAddRoutine
                                }
                                className="inline-flex items-center gap-2 px-3.5 py-2 bg-[#184e5a] text-white rounded-md text-xs font-semibold hover:bg-[#143e48]"
                            >
                                <Plus className="w-3.5 h-3.5" />

                                {tab === 'medications'
                                    ? 'Add medication'
                                    : 'Add routine'}
                            </button>
                        </div>

                        <div className="mt-4 flex border-b border-stone-100">
                            <button
                                type="button"
                                onClick={() =>
                                    setTab('medications')
                                }
                                className={`px-3 py-2 text-xs font-semibold border-b-2 ${tab === 'medications'
                                        ? 'border-[#184e5a] text-[#184e5a]'
                                        : 'border-transparent text-stone-500'
                                    }`}
                            >
                                Medications{' '}
                                <span className="ml-1">
                                    {activeMedications.length}
                                </span>
                            </button>

                            <button
                                type="button"
                                onClick={() =>
                                    setTab('routines')
                                }
                                className={`px-3 py-2 text-xs font-semibold border-b-2 ${tab === 'routines'
                                        ? 'border-[#184e5a] text-[#184e5a]'
                                        : 'border-transparent text-stone-500'
                                    }`}
                            >
                                Routines{' '}
                                <span className="ml-1">
                                    {activeRoutines.length}
                                </span>
                            </button>
                        </div>
                    </div>

                    {error &&
                        !medicationModal &&
                        !routineModal && (
                            <div className="mx-5 mt-4 px-3 py-2.5 bg-red-50 border border-red-200 rounded-md text-xs text-red-700">
                                {error}
                            </div>
                        )}

                    <div className="p-5">
                        {tab === 'medications' ? (
                            activeMedications.length === 0 ? (
                                <EmptyState
                                    icon={
                                        <Pill className="w-5 h-5" />
                                    }
                                    title="No medications configured"
                                    description="Add the medication schedule prescribed for this patient."
                                    buttonText="Add medication"
                                    onClick={openAddMedication}
                                />
                            ) : (
                                <div className="space-y-3">
                                    {activeMedications.map(
                                        (medication) => (
                                            <div
                                                key={medication.id}
                                                className="border border-stone-200 rounded-md p-4"
                                            >
                                                <div className="flex justify-between gap-4">
                                                    <div>
                                                        <div className="flex items-center gap-3">
                                                            <div className="w-8 h-8 rounded-md bg-[#184e5a]/10 flex items-center justify-center text-[#184e5a]">
                                                                <Pill className="w-4 h-4" />
                                                            </div>

                                                            <div>
                                                                <h3 className="text-sm font-bold text-stone-900">
                                                                    {medication.name}
                                                                </h3>

                                                                {medication.dosage && (
                                                                    <p className="text-xs text-stone-500">
                                                                        {medication.dosage}
                                                                    </p>
                                                                )}
                                                            </div>
                                                        </div>

                                                        <div className="ml-11 mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
                                                            <Info
                                                                label="Frequency"
                                                                value={labelFromValue(
                                                                    medication.frequency,
                                                                    FREQUENCIES
                                                                )}
                                                            />

                                                            <Info
                                                                label="Timing"
                                                                value={labelFromValue(
                                                                    medication.timing,
                                                                    TIMINGS
                                                                )}
                                                            />

                                                            <Info
                                                                label="Scheduled"
                                                                value={formatTime(
                                                                    medication.scheduled_time
                                                                )}
                                                            />

                                                            {medication.start_date && (
                                                                <Info
                                                                    label="Start"
                                                                    value={
                                                                        medication.start_date
                                                                    }
                                                                />
                                                            )}

                                                            {medication.end_date && (
                                                                <Info
                                                                    label="End"
                                                                    value={
                                                                        medication.end_date
                                                                    }
                                                                />
                                                            )}

                                                            {medication.notes && (
                                                                <Info
                                                                    label="Notes"
                                                                    value={
                                                                        medication.notes
                                                                    }
                                                                />
                                                            )}
                                                        </div>
                                                    </div>

                                                    <div className="flex gap-1">
                                                        {onUpdateMedication && (
                                                            <IconButton
                                                                onClick={() =>
                                                                    openEditMedication(
                                                                        medication
                                                                    )
                                                                }
                                                                label="Edit"
                                                            >
                                                                <Edit3 className="w-3.5 h-3.5" />
                                                            </IconButton>
                                                        )}

                                                        {onDeleteMedication && (
                                                            <IconButton
                                                                onClick={() =>
                                                                    deactivateMedication(
                                                                        medication
                                                                    )
                                                                }
                                                                label="Deactivate"
                                                            >
                                                                <Trash2 className="w-3.5 h-3.5" />
                                                            </IconButton>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    )}
                                </div>
                            )
                        ) : activeRoutines.length === 0 ? (
                            <EmptyState
                                icon={
                                    <CalendarDays className="w-5 h-5" />
                                }
                                title="No routines configured"
                                description="Add recurring activities for the patient's daily care plan."
                                buttonText="Add routine"
                                onClick={openAddRoutine}
                            />
                        ) : (
                            <div className="space-y-3">
                                {activeRoutines.map(
                                    (routine) => (
                                        <div
                                            key={routine.id}
                                            className="border border-stone-200 rounded-md p-4"
                                        >
                                            <div className="flex justify-between gap-4">
                                                <div>
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-8 h-8 rounded-md bg-stone-100 flex items-center justify-center text-stone-600">
                                                            <CalendarDays className="w-4 h-4" />
                                                        </div>

                                                        <div>
                                                            <h3 className="text-sm font-bold text-stone-900">
                                                                {routine.title}
                                                            </h3>

                                                            <p className="text-xs text-stone-500">
                                                                {labelFromValue(
                                                                    routine.category,
                                                                    CATEGORIES
                                                                )}
                                                            </p>
                                                        </div>
                                                    </div>

                                                    <div className="ml-11 mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                                                        <Info
                                                            label="Time"
                                                            value={formatTime(
                                                                routine.scheduled_time
                                                            )}
                                                        />

                                                        <Info
                                                            label="Days"
                                                            value={formatDays(
                                                                routine.days_of_week
                                                            )}
                                                        />

                                                        {routine.description && (
                                                            <Info
                                                                label="Description"
                                                                value={
                                                                    routine.description
                                                                }
                                                            />
                                                        )}
                                                    </div>
                                                </div>

                                                <div className="flex gap-1">
                                                    {onUpdateRoutine && (
                                                        <IconButton
                                                            onClick={() =>
                                                                openEditRoutine(
                                                                    routine
                                                                )
                                                            }
                                                            label="Edit"
                                                        >
                                                            <Edit3 className="w-3.5 h-3.5" />
                                                        </IconButton>
                                                    )}

                                                    {onDeleteRoutine && (
                                                        <IconButton
                                                            onClick={() =>
                                                                deactivateRoutine(
                                                                    routine
                                                                )
                                                            }
                                                            label="Deactivate"
                                                        >
                                                            <Trash2 className="w-3.5 h-3.5" />
                                                        </IconButton>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    )
                                )}
                            </div>
                        )}
                    </div>
                </section>

                {/* Medication modal */}
                {medicationModal && (
                    <Modal
                        title={
                            editingMedication
                                ? 'Edit medication'
                                : 'Add medication'
                        }
                        onClose={() => {
                            if (!saving) {
                                setMedicationModal(false);
                                setError('');
                            }
                        }}
                    >
                        <form
                            onSubmit={saveMedication}
                            className="space-y-4"
                        >
                            {error && (
                                <div className="p-3 bg-red-50 border border-red-200 rounded-md text-xs text-red-700">
                                    {error}
                                </div>
                            )}

                            <Field
                                label="Medication name"
                                required
                            >
                                <input
                                    className={inputClass}
                                    value={
                                        medicationForm.name
                                    }
                                    onChange={(e) =>
                                        setMedicationForm(
                                            (current) => ({
                                                ...current,
                                                name: e.target.value,
                                            })
                                        )
                                    }
                                    placeholder="e.g. Metformin"
                                />
                            </Field>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <Field label="Dosage">
                                    <input
                                        className={inputClass}
                                        value={
                                            medicationForm.dosage
                                        }
                                        onChange={(e) =>
                                            setMedicationForm(
                                                (current) => ({
                                                    ...current,
                                                    dosage:
                                                        e.target.value,
                                                })
                                            )
                                        }
                                        placeholder="e.g. 500 mg"
                                    />
                                </Field>

                                <Field
                                    label="Frequency"
                                    required
                                >
                                    <Select
                                        value={
                                            medicationForm.frequency
                                        }
                                        options={FREQUENCIES}
                                        onChange={(value) =>
                                            setMedicationForm(
                                                (current) => ({
                                                    ...current,
                                                    frequency:
                                                        value as MedicationFrequency,
                                                })
                                            )
                                        }
                                    />
                                </Field>

                                <Field label="Timing" required>
                                    <Select
                                        value={
                                            medicationForm.timing
                                        }
                                        options={TIMINGS}
                                        onChange={(value) =>
                                            setMedicationForm(
                                                (current) => ({
                                                    ...current,
                                                    timing:
                                                        value as MedicationTiming,
                                                })
                                            )
                                        }
                                    />
                                </Field>

                                <Field label="Scheduled time">
                                    <input
                                        type="time"
                                        className={inputClass}
                                        value={
                                            medicationForm.scheduled_time
                                        }
                                        onChange={(e) =>
                                            setMedicationForm(
                                                (current) => ({
                                                    ...current,
                                                    scheduled_time:
                                                        e.target.value,
                                                })
                                            )
                                        }
                                    />
                                </Field>

                                <Field label="Start date">
                                    <input
                                        type="date"
                                        className={inputClass}
                                        value={
                                            medicationForm.start_date
                                        }
                                        onChange={(e) =>
                                            setMedicationForm(
                                                (current) => ({
                                                    ...current,
                                                    start_date:
                                                        e.target.value,
                                                })
                                            )
                                        }
                                    />
                                </Field>

                                <Field label="End date">
                                    <input
                                        type="date"
                                        className={inputClass}
                                        value={
                                            medicationForm.end_date
                                        }
                                        onChange={(e) =>
                                            setMedicationForm(
                                                (current) => ({
                                                    ...current,
                                                    end_date:
                                                        e.target.value,
                                                })
                                            )
                                        }
                                    />
                                </Field>
                            </div>

                            <Field label="Notes">
                                <textarea
                                    className={`${inputClass} resize-none`}
                                    rows={3}
                                    value={
                                        medicationForm.notes
                                    }
                                    onChange={(e) =>
                                        setMedicationForm(
                                            (current) => ({
                                                ...current,
                                                notes: e.target.value,
                                            })
                                        )
                                    }
                                    placeholder="Additional instructions or information"
                                />
                            </Field>

                            <Actions
                                saving={saving}
                                onCancel={() => {
                                    setMedicationModal(false);
                                    setError('');
                                }}
                                label={
                                    editingMedication
                                        ? 'Save changes'
                                        : 'Add medication'
                                }
                            />
                        </form>
                    </Modal>
                )}

                {/* Routine modal */}
                {routineModal && (
                    <Modal
                        title={
                            editingRoutine
                                ? 'Edit routine'
                                : 'Add routine'
                        }
                        onClose={() => {
                            if (!saving) {
                                setRoutineModal(false);
                                setError('');
                            }
                        }}
                    >
                        <form
                            onSubmit={saveRoutine}
                            className="space-y-4"
                        >
                            {error && (
                                <div className="p-3 bg-red-50 border border-red-200 rounded-md text-xs text-red-700">
                                    {error}
                                </div>
                            )}

                            <Field
                                label="Routine name"
                                required
                            >
                                <input
                                    className={inputClass}
                                    value={
                                        routineForm.title
                                    }
                                    onChange={(e) =>
                                        setRoutineForm(
                                            (current) => ({
                                                ...current,
                                                title:
                                                    e.target.value,
                                            })
                                        )
                                    }
                                    placeholder="e.g. Morning walk"
                                />
                            </Field>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <Field label="Category" required>
                                    <Select
                                        value={
                                            routineForm.category
                                        }
                                        options={CATEGORIES}
                                        onChange={(value) =>
                                            setRoutineForm(
                                                (current) => ({
                                                    ...current,
                                                    category:
                                                        value as RoutineCategory,
                                                })
                                            )
                                        }
                                    />
                                </Field>

                                <Field
                                    label="Scheduled time"
                                    required
                                >
                                    <input
                                        type="time"
                                        className={inputClass}
                                        value={
                                            routineForm.scheduled_time
                                        }
                                        onChange={(e) =>
                                            setRoutineForm(
                                                (current) => ({
                                                    ...current,
                                                    scheduled_time:
                                                        e.target.value,
                                                })
                                            )
                                        }
                                    />
                                </Field>
                            </div>

                            <Field label="Repeat on" required>
                                <div className="flex flex-wrap gap-2">
                                    {DAYS.map((day) => {
                                        const selected =
                                            (routineForm.days_of_week &
                                                day.value) !==
                                            0;

                                        return (
                                            <button
                                                type="button"
                                                key={day.name}
                                                onClick={() =>
                                                    toggleDay(
                                                        day.value
                                                    )
                                                }
                                                className={`w-10 h-9 rounded-md border text-xs font-semibold ${selected
                                                        ? 'bg-[#184e5a] border-[#184e5a] text-white'
                                                        : 'border-stone-200 text-stone-600 hover:border-stone-400'
                                                    }`}
                                            >
                                                {day.label}
                                            </button>
                                        );
                                    })}
                                </div>

                                <p className="mt-2 text-[11px] text-stone-500">
                                    {formatDays(
                                        routineForm.days_of_week
                                    )}
                                </p>
                            </Field>

                            <Field label="Description">
                                <textarea
                                    className={`${inputClass} resize-none`}
                                    rows={3}
                                    value={
                                        routineForm.description
                                    }
                                    onChange={(e) =>
                                        setRoutineForm(
                                            (current) => ({
                                                ...current,
                                                description:
                                                    e.target.value,
                                            })
                                        )
                                    }
                                    placeholder="Describe the routine for the caregiver or patient."
                                />
                            </Field>

                            <Actions
                                saving={saving}
                                onCancel={() => {
                                    setRoutineModal(false);
                                    setError('');
                                }}
                                label={
                                    editingRoutine
                                        ? 'Save changes'
                                        : 'Add routine'
                                }
                            />
                        </form>
                    </Modal>
                )}
            </>
        );
    };

function Field({
    label,
    required,
    children,
}: {
    label: string;
    required?: boolean;
    children: React.ReactNode;
}) {
    return (
        <div>
            <label className="block mb-1.5 text-xs font-semibold text-stone-700">
                {label}
                {required && (
                    <span className="text-red-500 ml-0.5">
                        *
                    </span>
                )}
            </label>
            {children}
        </div>
    );
}

function Select({
    value,
    options,
    onChange,
}: {
    value: string;
    options: readonly (readonly [
        string,
        string
    ])[];
    onChange: (value: string) => void;
}) {
    return (
        <div className="relative">
            <select
                className={`${inputClass} appearance-none pr-8`}
                value={value}
                onChange={(e) =>
                    onChange(e.target.value)
                }
            >
                {options.map(([key, label]) => (
                    <option
                        key={key}
                        value={key}
                    >
                        {label}
                    </option>
                ))}
            </select>

            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400 pointer-events-none" />
        </div>
    );
}

function Info({
    label,
    value,
}: {
    label: string;
    value: string;
}) {
    return (
        <div>
            <p className="text-[10px] uppercase tracking-wide font-semibold text-stone-400">
                {label}
            </p>
            <p className="mt-0.5 text-xs text-stone-700">
                {value}
            </p>
        </div>
    );
}

function IconButton({
    children,
    onClick,
    label,
}: {
    children: React.ReactNode;
    onClick: () => void;
    label: string;
}) {
    return (
        <button
            type="button"
            title={label}
            onClick={onClick}
            className="w-8 h-8 flex items-center justify-center rounded-md border border-stone-200 text-stone-500 hover:bg-stone-50 hover:text-[#184e5a]"
        >
            {children}
        </button>
    );
}

function EmptyState({
    icon,
    title,
    description,
    buttonText,
    onClick,
}: {
    icon: React.ReactNode;
    title: string;
    description: string;
    buttonText: string;
    onClick: () => void;
}) {
    return (
        <div className="py-10 text-center border border-dashed border-stone-200 rounded-md">
            <div className="w-9 h-9 mx-auto flex items-center justify-center rounded-md bg-stone-100 text-stone-500">
                {icon}
            </div>

            <h3 className="mt-3 text-sm font-semibold text-stone-800">
                {title}
            </h3>

            <p className="mt-1 max-w-sm mx-auto text-xs text-stone-500">
                {description}
            </p>

            <button
                type="button"
                onClick={onClick}
                className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-2 bg-[#184e5a] text-white rounded-md text-xs font-semibold"
            >
                <Plus className="w-3.5 h-3.5" />
                {buttonText}
            </button>
        </div>
    );
}

function Modal({
    title,
    onClose,
    children,
}: {
    title: string;
    onClose: () => void;
    children: React.ReactNode;
}) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
                className="absolute inset-0 bg-black/30"
                onClick={onClose}
            />

            <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-white rounded-lg shadow-xl border border-stone-200">
                <div className="sticky top-0 z-10 flex items-center justify-between px-5 py-4 bg-white border-b border-stone-200">
                    <h2 className="text-base font-bold text-stone-900">
                        {title}
                    </h2>

                    <button
                        type="button"
                        onClick={onClose}
                        className="w-8 h-8 flex items-center justify-center rounded-md text-stone-400 hover:bg-stone-100"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="p-5">
                    {children}
                </div>
            </div>
        </div>
    );
}

function Actions({
    saving,
    onCancel,
    label,
}: {
    saving: boolean;
    onCancel: () => void;
    label: string;
}) {
    return (
        <div className="flex justify-end gap-2 pt-4 border-t border-stone-100">
            <button
                type="button"
                onClick={onCancel}
                disabled={saving}
                className="px-4 py-2.5 border border-stone-200 rounded-md text-xs font-semibold text-stone-600"
            >
                Cancel
            </button>

            <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#184e5a] text-white rounded-md text-xs font-semibold disabled:opacity-60"
            >
                {saving ? (
                    <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                ) : (
                    <Check className="w-3.5 h-3.5" />
                )}

                {saving ? 'Saving...' : label}
            </button>
        </div>
    );
}

export default MedicationRoutine;