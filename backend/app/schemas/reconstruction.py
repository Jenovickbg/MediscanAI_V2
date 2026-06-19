from pydantic import BaseModel


class VertebraBoundsSchema(BaseModel):
    min_z: float
    max_z: float
    center: list[float]


class FractureMarkerSchema(BaseModel):
    vertebre: str
    position: list[float]
    score: float


class Reconstruction3DSchema(BaseModel):
    vertices: list[list[float]]
    faces: list[list[int]]
    normals: list[list[float]]
    vertex_colors: list[str]
    vertebrae_bounds: dict[str, VertebraBoundsSchema]
    fracture_markers: list[FractureMarkerSchema] = []
