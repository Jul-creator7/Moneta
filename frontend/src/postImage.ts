const MAX_UPLOAD_BYTES = 12 * 1024 * 1024
const MAX_IMAGE_BYTES = 512 * 1024
const MAX_SIDE = 1200
export const imageTypes = "image/jpeg,image/png,image/webp"

export async function readPostImage(file: FormDataEntryValue | null) {
  if (!(file instanceof File) || !file.name) return null
  if (!imageTypes.split(",").includes(file.type)) throw new Error("Choose a JPEG, PNG, or WebP image.")
  if (file.size > MAX_UPLOAD_BYTES) throw new Error("Choose a source image smaller than 12 MB.")
  const image = await createImageBitmap(file).catch(() => {
    throw new Error("This image could not be opened.")
  })
  try {
    const scale = Math.min(1, MAX_SIDE / Math.max(image.width, image.height))
    const canvas = document.createElement("canvas")
    canvas.width = Math.max(1, Math.round(image.width * scale))
    canvas.height = Math.max(1, Math.round(image.height * scale))
    const context = canvas.getContext("2d")
    if (!context) throw new Error("This browser could not prepare the image.")
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    for (const quality of [0.82, 0.65, 0.45]) {
      const result = canvas.toDataURL("image/webp", quality)
      const encoded = result.slice(result.indexOf(",") + 1)
      if (encoded.length * 0.75 - (encoded.endsWith("==") ? 2 : encoded.endsWith("=") ? 1 : 0) <= MAX_IMAGE_BYTES) return result
    }
    throw new Error("The image is too large after compression. Try a smaller image.")
  } finally {
    image.close()
  }
}
