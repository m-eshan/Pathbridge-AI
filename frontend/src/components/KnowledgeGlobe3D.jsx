import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Sparkles, RefreshCw, Eye } from 'lucide-react';

const DOMAIN_NODES = [
  { name: 'Computer Science', category: 'degree', lat: 30, lon: -40, color: '#7c3aed' },
  { name: 'AI & Data Science', category: 'degree', lat: 50, lon: 20, color: '#7c3aed' },
  { name: 'Mechanical Eng', category: 'degree', lat: -20, lon: -60, color: '#7c3aed' },
  { name: 'Civil Eng', category: 'degree', lat: -40, lon: 30, color: '#7c3aed' },
  { name: 'Electrical Eng', category: 'degree', lat: 10, lon: 80, color: '#7c3aed' },
  { name: 'Biomedical Eng', category: 'degree', lat: -10, lon: -120, color: '#7c3aed' },
  
  { name: 'Machine Learning Eng', category: 'career', lat: 40, lon: 60, color: '#0891b2' },
  { name: 'Product Management', category: 'career', lat: 10, lon: -10, color: '#0891b2' },
  { name: 'Robotics & Automation', category: 'career', lat: -30, lon: -80, color: '#0891b2' },
  { name: 'Quantitative Finance', category: 'career', lat: 25, lon: 110, color: '#0891b2' },
  { name: 'Bioinformatics', category: 'career', lat: -25, lon: -150, color: '#0891b2' },
  { name: 'Smart Infrastructure', category: 'career', lat: -50, lon: 70, color: '#0891b2' },
  { name: 'UX & Product Design', category: 'career', lat: 55, lon: -80, color: '#db2777' },
  { name: 'Patent & Tech Law', category: 'career', lat: 60, lon: -10, color: '#d97706' }
];

const CONNECTIONS = [
  [0, 6], [0, 7], [1, 6], [1, 9], [1, 12],
  [2, 8], [2, 7], [3, 11], [4, 8], [4, 9],
  [5, 10], [5, 13], [1, 13], [0, 12]
];

function latLonToVector3(lat, lon, radius) {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  const x = -(radius * Math.sin(phi) * Math.cos(theta));
  const z = radius * Math.sin(phi) * Math.sin(theta);
  const y = radius * Math.cos(phi);
  return new THREE.Vector3(x, y, z);
}

function createArcCurve(v1, v2, radius) {
  const distance = v1.distanceTo(v2);
  const mid = v1.clone().add(v2).multiplyScalar(0.5);
  const midLength = mid.length();
  mid.normalize().multiplyScalar(radius + distance * 0.28);

  const curve = new THREE.QuadraticBezierCurve3(v1, mid, v2);
  return curve;
}

export default function KnowledgeGlobe3D() {
  const mountRef = useRef(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [viewMode2D, setViewMode2D] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (viewMode2D || !mountRef.current) return;

    const container = mountRef.current;
    const width = container.clientWidth || 800;
    const height = 480;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 260);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x7c3aed, 2.5, 300);
    pointLight.position.set(50, 50, 150);
    scene.add(pointLight);

    const cursorLight = new THREE.PointLight(0x0891b2, 2.0, 250);
    cursorLight.position.set(0, 0, 120);
    scene.add(cursorLight);

    // Globe Sphere Base
    const radius = 80;
    const globeGroup = new THREE.Group();
    scene.add(globeGroup);

    // Wireframe Globe Shell
    const sphereGeo = new THREE.SphereGeometry(radius, 32, 32);
    const wireframeMat = new THREE.MeshBasicMaterial({
      color: 0x7c3aed,
      wireframe: true,
      transparent: true,
      opacity: 0.12
    });
    const globeWire = new THREE.Mesh(sphereGeo, wireframeMat);
    globeGroup.add(globeWire);

    // Inner Glow Core
    const coreGeo = new THREE.SphereGeometry(radius * 0.95, 24, 24);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0xf8fafc,
      transparent: true,
      opacity: 0.6
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    globeGroup.add(coreMesh);

    // Nodes & Markers
    const nodeMeshes = [];
    DOMAIN_NODES.forEach((node, idx) => {
      const pos = latLonToVector3(node.lat, node.lon, radius);
      
      // Node Sphere
      const size = node.category === 'degree' ? 4.5 : 3.8;
      const nodeGeo = new THREE.SphereGeometry(size, 16, 16);
      const nodeMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(node.color),
        emissive: new THREE.Color(node.color),
        emissiveIntensity: 0.6,
        roughness: 0.2,
        metalness: 0.8
      });
      const nodeMesh = new THREE.Mesh(nodeGeo, nodeMat);
      nodeMesh.position.copy(pos);
      nodeMesh.userData = { ...node, index: idx, basePos: pos };
      globeGroup.add(nodeMesh);
      nodeMeshes.push(nodeMesh);

      // Outer Halo Ring
      const ringGeo = new THREE.RingGeometry(size * 1.3, size * 1.6, 24);
      const ringMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(node.color),
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.5
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.position.copy(pos.clone().multiplyScalar(1.02));
      ringMesh.lookAt(pos.clone().multiplyScalar(2));
      globeGroup.add(ringMesh);
    });

    // Curved Bezier Arcs
    CONNECTIONS.forEach(([startIdx, endIdx]) => {
      const n1 = DOMAIN_NODES[startIdx];
      const n2 = DOMAIN_NODES[endIdx];
      const v1 = latLonToVector3(n1.lat, n1.lon, radius);
      const v2 = latLonToVector3(n2.lat, n2.lon, radius);

      const curve = createArcCurve(v1, v2, radius);
      const points = curve.getPoints(40);
      const arcGeo = new THREE.BufferGeometry().setFromPoints(points);

      const arcMat = new THREE.LineBasicMaterial({
        color: new THREE.Color(n1.category === 'degree' ? '#7c3aed' : '#0891b2'),
        transparent: true,
        opacity: 0.45,
        blending: THREE.NormalBlending
      });

      const arcLine = new THREE.Line(arcGeo, arcMat);
      globeGroup.add(arcLine);
    });

    // Mouse Interaction
    let isDragging = false;
    let previousMousePos = { x: 0, y: 0 };
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onMouseDown = (e) => {
      isDragging = true;
      previousMousePos = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      // Cursor Light Tracking
      cursorLight.position.x = mouse.x * 120;
      cursorLight.position.y = mouse.y * 120;

      if (isDragging) {
        const deltaX = e.clientX - previousMousePos.x;
        const deltaY = e.clientY - previousMousePos.y;
        globeGroup.rotation.y += deltaX * 0.005;
        globeGroup.rotation.x += deltaY * 0.005;
        previousMousePos = { x: e.clientX, y: e.clientY };
      }

      // Raycasting for node hover
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(nodeMeshes);
      if (intersects.length > 0) {
        const hit = intersects[0].object.userData;
        setHoveredNode(hit);
        document.body.style.cursor = 'pointer';
      } else {
        setHoveredNode(null);
        document.body.style.cursor = 'default';
      }
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const domElem = renderer.domElement;
    domElem.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    // Render Loop with 45 FPS throttling
    setIsLoading(false);
    let lastTime = 0;
    let animationFrameId;

    const animate = (time) => {
      animationFrameId = requestAnimationFrame(animate);
      if (time - lastTime < 1000 / 45) return; // 45 FPS cap
      lastTime = time;

      if (!isDragging) {
        globeGroup.rotation.y += 0.0025; // Gentle auto-rotation
      }

      renderer.render(scene, camera);
    };

    animate(0);

    return () => {
      cancelAnimationFrame(animationFrameId);
      domElem.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      document.body.style.cursor = 'default';
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [viewMode2D]);

  return (
    <div style={{ position: 'relative', width: '100%', borderRadius: '20px', overflow: 'hidden', background: 'rgba(255, 255, 255, 0.65)', backdropFilter: 'blur(20px)', border: '1px solid rgba(255, 255, 255, 0.8)', boxShadow: '0 12px 36px rgba(124, 58, 237, 0.1)', padding: '24px' }}>
      
      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', zIndex: 10, position: 'relative' }}>
        <div>
          <span className="badge badge-purple" style={{ marginBottom: '6px' }}>
            <Sparkles size={14} /> 3D Interactive Knowledge Globe
          </span>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
            Global Engineering & Cross-Domain Skill Arc Network
          </h3>
        </div>

        <button
          onClick={() => setViewMode2D(!viewMode2D)}
          className="btn btn-secondary"
          style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: '999px' }}
        >
          {viewMode2D ? <RefreshCw size={14} /> : <Eye size={14} />} {viewMode2D ? 'Switch to 3D Globe' : 'Switch to 2D List View'}
        </button>
      </div>

      {/* 2D Fallback View */}
      {viewMode2D ? (
        <div style={{ padding: '24px', background: 'rgba(248, 250, 252, 0.85)', borderRadius: '16px', border: '1px solid #e2e8f0', minHeight: '380px' }}>
          <h4 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', color: 'var(--text-main)' }}>
            Domain Mapping Node Taxonomy (Accessible View)
          </h4>
          <div className="grid-2">
            <div>
              <h5 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-purple)', marginBottom: '8px' }}>Engineering Major Intake Nodes</h5>
              {DOMAIN_NODES.filter(n => n.category === 'degree').map((n, i) => (
                <div key={i} style={{ padding: '8px 12px', background: '#fff', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '6px', fontSize: '0.85rem' }}>
                  🎓 {n.name}
                </div>
              ))}
            </div>
            <div>
              <h5 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '8px' }}>Target Career Domain Bridges</h5>
              {DOMAIN_NODES.filter(n => n.category === 'career').map((n, i) => (
                <div key={i} style={{ padding: '8px 12px', background: '#fff', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '6px', fontSize: '0.85rem' }}>
                  🚀 {n.name}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* 3D WebGL Canvas Container */
        <div style={{ position: 'relative', height: '440px', width: '100%', background: 'radial-gradient(circle at 50% 50%, rgba(124, 58, 237, 0.05) 0%, transparent 70%)', borderRadius: '16px' }}>
          {isLoading && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Initializing 3D Knowledge Globe...
            </div>
          )}
          <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

          {/* Interactive Hover Card */}
          {hoveredNode && (
            <div style={{ position: 'absolute', bottom: '20px', left: '20px', background: 'rgba(255, 255, 255, 0.92)', backdropFilter: 'blur(16px)', padding: '12px 18px', borderRadius: '12px', border: `1.5px solid ${hoveredNode.color}`, boxShadow: '0 8px 20px rgba(0,0,0,0.08)', zIndex: 20 }}>
              <span className={`badge ${hoveredNode.category === 'degree' ? 'badge-purple' : 'badge-cyan'}`} style={{ fontSize: '0.7rem' }}>
                {hoveredNode.category === 'degree' ? 'Engineering Major' : 'Career Destination'}
              </span>
              <p style={{ fontWeight: 800, fontSize: '0.95rem', marginTop: '4px', color: 'var(--text-main)', marginBottom: 0 }}>
                {hoveredNode.name}
              </p>
            </div>
          )}

          <div style={{ position: 'absolute', bottom: '16px', right: '20px', fontSize: '0.75rem', color: 'var(--text-dim)', pointerEvents: 'none' }}>
            🖱️ Drag to rotate sphere | Scroll to zoom
          </div>
        </div>
      )}
    </div>
  );
}
