import React, { createContext, useContext, useState, useEffect } from 'react';
import { Patient } from '../types';
import { patientsApi } from '../api/patients';

import { useAuth } from './AuthContext';

interface PatientContextType {
  patients: Patient[];
  selectedPatient: Patient | null;
  setSelectedPatient: (patient: Patient | null) => void;
  isLoading: boolean;
  refreshPatients: () => Promise<void>;
}

const PatientContext = createContext<PatientContextType | undefined>(undefined);

export const PatientProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token } = useAuth();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const refreshPatients = async () => {
    setIsLoading(true);
    try {
      const data = await patientsApi.listPatients();
      if (data && data.length > 0) {
        setPatients(data);
        setSelectedPatient((prev) => {
          const match = data.find((p) => p.id === prev?.id);
          return match || data[0];
        });
      } else {
        setPatients([]);
        setSelectedPatient(null);
      }
    } catch {
      setPatients([]);
      setSelectedPatient(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!token) {
      setPatients([]);
      setSelectedPatient(null);
      return;
    }

    refreshPatients();
  }, [token]);

  return (
    <PatientContext.Provider
      value={{
        patients,
        selectedPatient,
        setSelectedPatient,
        isLoading,
        refreshPatients,
      }}
    >
      {children}
    </PatientContext.Provider>
  );
};

export const usePatient = () => {
  const ctx = useContext(PatientContext);
  if (!ctx) throw new Error('usePatient must be used within PatientProvider');
  return ctx;
};
