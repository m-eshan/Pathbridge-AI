import React, { useRef, useEffect, useState } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Info, Layers } from 'lucide-react';

export default function SkillGraphCanvas({ graphData, targetTitle }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  const [zoom, setZoom] = useState(1);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) return;

    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    const width = container.clientWidth || 800;
    const height = 500;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    // Layout node positioning algorithm
    const nodes = graphData.nodes.map((node, i) => {
      const angle = (i / graphData.nodes.length) * 2 * Math.PI;
      const radius = node.is_on_bridge_path ? 110 : 180 + (i % 3) * 35;
      return {
        ...node,
        x: width / 2 + Math.cos(angle) * radius,
        y: height / 2 + Math.sin(angle) * radius
      };
    });

    const links = graphData.links.map(link => {
      const sourceNode = nodes.find(n => n.id === link.source) || nodes[0];
      const targetNode = nodes.find(n => n.id === link.target) || nodes[1];
      return { ...link, sourceNode, targetNode };
    });

    let animationFrameId;

    const render = () => {
      // Repulsion forces
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x;
          const dy = nodes[j].y - nodes[i].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < 140) {
            const force = (140 - dist) / dist * 0.04;
            nodes[i].x -= dx * force;
            nodes[i].y -= dy * force;
            nodes[j].x += dx * force;
            nodes[j].y += dy * force;
          }
        }
      }

      // Spring forces
      links.forEach(link => {
        const dx = link.targetNode.x - link.sourceNode.x;
        const dy = link.targetNode.y - link.sourceNode.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - 110) * 0.015;
        link.sourceNode.x += (dx / dist) * force;
        link.sourceNode.y += (dy / dist) * force;
        link.targetNode.x -= (dx / dist) * force;
        link.targetNode.y -= (dy / dist) * force;
      });

      // Keep within canvas center bounds
      nodes.forEach(node => {
        node.x = Math.max(40, Math.min(width - 40, node.x));
        node.y = Math.max(40, Math.min(height - 40, node.y));
      });

      // Render Light Theme Canvas
      ctx.clearRect(0, 0, width, height);

      ctx.save();
      // Apply Zoom around center
      ctx.translate(width / 2, height / 2);
      ctx.scale(zoom, zoom);
      ctx.translate(-width / 2, -height / 2);

      // Draw Edges
      links.forEach(link => {
        ctx.beginPath();
        ctx.moveTo(link.sourceNode.x, link.sourceNode.y);
        ctx.lineTo(link.targetNode.x, link.targetNode.y);

        if (link.is_bridge) {
          ctx.strokeStyle = '#7c3aed';
          ctx.lineWidth = 3.5;
          ctx.shadowColor = 'rgba(124, 58, 237, 0.3)';
          ctx.shadowBlur = 8;
        } else {
          ctx.strokeStyle = '#cbd5e1';
          ctx.lineWidth = 1.2;
          ctx.shadowBlur = 0;
        }
        ctx.stroke();
        ctx.shadowBlur = 0;
      });

      // Draw Nodes
      nodes.forEach(node => {
        ctx.beginPath();
        const r = node.is_on_bridge_path ? 14 : 8;
        ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
        
        ctx.fillStyle = node.color;
        ctx.shadowColor = 'rgba(15, 23, 42, 0.15)';
        ctx.shadowBlur = node.is_on_bridge_path ? 10 : 3;
        ctx.fill();
        ctx.shadowBlur = 0;

        if (node.is_on_bridge_path) {
          ctx.strokeStyle = '#7c3aed';
          ctx.lineWidth = 2.5;
          ctx.stroke();
        }

        // Text Labels with legibility stroke halo
        if (node.is_on_bridge_path || node.node_type === 'degree' || node.node_type === 'occupation') {
          ctx.font = node.is_on_bridge_path ? 'bold 11px Inter, sans-serif' : '10px Inter, sans-serif';
          ctx.textAlign = 'center';
          const labelText = node.label.length > 24 ? node.label.slice(0, 22) + '...' : node.label;
          
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 3;
          ctx.strokeText(labelText, node.x, node.y + r + 14);

          ctx.fillStyle = '#0f172a';
          ctx.fillText(labelText, node.x, node.y + r + 14);
        }
      });

      ctx.restore();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [graphData, zoom]);

  return (
    <div ref={containerRef} className="canvas-wrapper" style={{ position: 'relative' }}>
      {/* Legend Header */}
      <div className="canvas-legend" style={{ background: 'rgba(255, 255, 255, 0.92)', backdropFilter: 'blur(8px)', padding: '8px 14px', borderRadius: '12px', border: '1px solid var(--border-color)', boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)' }}>
        <span className="badge badge-purple">● Major Node</span>
        <span className="badge badge-cyan">● ESCO Skill</span>
        <span className="badge badge-amber">● Target Occupation</span>
        <span className="badge badge-green">-- Dijkstra Bridge Path</span>
      </div>

      {/* Interactive Controls */}
      <div style={{ position: 'absolute', bottom: '16px', right: '16px', zIndex: 10, display: 'flex', gap: '6px', background: 'rgba(255, 255, 255, 0.92)', padding: '6px', borderRadius: '12px', border: '1px solid var(--border-color)', boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)' }}>
        <button onClick={() => setZoom(z => Math.min(2.0, z + 0.2))} className="btn btn-secondary" style={{ padding: '6px 10px' }} title="Zoom In">
          <ZoomIn size={16} />
        </button>
        <button onClick={() => setZoom(z => Math.max(0.5, z - 0.2))} className="btn btn-secondary" style={{ padding: '6px 10px' }} title="Zoom Out">
          <ZoomOut size={16} />
        </button>
        <button onClick={() => setZoom(1.0)} className="btn btn-secondary" style={{ padding: '6px 10px' }} title="Reset View">
          <RotateCcw size={16} />
        </button>
      </div>

      <canvas ref={canvasRef} style={{ width: '100%', height: '500px', display: 'block', background: '#f8fafc', borderRadius: '16px' }} />
    </div>
  );
}
