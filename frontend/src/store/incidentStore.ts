import { create } from 'zustand'
import type { Incident } from '../types'

interface IncidentStore {
  incidents: Incident[]
  setIncidents: (list: Incident[]) => void
  updateIncident: (update: Partial<Incident> & { incident_id: string }) => void
}

export const useIncidentStore = create<IncidentStore>((set) => ({
  incidents: [],

  setIncidents: (list) => set({ incidents: list }),

  updateIncident: (update) =>
    set((state) => ({
      incidents: state.incidents.map((inc) =>
        inc.id === update.incident_id ? { ...inc, ...update } : inc
      ),
    })),
}))
