import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Target, Eye, RefreshCw } from 'lucide-react';

export default function RoadmapTimeline3D({ roadmapData }) {
  const mountRef = useRef(null);
  const [viewMode2D, setViewMode2D] = useState(false);
  const [activeStageIdx, setActiveStageIdx] = useState(0);

  const stages = roadmapData?.stages ? Object.entries(roadmapData.stages) : [
    ["Stage 1: Core Skill Bridge (Months 1–3)", { focus: "Dijkstra shortest-path gap bridging skills", action_items: ["Complete online course", "Build micro-projects"] }],
    ["Stage 2: Applied Projects (Months 4–6)", { focus: "Cross-domain synthesis & real-world dataset analytics", action_items: ["Build portfolio capstone", "Deploy live application"] }],
    ["Stage 3: Placement Prep (Months 7–9)", { focus: "Target domain resume framing & technical interview prep", action_items: ["Mock interview sessions", "Target job applications"] }]
  ];

  useEffect(() => {
    if (viewMode2D || !mountRef.current) return;

    const container = mountRef.current;
    const width = container.clientWidth || 800;
    const height = 340;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 35, 110);
    camera.lookAt(0, 0, -20);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Lights
    scene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const pLight = new THREE.PointLight(0x7c3aed, 2.5, 300);
    pLight.position.set(0, 60, 40);
    scene.add(pLight);

    const cursorLight = new THREE.PointLight(0x0891b2, 2.0, 200);
    cursorLight.position.set(0, 20, 40);
    scene.add(cursorLight);

    const timelineGroup = new THREE.Group();
    scene.add(timelineGroup);

    // Winding Receding Road Curve Points
    const curvePoints = [
      new THREE.Vector3(-45, 0, 30),
      new THREE.Vector3(-15, 0, 0),
      new THREE.Vector3(15, 0, -30),
      new THREE.Vector3(45, 0, -60)
    ];

    const curve = new THREE.CatmullRomCurve3(curvePoints);
    const roadGeo = new THREE.TubeGeometry(curve, 60, 4, 12, false);
    const roadMat = new THREE.MeshStandardMaterial({
      color: 0x7c3aed,
      emissive: 0x4f46e5,
      emissiveIntensity: 0.3,
      roughness: 0.3,
      transparent: true,
      opacity: 0.7
    });
    const roadMesh = new THREE.Mesh(roadGeo, roadMat);
    timelineGroup.add(roadMesh);

    // Stage Waypoint Spheres & Glowing Columns
    const waypointMeshes = [];
    stages.forEach(([title, info], idx) => {
      const t = (idx + 1) / (stages.length + 1);
      const pos = curve.getPointAt(t);

      // Waypoint Pillar
      const pillarGeo = new THREE.CylinderGeometry(1.5, 2.5, 12, 16);
      const pillarMat = new THREE.MeshStandardMaterial({
        color: idx === activeStageIdx ? 0x0891b2 : 0x7c3aed,
        emissive: idx === activeStageIdx ? 0x0891b2 : 0x6d28d9,
        emissiveIntensity: 0.6
      });
      const pillarMesh = new THREE.Mesh(pillarGeo, pillarMat);
      pillarMesh.position.set(pos.x, pos.y + 6, pos.z);
      pillarMesh.userData = { title, info, index: idx };
      timelineGroup.add(pillarMesh);

      // Waypoint Top Glowing Orb
      const orbGeo = new THREE.SphereGeometry(4, 16, 16);
      const orbMat = new THREE.MeshStandardMaterial({
        color: idx === activeStageIdx ? 0x10b981 : 0xc084fc,
        emissive: idx === activeStageIdx ? 0x059669 : 0x7c3aed,
        emissiveIntensity: 0.8
      });
      const orbMesh = new THREE.Mesh(orbGeo, orbMat);
      orbMesh.position.set(pos.x, pos.y + 14, pos.z);
      orbMesh.userData = { title, info, index: idx };
      timelineGroup.add(orbMesh);

      waypointMeshes.push(orbMesh);
    });

    // Mouse Interaction
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onMouseMove = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      cursorLight.position.x = mouse.x * 50;
      cursorLight.position.z = -mouse.y * 50 + 20;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(waypointMeshes);
      if (intersects.length > 0) {
        document.body.style.cursor = 'pointer';
      } else {
        document.body.style.cursor = 'default';
      }
    };

    const onClick = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(waypointMeshes);
      if (intersects.length > 0) {
        const hit = intersects[0].object.userData;
        setActiveStageIdx(hit.index);
      }
    };

    const domElem = renderer.domElement;
    domElem.addEventListener('mousemove', onMouseMove);
    domElem.addEventListener('click', onClick);

    // 45 FPS Throttled Animation Loop
    let lastTime = 0;
    let animId;
    const animate = (time) => {
      animId = requestAnimationFrame(animate);
      if (time - lastTime < 1000 / 45) return;
      lastTime = time;

      // Smooth Camera Target Offset based on active stage
      const targetT = (activeStageIdx + 1) / (stages.length + 1);
      const targetPos = curve.getPointAt(targetT);
      camera.position.x += (targetPos.x * 0.4 - camera.position.x) * 0.05;
      camera.lookAt(targetPos.x, targetPos.y + 4, targetPos.z);

      renderer.render(scene, camera);
    };

    animate(0);

    return () => {
      cancelAnimationFrame(animId);
      domElem.removeEventListener('mousemove', onMouseMove);
      domElem.removeEventListener('click', onClick);
      document.body.style.cursor = 'default';
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [roadmapData, activeStageIdx, viewMode2D]);

  return (
    <div style={{ background: 'rgba(255, 255, 255, 0.65)', backdropFilter: 'blur(20px)', borderRadius: '18px', border: '1px solid rgba(255, 255, 255, 0.8)', padding: '20px', marginBottom: '24px', boxShadow: '0 8px 24px rgba(124, 58, 237, 0.08)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div>
          <span className="badge badge-purple" style={{ fontSize: '0.7rem' }}><Target size={12} /> 3D Roadmap Path</span>
          <h4 style={{ fontSize: '1.1rem', fontWeight: 800, margin: '4px 0 0 0', color: 'var(--text-main)' }}>
            3-Stage Sequential Receding Pathway Timeline
          </h4>
        </div>
        <button onClick={() => setViewMode2D(!viewMode2D)} className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.75rem', borderRadius: '999px' }}>
          {viewMode2D ? <RefreshCw size={12} /> : <Eye size={12} />} {viewMode2D ? '3D Path' : 'List View'}
        </button>
      </div>

      {viewMode2D ? (
        <div style={{ padding: '16px', background: 'rgba(248, 250, 252, 0.9)', borderRadius: '12px', border: '1px solid #e2e8f0', fontSize: '0.85rem' }}>
          {stages.map(([t, info], i) => (
            <div key={i} style={{ marginBottom: '12px', paddingBottom: '8px', borderBottom: '1px solid #e2e8f0' }}>
              <strong style={{ color: 'var(--accent-purple)' }}>{t}</strong>
              <p style={{ color: 'var(--text-muted)', margin: '2px 0 0 0' }}>Focus: {info.focus}</p>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ position: 'relative', height: '300px', width: '100%', background: 'radial-gradient(circle at 50% 50%, rgba(124, 58, 237, 0.05) 0%, transparent 80%)', borderRadius: '14px', overflow: 'hidden' }}>
          <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

          {/* Active Stage Display Panel */}
          <div style={{ position: 'absolute', bottom: '16px', left: '20px', right: '20px', background: 'rgba(255, 255, 255, 0.94)', backdropFilter: 'blur(14px)', padding: '12px 18px', borderRadius: '12px', border: '1.5px solid var(--accent-purple)', boxShadow: '0 8px 20px rgba(0,0,0,0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <span className="badge badge-purple" style={{ fontSize: '0.68rem' }}>ACTIVE WAYPOINT {activeStageIdx + 1} OF {stages.length}</span>
              <p style={{ fontWeight: 800, fontSize: '0.95rem', margin: '2px 0 0 0', color: 'var(--text-main)' }}>
                {stages[activeStageIdx][0]}
              </p>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: 0 }}>
                {stages[activeStageIdx][1].focus}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              {stages.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActiveStageIdx(i)}
                  style={{ width: '24px', height: '24px', borderRadius: '50%', border: 'none', background: i === activeStageIdx ? 'var(--accent-purple)' : '#e2e8f0', color: i === activeStageIdx ? '#fff' : '#64748b', fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer' }}
                >
                  {i + 1}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
