import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

export default function HeroGraphBackground() {
  const containerRef = useRef(null);
  const [webGlSupported, setWebGlSupported] = useState(true);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // WebGL support check
    try {
      const testCanvas = document.createElement('canvas');
      const gl = testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl');
      if (!gl) {
        setWebGlSupported(false);
        return;
      }
    } catch (e) {
      setWebGlSupported(false);
      return;
    }

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || 500;

    // 1. Scene, Camera, Renderer setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0xf8fafc, 0.0018);

    const camera = new THREE.PerspectiveCamera(60, width / height, 1, 1000);
    camera.position.z = 240;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'low-power' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setSize(width, height);
    renderer.setClearColor(0xf8fafc, 0); // Transparent to show light theme
    container.appendChild(renderer.domElement);

    // 2. Generate Skill/Knowledge Graph 3D Nodes
    const NODE_COUNT = 65;
    const nodePositions = [];
    const nodeVelocities = [];
    const nodeColors = [];
    const nodeSizes = [];

    const colorPalette = [
      new THREE.Color('#7c3aed'), // Purple accent
      new THREE.Color('#8b5cf6'),
      new THREE.Color('#0891b2'), // Cyan accent
      new THREE.Color('#a855f7'),
      new THREE.Color('#c084fc')
    ];

    for (let i = 0; i < NODE_COUNT; i++) {
      const x = (Math.random() - 0.5) * 320;
      const y = (Math.random() - 0.5) * 220;
      const z = (Math.random() - 0.5) * 200;
      nodePositions.push(x, y, z);

      nodeVelocities.push(
        (Math.random() - 0.5) * 0.12,
        (Math.random() - 0.5) * 0.12,
        (Math.random() - 0.5) * 0.08
      );

      const color = colorPalette[Math.floor(Math.random() * colorPalette.length)];
      nodeColors.push(color.r, color.g, color.b);

      nodeSizes.push(Math.random() * 4 + 3);
    }

    // Node Points Geometry
    const nodesGeometry = new THREE.BufferGeometry();
    nodesGeometry.setAttribute('position', new THREE.Float32BufferAttribute(nodePositions, 3));
    nodesGeometry.setAttribute('color', new THREE.Float32BufferAttribute(nodeColors, 3));

    // Custom circular sprite texture for soft smooth nodes
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 32;
    const ctx = canvas.getContext('2d');
    const grad = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
    grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
    grad.addColorStop(0.4, 'rgba(255, 255, 255, 0.8)');
    grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(16, 16, 16, 0, Math.PI * 2);
    ctx.fill();

    const spriteTexture = new THREE.CanvasTexture(canvas);

    const nodesMaterial = new THREE.PointsMaterial({
      size: 7,
      vertexColors: true,
      map: spriteTexture,
      transparent: true,
      opacity: 0.75,
      blending: THREE.NormalBlending,
      depthWrite: false
    });

    const nodesCloud = new THREE.Points(nodesGeometry, nodesMaterial);
    scene.add(nodesCloud);

    // 3. Dynamic Knowledge Graph Connecting Edges (Lines)
    const MAX_LINE_DIST = 75;
    const linesGeometry = new THREE.BufferGeometry();
    const linePositions = new Float32Array(NODE_COUNT * NODE_COUNT * 6);
    const lineColors = new Float32Array(NODE_COUNT * NODE_COUNT * 6);

    linesGeometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
    linesGeometry.setAttribute('color', new THREE.BufferAttribute(lineColors, 3));

    const linesMaterial = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.35,
      blending: THREE.NormalBlending
    });

    const lineSegments = new THREE.LineSegments(linesGeometry, linesMaterial);
    scene.add(lineSegments);

    // 4. Mouse Parallax Targets
    let mouseX = 0;
    let mouseY = 0;
    let targetRotationX = 0;
    let targetRotationY = 0;

    const handleMouseMove = (event) => {
      const rect = container.getBoundingClientRect();
      const relX = event.clientX - rect.left - rect.width / 2;
      const relY = event.clientY - rect.top - rect.height / 2;

      mouseX = relX * 0.0008;
      mouseY = relY * 0.0008;
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    // Handle Window Resize
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth || window.innerWidth;
      const h = container.clientHeight || 500;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    // 5. Animation Loop with Frame Throttling for low-end safety
    let animId;
    let lastTime = performance.now();
    const targetFPS = 45; // Smooth & energy efficient
    const interval = 1000 / targetFPS;

    const animate = (currentTime) => {
      animId = requestAnimationFrame(animate);

      const delta = currentTime - lastTime;
      if (delta < interval) return;
      lastTime = currentTime - (delta % interval);

      // Mouse parallax smooth interpolation
      targetRotationX += (mouseY - targetRotationX) * 0.04;
      targetRotationY += (mouseX - targetRotationY) * 0.04;

      scene.rotation.x = targetRotationX;
      scene.rotation.y = targetRotationY + currentTime * 0.00008; // Very slow drift

      // Drift Nodes
      const positions = nodesGeometry.attributes.position.array;
      for (let i = 0; i < NODE_COUNT; i++) {
        const idx = i * 3;
        positions[idx] += nodeVelocities[idx];
        positions[idx + 1] += nodeVelocities[idx + 1];
        positions[idx + 2] += nodeVelocities[idx + 2];

        // Bounce back within bounds
        if (Math.abs(positions[idx]) > 160) nodeVelocities[idx] *= -1;
        if (Math.abs(positions[idx + 1]) > 120) nodeVelocities[idx + 1] *= -1;
        if (Math.abs(positions[idx + 2]) > 100) nodeVelocities[idx + 2] *= -1;
      }
      nodesGeometry.attributes.position.needsUpdate = true;

      // Update Connecting Edges (Lines) dynamically based on distance
      let vertexIdx = 0;
      let colorIdx = 0;
      let connectionCount = 0;

      for (let i = 0; i < NODE_COUNT; i++) {
        for (let j = i + 1; j < NODE_COUNT; j++) {
          const i3 = i * 3;
          const j3 = j * 3;

          const dx = positions[i3] - positions[j3];
          const dy = positions[i3 + 1] - positions[j3 + 1];
          const dz = positions[i3 + 2] - positions[j3 + 2];
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

          if (dist < MAX_LINE_DIST) {
            const alpha = 1.0 - dist / MAX_LINE_DIST;

            // Line Endpoint A
            linePositions[vertexIdx++] = positions[i3];
            linePositions[vertexIdx++] = positions[i3 + 1];
            linePositions[vertexIdx++] = positions[i3 + 2];

            // Line Endpoint B
            linePositions[vertexIdx++] = positions[j3];
            linePositions[vertexIdx++] = positions[j3 + 1];
            linePositions[vertexIdx++] = positions[j3 + 2];

            // Purple / Teal gradient tint
            const cR = 0.48 * alpha + 0.1;
            const cG = 0.22 * alpha + 0.1;
            const cB = 0.92 * alpha + 0.2;

            lineColors[colorIdx++] = cR;
            lineColors[colorIdx++] = cG;
            lineColors[colorIdx++] = cB;

            lineColors[colorIdx++] = cR;
            lineColors[colorIdx++] = cG;
            lineColors[colorIdx++] = cB;

            connectionCount++;
          }
        }
      }

      linesGeometry.setDrawRange(0, connectionCount * 2);
      linesGeometry.attributes.position.needsUpdate = true;
      linesGeometry.attributes.color.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animate(performance.now());

    // Cleanup
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
      nodesGeometry.dispose();
      nodesMaterial.dispose();
      linesGeometry.dispose();
      linesMaterial.dispose();
      spriteTexture.dispose();
    };
  }, []);

  if (!webGlSupported) {
    return (
      <div 
        className="absolute inset-0 pointer-events-none z-0 opacity-40 transition-opacity" 
        style={{
          background: 'radial-gradient(circle at 50% 30%, rgba(124, 58, 237, 0.12) 0%, rgba(8, 145, 178, 0.08) 40%, transparent 70%)'
        }}
      />
    );
  }

  return (
    <div 
      ref={containerRef} 
      className="hero-graph-bg" 
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
        opacity: 0.65,
        overflow: 'hidden'
      }}
    />
  );
}
