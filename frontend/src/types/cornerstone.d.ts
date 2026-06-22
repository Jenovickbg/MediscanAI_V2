declare module 'cornerstone-core' {
  export interface CornerstoneImage {
    imageId: string
    minPixelValue: number
    maxPixelValue: number
    slope: number
    intercept: number
    windowCenter: number
    windowWidth: number
    rows: number
    columns: number
    height: number
    width: number
    color: boolean
    columnPixelSpacing: number
    rowPixelSpacing: number
    sizeInBytes: number
    getPixelData(): Uint8Array | Int16Array | Float32Array
  }

  const cornerstone: CornerstoneCore
  export default cornerstone

  interface CornerstoneCore {
    enable(element: HTMLElement): void
    disable(element: HTMLElement): void
    resize(element: HTMLElement, fitToWindow?: boolean): void
    loadImage(imageId: string): Promise<CornerstoneImage>
    displayImage(element: HTMLElement, image: CornerstoneImage): void
    getEnabledElement(element: HTMLElement): { image?: CornerstoneImage }
    registerImageLoader(
      scheme: string,
      loader: (imageId: string) => { promise: Promise<CornerstoneImage> },
    ): void
  }
}

declare module 'cornerstone-math' {
  const cornerstoneMath: unknown
  export default cornerstoneMath
}

declare module 'cornerstone-web-image-loader' {
  import type { CornerstoneImage } from 'cornerstone-core'

  interface WebImageLoader {
    external: {
      cornerstone: unknown
    }
    configure(options: { beforeSend?: (xhr: XMLHttpRequest) => void }): void
    loadImage(imageId: string): { promise: Promise<CornerstoneImage> }
    arrayBufferToImage(arrayBuffer: ArrayBuffer): Promise<HTMLImageElement>
    createImage(image: HTMLImageElement, imageId: string): CornerstoneImage
  }
  const loader: WebImageLoader
  export default loader
}

declare module 'cornerstone-tools' {
  interface CornerstoneTools {
    external: {
      cornerstone: unknown
      cornerstoneMath: unknown
    }
    init(config?: { mouseEnabled?: boolean; touchEnabled?: boolean }): void
    addTool(tool: unknown): void
    setToolActive(toolName: string, options: { mouseButtonMask: number }): void
    setToolActiveForElement(
      element: HTMLElement,
      toolName: string,
      options: { mouseButtonMask: number },
    ): void
    WwwcTool: unknown
    PanTool: unknown
    ZoomTool: unknown
    ZoomMouseWheelTool: unknown
  }
  const cornerstoneTools: CornerstoneTools
  export default cornerstoneTools
}
