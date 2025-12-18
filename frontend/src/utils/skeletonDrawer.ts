/**
 * Utility để vẽ skeleton (khớp xương) lên canvas
 * Sử dụng YOLOv8-Pose keypoint format (17 keypoints)
 */

export interface Keypoint {
  x: number
  y: number
  confidence: number
}

// YOLOv8-Pose keypoint indices (17 keypoints)
export const KEYPOINT_INDICES = {
  nose: 0,
  left_eye: 1,
  right_eye: 2,
  left_ear: 3,
  right_ear: 4,
  left_shoulder: 5,
  right_shoulder: 6,
  left_elbow: 7,
  right_elbow: 8,
  left_wrist: 9,
  right_wrist: 10,
  left_hip: 11,
  right_hip: 12,
  left_knee: 13,
  right_knee: 14,
  left_ankle: 15,
  right_ankle: 16,
}

// Skeleton connections (bone structure)
export const SKELETON_CONNECTIONS = [
  // Head
  [KEYPOINT_INDICES.nose, KEYPOINT_INDICES.left_eye],
  [KEYPOINT_INDICES.nose, KEYPOINT_INDICES.right_eye],
  [KEYPOINT_INDICES.left_eye, KEYPOINT_INDICES.left_ear],
  [KEYPOINT_INDICES.right_eye, KEYPOINT_INDICES.right_ear],
  
  // Torso
  [KEYPOINT_INDICES.left_shoulder, KEYPOINT_INDICES.right_shoulder],
  [KEYPOINT_INDICES.left_shoulder, KEYPOINT_INDICES.left_hip],
  [KEYPOINT_INDICES.right_shoulder, KEYPOINT_INDICES.right_hip],
  [KEYPOINT_INDICES.left_hip, KEYPOINT_INDICES.right_hip],
  
  // Left arm
  [KEYPOINT_INDICES.left_shoulder, KEYPOINT_INDICES.left_elbow],
  [KEYPOINT_INDICES.left_elbow, KEYPOINT_INDICES.left_wrist],
  
  // Right arm
  [KEYPOINT_INDICES.right_shoulder, KEYPOINT_INDICES.right_elbow],
  [KEYPOINT_INDICES.right_elbow, KEYPOINT_INDICES.right_wrist],
  
  // Left leg
  [KEYPOINT_INDICES.left_hip, KEYPOINT_INDICES.left_knee],
  [KEYPOINT_INDICES.left_knee, KEYPOINT_INDICES.left_ankle],
  
  // Right leg
  [KEYPOINT_INDICES.right_hip, KEYPOINT_INDICES.right_knee],
  [KEYPOINT_INDICES.right_knee, KEYPOINT_INDICES.right_ankle],
]

// Colors for different body parts
const COLORS = {
  head: '#FF6B6B',
  torso: '#4ECDC4',
  leftArm: '#45B7D1',
  rightArm: '#96CEB4',
  leftLeg: '#FFEAA7',
  rightLeg: '#DDA15E',
  joint: '#FFFFFF',
}

/**
 * Convert keypoints array [17, 3] to Keypoint objects
 */
export function parseKeypoints(keypoints: number[][] | null | undefined): Keypoint[] | null {
  if (!keypoints || !Array.isArray(keypoints) || keypoints.length === 0) {
    return null
  }
  
  // YOLOv8-Pose format: [x, y, confidence] for each of 17 keypoints
  if (keypoints.length !== 17) {
    return null
  }
  
  return keypoints.map((kp) => ({
    x: kp[0] || 0,
    y: kp[1] || 0,
    confidence: kp[2] || 0,
  }))
}

/**
 * Draw skeleton on canvas
 */
export function drawSkeleton(
  ctx: CanvasRenderingContext2D,
  keypoints: Keypoint[],
  scaleX: number = 1,
  scaleY: number = 1
) {
  if (!keypoints || keypoints.length !== 17) {
    return
  }

  // Draw connections (bones)
  ctx.lineWidth = 3
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'

  // Draw torso (green)
  ctx.strokeStyle = COLORS.torso
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.left_shoulder, KEYPOINT_INDICES.right_shoulder, scaleX, scaleY)
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.left_shoulder, KEYPOINT_INDICES.left_hip, scaleX, scaleY)
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.right_shoulder, KEYPOINT_INDICES.right_hip, scaleX, scaleY)
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.left_hip, KEYPOINT_INDICES.right_hip, scaleX, scaleY)

  // Draw left arm (blue)
  ctx.strokeStyle = COLORS.leftArm
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.left_shoulder, KEYPOINT_INDICES.left_elbow, scaleX, scaleY)
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.left_elbow, KEYPOINT_INDICES.left_wrist, scaleX, scaleY)

  // Draw right arm (light green)
  ctx.strokeStyle = COLORS.rightArm
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.right_shoulder, KEYPOINT_INDICES.right_elbow, scaleX, scaleY)
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.right_elbow, KEYPOINT_INDICES.right_wrist, scaleX, scaleY)

  // Draw left leg (yellow)
  ctx.strokeStyle = COLORS.leftLeg
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.left_hip, KEYPOINT_INDICES.left_knee, scaleX, scaleY)
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.left_knee, KEYPOINT_INDICES.left_ankle, scaleX, scaleY)

  // Draw right leg (orange)
  ctx.strokeStyle = COLORS.rightLeg
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.right_hip, KEYPOINT_INDICES.right_knee, scaleX, scaleY)
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.right_knee, KEYPOINT_INDICES.right_ankle, scaleX, scaleY)

  // Draw head connections
  ctx.strokeStyle = COLORS.head
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.nose, KEYPOINT_INDICES.left_eye, scaleX, scaleY)
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.nose, KEYPOINT_INDICES.right_eye, scaleX, scaleY)
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.left_eye, KEYPOINT_INDICES.left_ear, scaleX, scaleY)
  drawConnection(ctx, keypoints, KEYPOINT_INDICES.right_eye, KEYPOINT_INDICES.right_ear, scaleX, scaleY)

  // Draw joints (keypoints)
  ctx.fillStyle = COLORS.joint
  keypoints.forEach((kp) => {
    if (kp.confidence > 0.3) {  // Only draw if confidence > 30%
      const x = kp.x * scaleX
      const y = kp.y * scaleY
      
      // Draw joint circle
      ctx.beginPath()
      ctx.arc(x, y, 4, 0, 2 * Math.PI)
      ctx.fill()
      
      // Draw outer ring for better visibility
      ctx.strokeStyle = COLORS.joint
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.arc(x, y, 6, 0, 2 * Math.PI)
      ctx.stroke()
    }
  })
}

/**
 * Draw a connection between two keypoints
 */
function drawConnection(
  ctx: CanvasRenderingContext2D,
  keypoints: Keypoint[],
  idx1: number,
  idx2: number,
  scaleX: number,
  scaleY: number
) {
  const kp1 = keypoints[idx1]
  const kp2 = keypoints[idx2]

  if (!kp1 || !kp2) return
  if (kp1.confidence < 0.3 || kp2.confidence < 0.3) return  // Skip if confidence too low

  ctx.beginPath()
  ctx.moveTo(kp1.x * scaleX, kp1.y * scaleY)
  ctx.lineTo(kp2.x * scaleX, kp2.y * scaleY)
  ctx.stroke()
}

/**
 * Draw person ID label
 */
export function drawPersonLabel(
  ctx: CanvasRenderingContext2D,
  personId: number,
  keypoints: Keypoint[],
  scaleX: number,
  scaleY: number
) {
  if (!keypoints || keypoints.length === 0) return

  // Use nose or top of head as label position
  const headKp = keypoints[KEYPOINT_INDICES.nose]
  if (!headKp || headKp.confidence < 0.3) return

  const x = headKp.x * scaleX
  const y = headKp.y * scaleY - 20

  // Draw background
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
  ctx.fillRect(x - 20, y - 15, 40, 20)

  // Draw text
  ctx.fillStyle = '#FFFFFF'
  ctx.font = 'bold 14px Arial'
  ctx.textAlign = 'center'
  ctx.fillText(`ID ${personId}`, x, y)
}

