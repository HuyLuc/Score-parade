import jsPDF from 'jspdf'
import * as XLSX from 'xlsx'
import { Session } from '../store/useSessionStore'
import { format } from 'date-fns'

interface Error {
  frame_number?: number
  start_frame?: number
  end_frame?: number
  timestamp: number
  error_type?: string
  type?: string
  severity: number
  description: string
  is_sequence?: boolean
}

export function exportToPDF(session: Session, errors: Error[], score: number) {
  const doc = new jsPDF()
  
  // Title
  doc.setFontSize(20)
  doc.text('Báo Cáo Kết Quả Chấm Điểm', 105, 20, { align: 'center' })
  
  // Session Info
  doc.setFontSize(12)
  let y = 40
  doc.text(`Session ID: ${session.id}`, 20, y)
  y += 10
  doc.text(`Chế độ: ${session.mode}`, 20, y)
  y += 10
  doc.text(`Thời gian: ${format(new Date(session.startTime), 'dd/MM/yyyy HH:mm')}`, 20, y)
  y += 10
  doc.text(`Điểm số: ${score.toFixed(1)}`, 20, y)
  y += 10
  doc.text(`Tổng số lỗi: ${errors.length}`, 20, y)
  
  // Errors Table
  y += 20
  doc.setFontSize(14)
  doc.text('Chi Tiết Lỗi', 20, y)
  y += 10
  
  // Table headers
  doc.setFontSize(10)
  doc.text('Frame', 20, y)
  doc.text('Loại Lỗi', 50, y)
  doc.text('Mức Độ', 100, y)
  doc.text('Mô Tả', 130, y)
  y += 5
  
  // Table rows
  errors.slice(0, 20).forEach((error) => {
    if (y > 280) {
      doc.addPage()
      y = 20
    }
    const frameNumber = error.frame_number || error.start_frame || 0
    const frameDisplay = error.is_sequence && error.end_frame
      ? `${error.start_frame}-${error.end_frame}`
      : frameNumber.toString()
    const errorType = error.error_type || error.type || 'unknown'
    doc.text(frameDisplay, 20, y)
    doc.text(errorType, 50, y)
    doc.text(error.severity.toFixed(2), 100, y)
    doc.text(error.description.substring(0, 40), 130, y)
    y += 7
  })
  
  doc.save(`score_report_${session.id}.pdf`)
}

export function exportToExcel(session: Session, errors: Error[], score: number) {
  // Create workbook
  const wb = XLSX.utils.book_new()
  
  // Summary sheet
  const summaryData = [
    ['Session ID', session.id],
    ['Chế độ', session.mode],
    ['Thời gian', format(new Date(session.startTime), 'dd/MM/yyyy HH:mm')],
    ['Điểm số', score.toFixed(1)],
    ['Tổng số lỗi', errors.length],
  ]
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData)
  XLSX.utils.book_append_sheet(wb, summarySheet, 'Tổng Quan')
  
  // Errors sheet
  const errorsData = errors.map((error) => {
    const frameNumber = error.frame_number || error.start_frame || 0
    const frameDisplay = error.is_sequence && error.end_frame
      ? `${error.start_frame}-${error.end_frame}`
      : frameNumber.toString()
    const errorType = error.error_type || error.type || 'unknown'
    return [
      frameDisplay,
      error.timestamp ? new Date(error.timestamp * 1000).toLocaleString() : '-',
      errorType,
      error.severity.toFixed(2),
      error.description,
    ]
  })
  errorsData.unshift(['Frame', 'Thời Gian', 'Loại Lỗi', 'Mức Độ', 'Mô Tả'])
  const errorsSheet = XLSX.utils.aoa_to_sheet(errorsData)
  XLSX.utils.book_append_sheet(wb, errorsSheet, 'Chi Tiết Lỗi')
  
  // Save file
  XLSX.writeFile(wb, `score_report_${session.id}.xlsx`)
}

