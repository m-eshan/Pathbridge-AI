import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { BrainCircuit, Eye, RefreshCw } from 'lucide-react';

export default function TraitRadar3D({ bfScores, riasecScores }) {
  const mountRef = useRef(null);
  const [viewMode2D, setViewMode2D] = useState(false);
  const [activeAxis, setActiveAxis] = useState(null);

  const bf = bfScores || { Extraversion: 3.4, Agreeableness: 3.8, Conscientiousness: 4.2, Emotional_Stability: 3.5, Intellect: 4.5 };
  const riasec = riasecScores || { Realistic: 25, Investigative: 38, Artistic: 20, Social: 18, Enterprising: 25, Conventional: 30 };

  // Normalize scores to [0, 1] range
  const axes = [
    { label: 'Big5: Openness/Intellect', val: (bf.Intellect || 3.5) / 5.0, color: '#7c3aed' },
    { label: 'Big5: Conscientiousness', val: (bf.Conscientiousness || 3.5) / 5.0, color: '#7c3aed' },
    { label: 'Big5: Extraversion', val: (bf.Extraversion || 3.5) / 5.0, color: '#7c3aed' },
    { label: 'Big5: Agreeableness', val: (bf.Agreeableness || 3.5) / 5.0, color: '#7c3aed' },
    { label: 'Big5: Stability', val: (bf.Emotional_Stability || 3.5) / 5.0, color: '#7c3aed' },
    
    { label: 'RIASEC: Investigative', val: (riasec.Investigative || 25) / 50.0, color: '#0891b2' },
    { label: 'RIASEC: Realistic', val: (riasec.Realistic || 20) / 50.0, color: '#0891b2' },
    { label: 'RIASEC: Artistic', val: (riasec.Artistic || 20) / 50.0, color: '#0891b2' },
    { label: 'RIASEC: Social', val: (riasec.Social || 18) / 50.0, color: '#0891b2' },
    { label: 'RIASEC: Enterprising', val: (riasec.Enterprising || 25) / 50.0, color: '#0891b2' },
    { label: 'RIASEC: Conventional', val: (riasec.Conventional || 30) / 50.0, color: '#0891b2' }
  ];

  useEffect(() => {
    if (viewMode2D || !mountRef.current) return;

    const container = mountRef.current;
    const width = container.clientWidth || 800;
    const height = 400;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 30, 110);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Lights
    scene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const pLight = new THREE.PointLight(0x7c3aed, 2.5, 250);
    pLight.position.set(40, 50, 80);
    scene.add(pLight);

    const cursorLight = new THREE.PointLight(0x0891b2, 2.0, 200);
    cursorLight.position.set(0, 0, 80);
    scene.add(cursorLight);

    const radarGroup = new THREE.Group();
    scene.add(radarGroup);

    const radius = 42;
    const numAxes = axes.length;

    // 1. Radar Axes Grid & Rings
    const axisPositions = [];
    const valPositions = [];

    [0.25, 0.5, 0.75, 1.0].forEach(level => {
      const ringGeo = new THREE.BufferGeometry();
      const ringPts = [];
      for (let i = 0; i <= numAxes; i++) {
        const angle = (i % numAxes) * (Math.PI * 2 / numAxes);
        ringPts.push(new THREE.Vector3(Math.cos(angle) * radius * level, Math.sin(angle) * radius * level, 0));
      }
      ringGeo.setFromPoints(ringPts);
      const ringMat = new THREE.LineBasicMaterial({ color: 0xcbd5e1, transparent: true, opacity: 0.4 });
      radarGroup.add(new THREE.Line(ringGeo, ringMat));
    });

    // 2. Axes Spoke Lines & Score Nodes
    const nodeMeshes = [];

    axes.forEach((axis, i) => {
      const angle = i * (Math.PI * 2 / numAxes);
      const endVec = new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0);
      axisPositions.push(endVec);

      // Spoke line
      const spokeGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), endVec]);
      const spokeMat = new THREE.LineBasicMaterial({ color: 0x94a3b8, transparent: true, opacity: 0.5 });
      radarGroup.add(new THREE.Line(spokeGeo, spokeMat));

      // Value position
      const valVec = new THREE.Vector3(Math.cos(angle) * radius * axis.val, Math.sin(angle) * radius * axis.val, 0);
      valPositions.push(valVec);

      // Value Node Sphere
      const sphereGeo = new THREE.SphereGeometry(2.5, 16, 16);
      const sphereMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(axis.color),
        emissive: new THREE.Color(axis.color),
        emissiveIntensity: 0.6
      });
      const nodeMesh = new THREE.Mesh(sphereGeo, sphereMat);
      nodeMesh.position.copy(valVec);
      nodeMesh.userData = axis;
      radarGroup.add(nodeMesh);
      nodeMeshes.push(nodeMesh);
    });

    // 3. Score Vector Polyhedron Mesh (Translucent Glowing Polygon)
    const polyShape = new THREE.Shape();
    valPositions.forEach((pos, idx) => {
      if (idx === 0) polyShape.moveTo(pos.x, pos.y);
      else polyShape.lineTo(pos.x, pos.y);
    });

    const extrudeSettings = { depth: 3, bevelEnabled: true, bevelSegments: 3, steps: 1, bevelSize: 1, bevelThickness: 1 };
    const polyGeo = new THREE.ExtrudeGeometry(polyShape, extrudeSettings);
    const polyMat = new THREE.MeshStandardMaterial({
      color: 0x7c3aed,
      emissive: 0x6d28d9,
      emissiveIntensity: 0.4,
      transparent: true,
      opacity: 0.55,
      roughness: 0.2,
      metalness: 0.8
    });
    const polyMesh = new THREE.Mesh(polyGeo, polyMat);
    polyMesh.position.z = -1.5;
    radarGroup.add(polyMesh);

    // Mouse Controls
    let isDragging = false;
    let prevMouse = { x: 0, y: 0 };
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onMouseDown = (e) => { isDragging = true; prevMouse = { x: e.clientX, y: e.clientY }; };
    const onMouseMove = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      cursorLight.position.x = mouse.x * 50;
      cursorLight.position.y = mouse.y * 50;

      if (isDragging) {
        radarGroup.rotation.y += (e.clientX - prevMouse.x) * 0.006;
        radarGroup.rotation.x += (e.clientY - prevMouse.y) * 0.006;
        prevMouse = { x: e.clientX, y: e.clientY };
      }

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(nodeMeshes);
      if (intersects.length > 0) {
        setActiveAxis(intersects[0].object.userData);
        document.body.style.cursor = 'pointer';
      } else {
        setActiveAxis(null);
        document.body.style.cursor = 'default';
      }
    };
    const onMouseUp = () => { isDragging = false; };

    const domElem = renderer.domElement;
    domElem.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    // 45 FPS throttled render loop
    let lastTime = 0;
    let animId;
    const animate = (time) => {
      animId = requestAnimationFrame(animate);
      if (time - lastTime < 1000 / 45) return;
      lastTime = time;

      if (!isDragging) {
        radarGroup.rotation.y += 0.003;
      }
      renderer.render(scene, camera);
    };

    animate(0);

    return () => {
      cancelAnimationFrame(animId);
      domElem.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      document.body.style.cursor = 'default';
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [bfScores, riasecScores, viewMode2D]);

  return (
    <div style={{ background: 'rgba(255, 255, 255, 0.65)', backdropFilter: 'blur(20px)', borderRadius: '18px', border: '1px solid rgba(255, 255, 255, 0.8)', padding: '20px', marginBottom: '24px', boxShadow: '0 8px 24px rgba(124, 58, 237, 0.08)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div>
          <span className="badge badge-purple" style={{ fontSize: '0.7rem' }}><BrainCircuit size={12} /> 3D Trait Polyhedron</span>
          <h4 style={{ fontSize: '1.1rem', fontWeight: 800, margin: '4px 0 0 0', color: 'var(--text-main)' }}>
            Dual Psychological Trait Polyhedron (Big Five + RIASEC)
          </h4>
        </div>
        <button onClick={() => setViewMode2D(!viewMode2D)} className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.75rem', borderRadius: '999px' }}>
          {viewMode2D ? <RefreshCw size={12} /> : <Eye size={12} />} {viewMode2D ? '3D View' : 'Table View'}
        </button>
      </div>

      {viewMode2D ? (
        <div style={{ padding: '16px', background: 'rgba(248, 250, 252, 0.9)', borderRadius: '12px', border: '1px solid #e2e8f0', fontSize: '0.85rem' }}>
          <div className="grid-2">
            <div>
              <strong style={{ color: 'var(--accent-purple)' }}>Big Five Personality Vectors:</strong>
              <ul style={{ paddingLeft: '18px', marginTop: '6px' }}>
                {Object.entries(bf).map(([k, v]) => <li key={k}><strong>{k}:</strong> {v} / 5.0</li>)}
              </ul>
            </div>
            <div>
              <strong style={{ color: 'var(--accent-cyan)' }}>Holland RIASEC Interest Profile:</strong>
              <ul style={{ paddingLeft: '18px', marginTop: '6px' }}>
                {Object.entries(riasec).map(([k, v]) => <li key={k}><strong>{k}:</strong> {v} / 50</li>)}
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ position: 'relative', height: '360px', width: '100%', background: 'radial-gradient(circle at 50% 50%, rgba(124, 58, 237, 0.05) 0%, transparent 75%)', borderRadius: '14px', overflow: 'hidden' }}>
          <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

          {activeAxis && (
            <div style={{ position: 'absolute', bottom: '16px', left: '20px', background: 'rgba(255, 255, 255, 0.94)', backdropFilter: 'blur(14px)', padding: '8px 16px', borderRadius: '12px', border: `1.5px solid ${activeAxis.color}`, fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', boxShadow: '0 6px 16px rgba(0,0,0,0.1)' }}>
              {activeAxis.label}: <span style={{ color: activeAxis.color }}>{(activeAxis.val * 100).toFixed(0)}% Match</span>
            </div>
          )}
          <div style={{ position: 'absolute', bottom: '16px', right: '20px', fontSize: '0.75rem', color: 'var(--text-dim)', pointerEvents: 'none' }}>
            🖱️ Drag to rotate 3D Trait Polyhedron
          </div>
        </div>
      )}
    </div>
  );
}
