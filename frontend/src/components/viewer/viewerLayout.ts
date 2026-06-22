/** Cadre commun des viewers 2D/3D — marge intérieure pour éviter un cadrage trop serré. */
export const VIEWER_FRAME_CLASS =
  'relative box-border h-[min(70vh,640px)] p-[10%]'

export const VIEWER_INNER_CLASS = 'relative h-full w-full min-h-0 min-w-0'

/** Centrage des images PNG (MPR) dans la zone utile. */
export const VIEWER_IMAGE_CENTER_CLASS =
  'flex h-full w-full items-center justify-center'

/** Recul caméra perspective par rapport au rayon du maillage. */
export const VIEWER_3D_CAMERA_PADDING = 1.85
