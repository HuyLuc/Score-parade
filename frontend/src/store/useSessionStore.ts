import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface Session {
  id: string
  mode: 'testing' | 'practising'
  startTime: Date
  score: number
  totalErrors: number
  status: 'active' | 'completed' | 'stopped'
  audioSet: boolean
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
        set((state) => ({
          sessions: [...state.sessions, session],
        })),
      updateSession: (id, updates) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === id ? { ...s, ...updates } : s
          ),
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
        return state.sessions.find((s) => s.id === id)
      },
    }),
    {
      name: 'session-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
)

