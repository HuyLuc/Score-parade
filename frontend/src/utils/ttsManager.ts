/**
 * Text-to-Speech Manager cho đọc lỗi realtime
 * Sử dụng Web Speech API
 */

interface QueuedError {
  errorType: string
  message: string
  timestamp: number
  personId?: number
}

class TTSManager {
  private synth: SpeechSynthesis | null = null
  private isEnabled: boolean = true
  private isSpeaking: boolean = false
  private errorQueue: QueuedError[] = []
  private lastSpokenErrors: Map<string, number> = new Map() // errorType -> last spoken timestamp
  private readonly COOLDOWN_MS = 2000 // 2 giây giữa các lần đọc cùng loại lỗi
  private readonly MAX_QUEUE_SIZE = 5

  constructor() {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      this.synth = window.speechSynthesis
    } else {
      console.warn('Web Speech API không được hỗ trợ trong trình duyệt này')
    }
  }

  /**
   * Bật/tắt TTS
   */
  setEnabled(enabled: boolean) {
    this.isEnabled = enabled
    if (!enabled && this.isSpeaking) {
      this.stop()
    }
  }

  /**
   * Kiểm tra TTS có được bật không
   */
  getEnabled(): boolean {
    return this.isEnabled
  }

  /**
   * Dừng đọc hiện tại
   */
  stop() {
    if (this.synth) {
      this.synth.cancel()
      this.isSpeaking = false
    }
    this.errorQueue = []
  }

  /**
   * Chuyển đổi error type sang tiếng Việt
   */
  private getErrorMessage(error: QueuedError): string {
    const errorMessages: Record<string, string> = {
      arm_angle: 'Góc tay chưa đúng chuẩn',
      leg_angle: 'Góc chân chưa đúng chuẩn',
      arm_height: 'Tay đang hơi cao hoặc hơi thấp',
      leg_height: 'Chân đang hơi cao hoặc hơi thấp',
      head_angle: 'Đầu cúi hoặc ngẩng quá mức',
      neck_angle: 'Cổ không thẳng',
      torso_stability: 'Thân người không ổn định',
      rhythm: 'Động tác chưa đúng nhịp với nhạc',
      distance: 'Khoảng cách đội hình chưa đúng',
      speed: 'Tốc độ động tác quá nhanh hoặc quá chậm',
    }

    // Ưu tiên message từ backend, fallback về error type
    if (error.message) {
      return error.message
    }

    return errorMessages[error.errorType] || `Lỗi ${error.errorType}`
  }

  /**
   * Thêm lỗi vào queue để đọc
   */
  queueError(errorType: string, message: string, personId?: number) {
    if (!this.isEnabled || !this.synth) {
      return
    }

    // Kiểm tra cooldown - tránh đọc trùng lặp
    const now = Date.now()
    const lastSpoken = this.lastSpokenErrors.get(errorType)
    if (lastSpoken && now - lastSpoken < this.COOLDOWN_MS) {
      return // Bỏ qua nếu vừa đọc loại lỗi này
    }

    // Thêm vào queue
    const error: QueuedError = {
      errorType,
      message,
      timestamp: now,
      personId,
    }

    // Giới hạn queue size
    if (this.errorQueue.length >= this.MAX_QUEUE_SIZE) {
      this.errorQueue.shift() // Xóa lỗi cũ nhất
    }

    this.errorQueue.push(error)

    // Bắt đầu đọc nếu chưa đang đọc
    if (!this.isSpeaking) {
      this.processQueue()
    }
  }

  /**
   * Xử lý queue và đọc lỗi
   */
  private processQueue() {
    if (!this.synth || this.errorQueue.length === 0) {
      this.isSpeaking = false
      return
    }

    const error = this.errorQueue.shift()
    if (!error) {
      this.isSpeaking = false
      return
    }

    // Cập nhật last spoken time
    this.lastSpokenErrors.set(error.errorType, Date.now())

    // Tạo utterance
    const text = this.getErrorMessage(error)
    const utterance = new SpeechSynthesisUtterance(text)

    // Cấu hình giọng nói
    utterance.lang = 'vi-VN' // Tiếng Việt
    utterance.rate = 1.0 // Tốc độ bình thường
    utterance.pitch = 1.0 // Cao độ bình thường
    utterance.volume = 1.0 // Âm lượng tối đa

    // Tìm giọng tiếng Việt nếu có
    const voices = this.synth.getVoices()
    const vietnameseVoice = voices.find((voice) => voice.lang.startsWith('vi'))
    if (vietnameseVoice) {
      utterance.voice = vietnameseVoice
    }

    // Event handlers
    utterance.onend = () => {
      this.isSpeaking = false
      // Đọc lỗi tiếp theo trong queue
      setTimeout(() => this.processQueue(), 300) // Delay 300ms giữa các lỗi
    }

    utterance.onerror = (event) => {
      console.error('TTS Error:', event)
      this.isSpeaking = false
      // Vẫn tiếp tục với lỗi tiếp theo
      setTimeout(() => this.processQueue(), 300)
    }

    // Bắt đầu đọc
    this.isSpeaking = true
    this.synth.speak(utterance)
  }

  /**
   * Đọc một thông báo tùy chỉnh
   */
  speak(text: string) {
    if (!this.isEnabled || !this.synth) {
      return
    }

    this.stop() // Dừng mọi thứ đang đọc

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'vi-VN'
    utterance.rate = 1.0
    utterance.pitch = 1.0
    utterance.volume = 1.0

    const voices = this.synth.getVoices()
    const vietnameseVoice = voices.find((voice) => voice.lang.startsWith('vi'))
    if (vietnameseVoice) {
      utterance.voice = vietnameseVoice
    }

    this.synth.speak(utterance)
  }

  /**
   * Làm sạch queue và reset
   */
  clear() {
    this.stop()
    this.errorQueue = []
    this.lastSpokenErrors.clear()
  }
}

// Singleton instance
export const ttsManager = new TTSManager()

// Khởi tạo voices khi trang load (cần thiết cho một số trình duyệt)
if (typeof window !== 'undefined') {
  if ('speechSynthesis' in window) {
    // Chrome cần load voices sau khi trang load
    window.speechSynthesis.onvoiceschanged = () => {
      console.log('TTS voices loaded:', window.speechSynthesis.getVoices().length)
    }
  }
}

