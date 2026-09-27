import type { AiImage } from './api'

const MAX_SIDE = 1280

// Downscale photos before upload: faster on mobile data, and plenty of detail to identify food.
export async function prepareImage(file: File): Promise<{ image: AiImage; previewUrl: string }> {
  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)
  canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  bitmap.close()
  const dataUrl = canvas.toDataURL('image/jpeg', 0.85)
  return { image: { media_type: 'image/jpeg', data: dataUrl.split(',')[1] }, previewUrl: dataUrl }
}
