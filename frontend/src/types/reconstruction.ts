export interface VertebraBounds {
  min_z: number
  max_z: number
  center: [number, number, number]
}

export interface FractureMarker {
  vertebre: string
  position: [number, number, number]
  score: number
}

export interface Reconstruction3D {
  vertices: number[][]
  faces: number[][]
  normals: number[][]
  vertex_colors: string[]
  vertebrae_bounds: Record<string, VertebraBounds>
  fracture_markers: FractureMarker[]
}
