import React, { useRef, useEffect, useState, useMemo } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';
import { ZoomIn, ZoomOut, RotateCcw, Box, Layers } from 'lucide-react';
import SkillGraphCanvas from './SkillGraphCanvas';

export default function SkillGraph3DCanvas({ graphData, targetTitle }) {
  const fgRef = useRef(null);
  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(800);
  const [is3DMode, setIs3DMode] = useState(true);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth || 800);
      }
    };
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  // Format Graph Data for 3D force graph
  const formattedData = useMemo(() => {
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
      return { nodes: [], links: [] };
    }

    const nodes = graphData.nodes.map(n => ({
      id: n.id,
      label: n.label,
      node_type: n.node_type,
      color: n.color,
      is_on_bridge_path: n.is_on_bridge_path,
      val: n.is_on_bridge_path ? 14 : (n.node_type === 'degree' || n.node_type === 'occupation' ? 10 : 5)
    }));

    const links = graphData.links.map(l => ({
      source: l.source,
      target: l.target,
      is_bridge: l.is_bridge,
      color: l.is_bridge ? '#7c3aed' : '#cbd5e1',
      width: l.is_bridge ? 3.5 : 1
    }));

    return { nodes, links };
  }, [graphData]);

  // Initial camera position & auto-rotation
  useEffect(() => {
    if (fgRef.current && is3DMode) {
      fgRef.current.cameraPosition({ x: 0, y: 0, z: 280 });
    }
  }, [formattedData, is3DMode]);

  const handleResetCamera = () => {
    if (fgRef.current) {
      fgRef.current.cameraPosition({ x: 0, y: 0, z: 280 }, { x: 0, y: 0, z: 0 }, 1000);
    }
  };

  // Node 3D Custom Object generator (Sphere + Canvas Sprite Label)
  const createNodeObject = (node) => {
    const group = new THREE.Group();

    // Node 3D Sphere Mesh
    const radius = node.is_on_bridge_path ? 6 : (node.node_type === 'degree' || node.node_type === 'occupation' ? 5 : 3.2);
    const geometry = new THREE.SphereGeometry(radius, 24, 24);
    
    const material = new THREE.MeshPhongMaterial({
      color: node.color || '#8b5cf6',
      emissive: node.is_on_bridge_path ? '#7c3aed' : '#000000',
      emissiveIntensity: node.is_on_bridge_path ? 0.4 : 0,
      shininess: 80,
      transparent: true,
      opacity: 0.95
    });

    const sphere = new THREE.Mesh(geometry, material);
    group.add(sphere);

    // Glowing halo ring for bridge path nodes
    if (node.is_on_bridge_path) {
      const ringGeo = new THREE.RingGeometry(radius + 1.5, radius + 3, 32);
      const ringMat = new THREE.MeshBasicMaterial({ color: '#7c3aed', side: THREE.DoubleSide, transparent: true, opacity: 0.6 });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      group.add(ring);
    }

    // Text Label Sprite for important nodes
    if (node.is_on_bridge_path || node.node_type === 'degree' || node.node_type === 'occupation') {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      canvas.width = 256;
      canvas.height = 64;

      ctx.font = node.is_on_bridge_path ? 'Bold 20px Inter, sans-serif' : '18px Inter, sans-serif';
      ctx.textAlign = 'center';
      
      // Text stroke outline for readability
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 4;
      const text = node.label.length > 22 ? node.label.slice(0, 20) + '...' : node.label;
      ctx.strokeText(text, 128, 40);

      ctx.fillStyle = '#0f172a';
      ctx.fillText(text, 128, 40);

      const texture = new THREE.CanvasTexture(canvas);
      const spriteMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true });
      const sprite = new THREE.Sprite(spriteMaterial);
      sprite.position.set(0, -(radius + 8), 0);
      sprite.scale.set(40, 10, 1);
      group.add(sprite);
    }

    return group;
  };

  if (hasError || !is3DMode) {
    return (
      <div className="relative">
        <div className="flex justify-end mb-2">
          <button 
            onClick={() => setIs3DMode(true)} 
            className="btn btn-secondary" 
            style={{ fontSize: '0.75rem', padding: '4px 10px' }}
          >
            <Box size={14} /> Switch to 3D Orbit View
          </button>
        </div>
        <SkillGraphCanvas graphData={graphData} targetTitle={targetTitle} />
      </div>
    );
  }

  return (
    <div ref={containerRef} className="canvas-wrapper relative rounded-2xl overflow-hidden border border-slate-200 bg-slate-50 shadow-md">
      {/* Legend Header */}
      <div className="canvas-legend" style={{ background: 'rgba(255, 255, 255, 0.92)', backdropFilter: 'blur(12px)', padding: '8px 14px', borderRadius: '12px', border: '1px solid var(--border-color)', boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)', position: 'absolute', top: '16px', left: '16px', zIndex: 10 }}>
        <span className="badge badge-purple">● Degree Node</span>
        <span className="badge badge-cyan">● ESCO Skill</span>
        <span className="badge badge-amber">● Target Occupation</span>
        <span className="badge badge-green">-- Dijkstra Bridge Path</span>
      </div>

      {/* Mode & Reset Controls */}
      <div style={{ position: 'absolute', bottom: '16px', right: '16px', zIndex: 10, display: 'flex', gap: '6px', background: 'rgba(255, 255, 255, 0.92)', padding: '6px 10px', borderRadius: '12px', border: '1px solid var(--border-color)', boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)' }}>
        <button onClick={handleResetCamera} className="btn btn-secondary" style={{ padding: '6px 10px', fontSize: '0.75rem' }} title="Reset 3D Orbit">
          <RotateCcw size={14} /> Reset 3D View
        </button>
        <button onClick={() => setIs3DMode(false)} className="btn btn-secondary" style={{ padding: '6px 10px', fontSize: '0.75rem' }} title="Switch to 2D View">
          <Layers size={14} /> 2D Canvas View
        </button>
      </div>

      {/* 3D Force Graph Render */}
      <ForceGraph3D
        ref={fgRef}
        width={containerWidth}
        height={520}
        graphData={formattedData}
        backgroundColor="#f8fafc"
        nodeThreeObject={createNodeObject}
        nodeLabel="label"
        linkColor={link => link.color}
        linkWidth={link => link.width}
        linkOpacity={0.7}
        linkDirectionalParticles={link => link.is_bridge ? 4 : 0}
        linkDirectionalParticleSpeed={0.008}
        linkDirectionalParticleWidth={2.5}
        linkDirectionalParticleColor={() => '#7c3aed'}
        enableNodeDrag={true}
        enableNavigationControls={true}
        showNavInfo={false}
        onRenderError={() => setHasError(true)}
      />
    </div>
  );
}
