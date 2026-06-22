import cornerstone from 'cornerstone-core'
import type { CornerstoneImage } from 'cornerstone-core'
import cornerstoneMath from 'cornerstone-math'
import cornerstoneTools from 'cornerstone-tools'
import cornerstoneWebImageLoader from 'cornerstone-web-image-loader'

let initialized = false

export function initCornerstone(): void {
  if (initialized) return

  cornerstoneWebImageLoader.external.cornerstone = cornerstone
  cornerstoneWebImageLoader.configure({})
  cornerstone.registerImageLoader('blob', cornerstoneWebImageLoader.loadImage)
  cornerstoneTools.external.cornerstone = cornerstone
  cornerstoneTools.external.cornerstoneMath = cornerstoneMath

  cornerstoneTools.init({
    mouseEnabled: true,
    touchEnabled: false,
  })

  cornerstoneTools.addTool(cornerstoneTools.WwwcTool)
  cornerstoneTools.addTool(cornerstoneTools.PanTool)
  cornerstoneTools.addTool(cornerstoneTools.ZoomTool)
  cornerstoneTools.addTool(cornerstoneTools.ZoomMouseWheelTool)

  initialized = true
}

export function activateViewerTools(element: HTMLElement): void {
  cornerstoneTools.setToolActiveForElement(element, 'Wwwc', { mouseButtonMask: 1 })
  cornerstoneTools.setToolActiveForElement(element, 'Pan', { mouseButtonMask: 2 })
  cornerstoneTools.setToolActiveForElement(element, 'ZoomMouseWheel', { mouseButtonMask: 1 })
}

export async function loadPngBlobAsCornerstoneImage(
  blob: Blob,
  imageId: string,
): Promise<CornerstoneImage> {
  const arrayBuffer = await blob.arrayBuffer()
  const htmlImage = await cornerstoneWebImageLoader.arrayBufferToImage(arrayBuffer)
  return cornerstoneWebImageLoader.createImage(htmlImage, imageId)
}

export { cornerstone, cornerstoneTools, cornerstoneWebImageLoader }
