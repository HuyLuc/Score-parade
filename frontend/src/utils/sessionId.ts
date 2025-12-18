export type SessionType = 'realtime' | 'offline' | 'local'

const STORAGE_KEY = 'score_parade_session_counter'

const getNextCounter = (): number => {
  if (typeof window === 'undefined') return Date.now()
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const current = raw ? parseInt(raw, 10) || 0 : 0
    const next = current + 1
    window.localStorage.setItem(STORAGE_KEY, String(next))
    return next
  } catch {
    // Fallback nếu localStorage không khả dụng
    return Date.now()
  }
}

export const generateSessionId = (type: SessionType): string => {
  const counter = getNextCounter()
  const padded = counter.toString().padStart(2, '0')

  switch (type) {
    case 'realtime':
      return `realtime_${padded}`
    case 'offline':
      return `session_${padded}`
    case 'local':
      return `local_${padded}`
    default:
      return `session_${padded}`
  }
}


