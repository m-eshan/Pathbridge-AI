import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Layers, ArrowRight, Eye, RefreshCw } from 'lucide-react';

export default function PathwayBridge3D({ pathway, degree = 'Computer Science Engineering' }) {
  const mountRef = useRef(null);
  const [viewMode2D, setViewMode2D] = useState(false);
  const [activeStone, setActiveStone] = useState(null);

  const transferableSkills = pathway?.transferable_skills || ["python programming", "algorithms", "data structures"];
  const skillGap = pathway?.skill_gap || ["deep learning", "nlp", "model deployment"];
  const targetDomain = pathway?.title || "AI Research Engineer";

  useEffect(() => {
    if (viewMode2D || !mountRef.current) return;

    const container = mountRef.current;
    const width = container.clientWidth || 800;
    const height = 360;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 45, 130);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x7c3aed, 2.5, 300);
    pointLight.position.set(-60, 60, 80);
    scene.add(pointLight);

    const targetLight = new THREE.PointLight(0x0891b2, 2.5, 300);
    targetLight.position.set(60, 60, 80);
    scene.add(targetLight);

    const cursorLight = new THREE.PointLight(0x10b981, 2.0, 200);
    cursorLight.position.set(0, 20, 60);
    scene.add(cursorLight);

    const bridgeGroup = new THREE.Group();
    scene.add(bridgeGroup);

    // 1. Left Platform (Your Degree)
    const platformGeo = new THREE.BoxGeometry(32, 6, 28);
    const leftPlatformMat = new THREE.MeshStandardMaterial({
      color: 0x7c3aed,
      roughness: 0.3,
      metalness: 0.7,
      transparent: true,
      opacity: 0.85
    });
    const leftPlatform = new THREE.Mesh(platformGeo, leftPlatformMat);
    leftPlatform.position.set(-65, 0, 0);
    bridgeGroup.add(leftPlatform);

    // 2. Right Platform (Target Career)
    const rightPlatformMat = new THREE.MeshStandardMaterial({
      color: 0x0891b2,
      roughness: 0.3,
      metalness: 0.7,
      transparent: true,
      opacity: 0.85
    });
    const rightPlatform = new THREE.Mesh(platformGeo, rightPlatformMat);
    rightPlatform.position.set(65, 0, 0);
    bridgeGroup.add(rightPlatform);

    // 3. Stepping Stone Nodes Walkway
    const totalStones = transferableSkills.length + skillGap.length;
    const startX = -45;
    const endX = 45;
    const stepX = (endX - startX) / (totalStones + 1);

    const stoneMeshes = [];

    // Transferable Skills Stepping Stones (Green/Purple)
    transferableSkills.forEach((skill, idx) => {
      const stoneGeo = new THREE.CylinderGeometry(4.5, 5.5, 3, 20);
      const stoneMat = new THREE.MeshStandardMaterial({
        color: 0x10b981,
        emissive: 0x059669,
        emissiveIntensity: 0.5,
        roughness: 0.2
      });
      const stoneMesh = new THREE.Mesh(stoneGeo, stoneMat);
      const posX = startX + (idx + 1) * stepX;
      const posZ = Math.sin(idx * 0.8) * 6;
      stoneMesh.position.set(posX, 2, posZ);
      stoneMesh.userData = { skill, type: 'transferable', name: skill };
      bridgeGroup.add(stoneMesh);
      stoneMeshes.push(stoneMesh);
    });

    // Skill Gap Stepping Stones (Translucent Amber Locked Stones)
    skillGap.forEach((skill, idx) => {
      const stoneGeo = new THREE.CylinderGeometry(4.2, 5.0, 2.5, 20);
      const stoneMat = new THREE.MeshStandardMaterial({
        color: 0xd97706,
        emissive: 0xb45309,
        emissiveIntensity: 0.3,
        transparent: true,
        opacity: 0.7,
        roughness: 0.4
      });
      const stoneMesh = new THREE.Mesh(stoneGeo, stoneMat);
      const posX = startX + (transferableSkills.length + idx + 1) * stepX;
      const posZ = Math.sin((transferableSkills.length + idx) * 0.8) * 6;
      stoneMesh.position.set(posX, 2, posZ);
      stoneMesh.userData = { skill, type: 'gap', name: skill };
      bridgeGroup.add(stoneMesh);
      stoneMeshes.push(stoneMesh);
    });

    // Connecting Energy Beam Walkway
    const beamPoints = [
      new THREE.Vector3(-65, 1, 0),
      ...stoneMeshes.map(m => m.position.clone()),
      new THREE.Vector3(65, 1, 0)
    ];
    const curve = new THREE.CatmullRomCurve3(beamPoints);
    const tubeGeo = new THREE.TubeGeometry(curve, 50, 0.8, 8, false);
    const tubeMat = new THREE.MeshBasicMaterial({
      color: 0xc084fc,
      transparent: true,
      opacity: 0.5
    });
    const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat);
    bridgeGroup.add(tubeMesh);

    // Mouse Tracking
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onMouseMove = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      cursorLight.position.x = mouse.x * 60;
      cursorLight.position.z = -mouse.y * 40 + 20;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(stoneMeshes);
      if (intersects.length > 0) {
        setActiveStone(intersects[0].object.userData);
        document.body.style.cursor = 'pointer';
      } else {
        setActiveStone(null);
        document.body.style.cursor = 'default';
      }
    };

    const domElem = renderer.domElement;
    domElem.addEventListener('mousemove', onMouseMove);

    // 45 FPS throttled render loop
    let lastTime = 0;
    let animId;
    const animate = (time) => {
      animId = requestAnimationFrame(animate);
      if (time - lastTime < 1000 / 45) return;
      lastTime = time;

      // Subtle Floating Oscillation
      stoneMeshes.forEach((mesh, i) => {
        mesh.position.y = 2 + Math.sin(time * 0.002 + i) * 1.2;
      });

      renderer.render(scene, camera);
    };

    animate(0);

    return () => {
      cancelAnimationFrame(animId);
      domElem.removeEventListener('mousemove', onMouseMove);
      document.body.style.cursor = 'default';
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [pathway, viewMode2D]);

  return (
    <div style={{ background: 'rgba(255, 255, 255, 0.65)', backdropFilter: 'blur(20px)', borderRadius: '18px', border: '1px solid rgba(255, 255, 255, 0.8)', padding: '20px', marginBottom: '24px', boxShadow: '0 8px 24px rgba(124, 58, 237, 0.08)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div>
          <span className="badge badge-purple" style={{ fontSize: '0.7rem' }}><Layers size={12} /> 3D Skill Bridge Walkway</span>
          <h4 style={{ fontSize: '1.1rem', fontWeight: 800, margin: '4px 0 0 0', color: 'var(--text-main)' }}>
            Graph Traversal Walkway: {degree.replace('Degree:', '')} → {targetDomain}
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
              <strong style={{ color: 'var(--accent-green)' }}>Transferable Stepping Stones:</strong>
              <ul style={{ paddingLeft: '18px', marginTop: '6px' }}>
                {transferableSkills.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
            <div>
              <strong style={{ color: 'var(--accent-amber)' }}>Skill Gap Stepping Stones:</strong>
              <ul style={{ paddingLeft: '18px', marginTop: '6px' }}>
                {skillGap.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ position: 'relative', height: '320px', width: '100%', background: 'radial-gradient(circle at 50% 50%, rgba(124, 58, 237, 0.06) 0%, transparent 80%)', borderRadius: '14px', overflow: 'hidden' }}>
          <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

          {/* Active Hover Label */}
          {activeStone && (
            <div style={{ position: 'absolute', bottom: '16px', left: '50%', transform: 'translateX(-50%)', background: 'rgba(255, 255, 255, 0.94)', backdropFilter: 'blur(14px)', padding: '8px 16px', borderRadius: '999px', border: `1.5px solid ${activeStone.type === 'transferable' ? '#10b981' : '#d97706'}`, fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', boxShadow: '0 6px 16px rgba(0,0,0,0.1)' }}>
              {activeStone.type === 'transferable' ? '✅ Transferable Skill Stone: ' : '🔒 Skill Gap Stone: '}
              <span style={{ color: activeStone.type === 'transferable' ? '#059669' : '#b45309' }}>{activeStone.name}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
