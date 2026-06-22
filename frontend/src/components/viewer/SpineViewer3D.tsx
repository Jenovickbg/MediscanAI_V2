import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { Pause, Play, RotateCcw } from 'lucide-react'

import { fetchReconstruction3D } from '../../api/reconstruction'
import { useViewerStore } from '../../store/viewerStore'
import { cn } from '../../utils/cn'
import { Button, LoadingSpinner } from '../ui'
import { VIEWER_3D_CAMERA_PADDING, VIEWER_FRAME_CLASS, VIEWER_INNER_CLASS } from './viewerLayout'

interface SpineViewer3DProps {
  studyId: string
  className?: string
}

function hexToColor(hex: string): THREE.Color {
  return new THREE.Color(hex)
}

function fitCameraToGroup(
  camera: THREE.PerspectiveCamera,
  controls: OrbitControls,
  scene: THREE.Scene,
  root: THREE.Object3D,
  padding = VIEWER_3D_CAMERA_PADDING,
): number {
  const box = new THREE.Box3().setFromObject(root)
  const sphere = new THREE.Sphere()
  box.getBoundingSphere(sphere)

  if (!Number.isFinite(sphere.radius) || sphere.radius <= 0) {
    camera.position.set(0, 0, 80)
    camera.near = 0.1
    camera.far = 500
    camera.updateProjectionMatrix()
    controls.target.set(0, 0, 0)
    controls.update()
    return 80
  }

  const fovRad = (camera.fov * Math.PI) / 180
  const distance = (sphere.radius / Math.sin(fovRad / 2)) * padding

  camera.near = Math.max(distance / 200, 0.1)
  camera.far = distance * 4 + sphere.radius * 6
  camera.updateProjectionMatrix()

  camera.position.set(sphere.center.x, sphere.center.y, sphere.center.z + distance)
  controls.target.copy(sphere.center)
  controls.minDistance = sphere.radius * 0.35
  controls.maxDistance = distance * 2.5
  controls.update()

  if (scene.fog instanceof THREE.Fog) {
    scene.fog.near = distance * 0.4
    scene.fog.far = distance * 2.8 + sphere.radius * 2
  }

  return distance
}

export function SpineViewer3D({ studyId, className }: SpineViewer3DProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const meshGroupRef = useRef<THREE.Group | null>(null)
  const highlightRef = useRef<THREE.Mesh | null>(null)
  const meshDataRef = useRef<Awaited<ReturnType<typeof fetchReconstruction3D>> | null>(null)
  const defaultCameraDistanceRef = useRef(80)
  const frameRef = useRef<number>(0)
  const [autoRotate, setAutoRotate] = useState(false)
  const selectedVertebra = useViewerStore((s) => s.selectedVertebra)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reconstruction-3d', studyId],
    queryFn: () => fetchReconstruction3D(studyId),
    staleTime: Infinity,
  })

  useEffect(() => {
    const container = containerRef.current
    if (!container || !data) return

    let disposed = false
    let geometry: THREE.BufferGeometry | null = null
    let material: THREE.MeshPhongMaterial | null = null
    let controls: OrbitControls | null = null
    let renderer: THREE.WebGLRenderer | null = null

    const onResize = () => {
      if (!container || !cameraRef.current || !rendererRef.current) return
      const w = container.clientWidth
      const h = container.clientHeight
      if (w < 32 || h < 32) return
      cameraRef.current.aspect = w / h
      cameraRef.current.updateProjectionMatrix()
      rendererRef.current.setSize(w, h)
    }

    const setupScene = () => {
      if (disposed || rendererRef.current) return

      const width = container.clientWidth
      const height = container.clientHeight
      if (width < 32 || height < 32) return

      const scene = new THREE.Scene()
      scene.background = new THREE.Color(0x0a0f1e)
      scene.fog = new THREE.Fog(0x0a0f1e, 40, 400)

      const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 2000)

      renderer = new THREE.WebGLRenderer({ antialias: true })
      renderer.setSize(width, height)
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      container.innerHTML = ''
      container.appendChild(renderer.domElement)

      const ambientLight = new THREE.AmbientLight(0x3050a0, 0.8)
      const mainLight = new THREE.DirectionalLight(0xffffff, 1.5)
      mainLight.position.set(5, 8, 6)
      const fillLight = new THREE.DirectionalLight(0x4488ff, 0.5)
      fillLight.position.set(-4, -3, -5)
      const rimLight = new THREE.DirectionalLight(0x00c6ff, 0.3)
      rimLight.position.set(0, -6, -4)

      scene.add(ambientLight, mainLight, fillLight, rimLight)

      controls = new OrbitControls(camera, renderer.domElement)
      controls.enableDamping = true
      controls.dampingFactor = 0.08

      const group = new THREE.Group()
      scene.add(group)

      geometry = new THREE.BufferGeometry()
      const positions = new Float32Array(data.vertices.flat())
      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

      const indices = new Uint32Array(data.faces.flat())
      geometry.setIndex(new THREE.BufferAttribute(indices, 1))

      const colors = new Float32Array(data.vertex_colors.length * 3)
      data.vertex_colors.forEach((hex, i) => {
        const color = hexToColor(hex)
        colors[i * 3] = color.r
        colors[i * 3 + 1] = color.g
        colors[i * 3 + 2] = color.b
      })
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
      geometry.computeVertexNormals()

      material = new THREE.MeshPhongMaterial({
        vertexColors: true,
        shininess: 45,
        specular: new THREE.Color(0.25, 0.28, 0.35),
        side: THREE.DoubleSide,
      })

      const mesh = new THREE.Mesh(geometry, material)
      group.add(mesh)

      geometry.computeBoundingBox()
      const box = geometry.boundingBox
      if (box) {
        const center = new THREE.Vector3()
        box.getCenter(center)
        group.position.sub(center)
      }

      for (const marker of data.fracture_markers) {
        const sphere = new THREE.Mesh(
          new THREE.SphereGeometry(0.15, 8, 8),
          new THREE.MeshBasicMaterial({
            color: 0xff4757,
            transparent: true,
            opacity: 0.8,
          }),
        )
        sphere.position.set(marker.position[0], marker.position[1], marker.position[2])
        sphere.userData.isFractureMarker = true
        group.add(sphere)
      }

      meshDataRef.current = data

      Object.entries(data.vertebrae_bounds).forEach(([label, bound]) => {
        const sprite = createLabelSprite(label, label === selectedVertebra)
        sprite.position.set(bound.center[0], bound.center[1], bound.center[2] + 0.8)
        sprite.userData.vertebraLabel = label
        group.add(sprite)
      })

      const highlight = new THREE.Mesh(
        new THREE.RingGeometry(0.35, 0.5, 32),
        new THREE.MeshBasicMaterial({
          color: 0x00c6ff,
          transparent: true,
          opacity: 0.85,
          side: THREE.DoubleSide,
        }),
      )
      highlight.userData.isSelectionHighlight = true
      highlight.visible = false
      group.add(highlight)
      highlightRef.current = highlight

      defaultCameraDistanceRef.current = fitCameraToGroup(camera, controls, scene, group)

      const axes = new THREE.AxesHelper(2)
      axes.position.set(-3, -3, -3)
      scene.add(axes)

      sceneRef.current = scene
      cameraRef.current = camera
      rendererRef.current = renderer
      controlsRef.current = controls
      meshGroupRef.current = group

      const animate = (time: number) => {
        if (disposed) return
        frameRef.current = requestAnimationFrame(animate)

        if (autoRotate && meshGroupRef.current) {
          meshGroupRef.current.rotation.y += 0.003
        }

        meshGroupRef.current?.children.forEach((child) => {
          if (child.userData.isFractureMarker) {
            const scale = 0.8 + 0.2 * Math.sin(time * 0.003)
            child.scale.setScalar(scale)
          }
        })

        controls?.update()
        renderer?.render(scene, camera)
      }
      frameRef.current = requestAnimationFrame(animate)
    }

    setupScene()
    requestAnimationFrame(setupScene)

    const resizeObserver = new ResizeObserver(() => {
      if (!rendererRef.current) {
        setupScene()
        return
      }
      onResize()
    })
    resizeObserver.observe(container)
    window.addEventListener('resize', onResize)

    return () => {
      disposed = true
      resizeObserver.disconnect()
      window.removeEventListener('resize', onResize)
      cancelAnimationFrame(frameRef.current)
      controls?.dispose()
      renderer?.dispose()
      geometry?.dispose()
      material?.dispose()
      sceneRef.current = null
      cameraRef.current = null
      rendererRef.current = null
      controlsRef.current = null
      meshGroupRef.current = null
      highlightRef.current = null
      if (renderer?.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [autoRotate, data, selectedVertebra])

  useEffect(() => {
    const group = meshGroupRef.current
    const meshData = meshDataRef.current
    const highlight = highlightRef.current
    const controls = controlsRef.current
    const camera = cameraRef.current

    if (!group || !meshData) return

    group.children.forEach((child) => {
      if (child.userData.vertebraLabel) {
        const label = child.userData.vertebraLabel as string
        const isSelected = label === selectedVertebra
        child.scale.set(isSelected ? 1.6 : 1.2, isSelected ? 0.8 : 0.6, 1)
      }
    })

    if (!selectedVertebra || !meshData.vertebrae_bounds[selectedVertebra]) {
      if (highlight) highlight.visible = false
      return
    }

    const bound = meshData.vertebrae_bounds[selectedVertebra]
    const [x, y, z] = bound.center

    if (highlight) {
      highlight.visible = true
      highlight.position.set(x, y, z)
      highlight.lookAt(camera?.position ?? new THREE.Vector3(0, 0, defaultCameraDistanceRef.current))
    }

    if (controls && camera) {
      const target = new THREE.Vector3(x, y, z)
      controls.target.lerp(target, 0.35)
      controls.update()
    }
  }, [selectedVertebra])

  const handleResetCamera = () => {
    const distance = defaultCameraDistanceRef.current
    const group = meshGroupRef.current
    if (cameraRef.current && controlsRef.current && group) {
      const box = new THREE.Box3().setFromObject(group)
      const center = new THREE.Vector3()
      box.getCenter(center)
      cameraRef.current.position.set(center.x, center.y, center.z + distance)
      controlsRef.current.target.copy(center)
      controlsRef.current.update()
    }
    if (meshGroupRef.current) {
      meshGroupRef.current.rotation.set(0, 0, 0)
    }
  }

  if (isLoading) {
    return (
      <div
        className={cn(
          'flex h-[min(70vh,640px)] items-center justify-center rounded-xl border border-border bg-bg-tertiary',
          className,
        )}
      >
        <div className="text-center">
          <LoadingSpinner size="lg" label="Reconstruction 3D…" />
          <p className="mt-3 text-xs text-text-muted">Marching Cubes — peut prendre 1–2 min</p>
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div
        className={cn(
          'flex h-[min(70vh,640px)] flex-col items-center justify-center rounded-xl border border-border bg-bg-tertiary',
          className,
        )}
      >
        <p className="text-sm text-danger">Reconstruction 3D indisponible</p>
        <Button variant="ghost" className="mt-3" onClick={() => void refetch()}>
          Réessayer
        </Button>
      </div>
    )
  }

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center gap-2">
        <Button
          variant={autoRotate ? 'primary' : 'ghost'}
          icon={autoRotate ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          onClick={() => setAutoRotate((v) => !v)}
        >
          Rotation auto
        </Button>
        <Button variant="ghost" icon={<RotateCcw className="h-4 w-4" />} onClick={handleResetCamera}>
          Reset vue
        </Button>
        <span className="text-xs text-text-muted">
          {data.vertices.length.toLocaleString()} sommets ·{' '}
          {data.faces.length.toLocaleString()} faces
        </span>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-black">
        <div className={VIEWER_FRAME_CLASS}>
          <div ref={containerRef} className={VIEWER_INNER_CLASS} />
        </div>
      </div>
    </div>
  )
}

function createLabelSprite(text: string, highlighted = false): THREE.Sprite {
  const canvas = document.createElement('canvas')
  canvas.width = 64
  canvas.height = 32
  const ctx = canvas.getContext('2d')
  if (ctx) {
    ctx.fillStyle = highlighted ? 'rgba(0, 198, 255, 0.35)' : 'rgba(10, 15, 30, 0.7)'
    ctx.fillRect(0, 0, 64, 32)
    ctx.fillStyle = highlighted ? '#00C6FF' : '#E8EDF7'
    ctx.font = 'bold 14px Inter, sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(text, 32, 16)
  }

  const texture = new THREE.CanvasTexture(canvas)
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true })
  const sprite = new THREE.Sprite(material)
  sprite.scale.set(1.2, 0.6, 1)
  return sprite
}
