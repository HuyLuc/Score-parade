import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface Session {
  id: string
  mode: 'testing' | 'practising'
  startTime: Date | string  // Allow string for serialization
  score: number
  totalErrors: number
  status: 'active' | 'completed' | 'stopped'
  audioSet: boolean
  errors?: any[]  // Store errors for completed sessions
  skeletonVideoUrl?: string  // URL to skeleton video with overlay
}

interface SessionState {
  sessions: Session[]
  activeSessionId: string | null
  addSession: (session: Session) => void
  updateSession: (id: string, updates: Partial<Session>) => void
  removeSession: (id: string) => void
  setActiveSession: (id: string | null) => void
  getSession: (id: string) => Session | undefined
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      sessions: [],
      activeSessionId: null,
      addSession: (session) =>
        set((state) => {
          // Check if session with same ID already exists
          const existingIndex = state.sessions.findIndex(s => s.id === session.id)
          if (existingIndex >= 0) {
            // Update existing session instead of adding duplicate
            const updatedSessions = [...state.sessions]
            updatedSessions[existingIndex] = {
              ...session,
              startTime: session.startTime instanceof Date 
                ? session.startTime.toISOString() 
                : session.startTime
            }
            return { sessions: updatedSessions }
          }
          // Add new session
          return {
            sessions: [...state.sessions, {
              ...session,
              startTime: session.startTime instanceof Date 
                ? session.startTime.toISOString() 
                : session.startTime
            }],
          }
        }),
      updateSession: (id, updates) =>
        set((state) => ({
          sessions: state.sessions.map((s) => {
            if (s.id === id) {
              const updated = { ...s, ...updates }
              // Ensure startTime is serialized correctly
              if (updated.startTime instanceof Date) {
                updated.startTime = updated.startTime.toISOString()
              }
              return updated
            }
            return s
          }),
        })),
      removeSession: (id) =>
        set((state) => ({
          sessions: state.sessions.filter((s) => s.id !== id),
          activeSessionId:
            state.activeSessionId === id ? null : state.activeSessionId,
        })),
      setActiveSession: (id) =>
        set({
          activeSessionId: id,
        }),
      getSession: (id) => {
        const state = get()
        const session = state.sessions.find((s) => s.id === id)
        if (session && typeof session.startTime === 'string') {
          // Convert string back to Date for use
          return { ...session, startTime: new Date(session.startTime) }
        }
        return session
      },
    }),
    {
      name: 'session-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
)

