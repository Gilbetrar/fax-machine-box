import * as THREE from 'three';

// Configuration from config.py
const CONFIG = {
    MATERIAL_THICKNESS: 3.0,
    DRAWER_MATERIAL_THICKNESS: 3.175,
    
    SHELL: {
        width: 304.8,   // 12" external width
        depth: 165.1,   // 6.5" external depth
        height: 127.0,  // 5" external height
    },
    
    DRAWER: {
        width: 222.0,
        depth: 158.0,
        height: 53.0,
    },
    
    PAPER_COMPARTMENT_DEPTH: 76.2,  // 3" internal depth
};

// Calculate internal dimensions
const T = CONFIG.MATERIAL_THICKNESS;
const DT = CONFIG.DRAWER_MATERIAL_THICKNESS;

const SHELL_INTERNAL = {
    width: CONFIG.SHELL.width - 2 * T,
    depth: CONFIG.SHELL.depth - 2 * T,
    height: CONFIG.SHELL.height - T, // No top
};

// Part information for display
export const PART_INFO = {
    'shell-front': {
        name: 'Front Wall',
        description: 'Outer shell front panel with FAX MACHINE engraving',
        dimensions: `${CONFIG.SHELL.width} x ${CONFIG.SHELL.height} x ${T}mm`
    },
    'shell-back': {
        name: 'Back Wall',
        description: 'Outer shell back panel',
        dimensions: `${CONFIG.SHELL.width} x ${CONFIG.SHELL.height} x ${T}mm`
    },
    'shell-left': {
        name: 'Left Wall',
        description: 'Outer shell left side panel',
        dimensions: `${CONFIG.SHELL.depth} x ${CONFIG.SHELL.height} x ${T}mm`
    },
    'shell-right': {
        name: 'Right Wall',
        description: 'Outer shell right side panel',
        dimensions: `${CONFIG.SHELL.depth} x ${CONFIG.SHELL.height} x ${T}mm`
    },
    'shell-bottom': {
        name: 'Bottom Panel',
        description: 'Outer shell bottom',
        dimensions: `${CONFIG.SHELL.width} x ${CONFIG.SHELL.depth} x ${T}mm`
    },
    'divider': {
        name: 'Vertical Divider',
        description: 'Separates paper compartment from drawer bay',
        dimensions: `${SHELL_INTERNAL.depth} x ${CONFIG.SHELL.height - T} x ${T}mm`
    },
    'shelf': {
        name: 'Horizontal Shelf',
        description: 'Divides drawer bay into upper and lower sections',
        dimensions: `${SHELL_INTERNAL.width - CONFIG.PAPER_COMPARTMENT_DEPTH} x ${SHELL_INTERNAL.depth} x ${T}mm`
    },
    'drawer-top': {
        name: 'Top Drawer',
        description: 'Upper drawer with finger-notch pull',
        dimensions: `${CONFIG.DRAWER.width} x ${CONFIG.DRAWER.depth} x ${CONFIG.DRAWER.height}mm`
    },
    'drawer-bottom': {
        name: 'Bottom Drawer',
        description: 'Lower drawer with finger-notch pull',
        dimensions: `${CONFIG.DRAWER.width} x ${CONFIG.DRAWER.depth} x ${CONFIG.DRAWER.height}mm`
    },
    'lid-sliding': {
        name: 'Sliding Lid',
        description: 'Covers paper compartment, slides in grooves',
        dimensions: `${CONFIG.PAPER_COMPARTMENT_DEPTH + 20} x ${SHELL_INTERNAL.depth - 10} x ${DT}mm`
    },
    'lid-flat': {
        name: 'Flat Tabbed Lid',
        description: 'Covers drawer bay, sits on top with alignment tabs',
        dimensions: `${SHELL_INTERNAL.width - CONFIG.PAPER_COMPARTMENT_DEPTH + 10} x ${SHELL_INTERNAL.depth + 10} x ${DT}mm`
    }
};

// Colors for different parts
const COLORS = {
    shell: 0xd4a574,      // Light wood
    divider: 0xc49a64,    // Slightly darker
    shelf: 0xc49a64,
    drawer: 0xe8c99b,     // Lighter for drawers
    lid: 0xf0dcc0,        // Lightest for lids
};

function createMaterial(color) {
    return new THREE.MeshStandardMaterial({
        color: color,
        roughness: 0.8,
        metalness: 0.0,
    });
}

function createPart(name, geometry, color, position, explodeOffset) {
    const material = createMaterial(color);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(position);
    
    // Add edges for visibility
    const edges = new THREE.EdgesGeometry(geometry);
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x333333, opacity: 0.5, transparent: true });
    const line = new THREE.LineSegments(edges, lineMaterial);
    mesh.add(line);
    
    return {
        name,
        mesh,
        explodeOffset: explodeOffset || new THREE.Vector3(0, 0, 0)
    };
}

export function createBoxParts() {
    const parts = [];
    const W = CONFIG.SHELL.width;
    const D = CONFIG.SHELL.depth;
    const H = CONFIG.SHELL.height;
    const paperDepth = CONFIG.PAPER_COMPARTMENT_DEPTH;
    
    // Shell Front Wall
    const frontGeom = new THREE.BoxGeometry(W, H, T);
    parts.push(createPart(
        'shell-front',
        frontGeom,
        COLORS.shell,
        new THREE.Vector3(W/2, H/2, T/2),
        new THREE.Vector3(0, 0, -80)
    ));
    
    // Shell Back Wall
    const backGeom = new THREE.BoxGeometry(W, H, T);
    parts.push(createPart(
        'shell-back',
        backGeom,
        COLORS.shell,
        new THREE.Vector3(W/2, H/2, D - T/2),
        new THREE.Vector3(0, 0, 80)
    ));
    
    // Shell Left Wall
    const leftGeom = new THREE.BoxGeometry(T, H, D - 2*T);
    parts.push(createPart(
        'shell-left',
        leftGeom,
        COLORS.shell,
        new THREE.Vector3(T/2, H/2, D/2),
        new THREE.Vector3(-80, 0, 0)
    ));
    
    // Shell Right Wall
    const rightGeom = new THREE.BoxGeometry(T, H, D - 2*T);
    parts.push(createPart(
        'shell-right',
        rightGeom,
        COLORS.shell,
        new THREE.Vector3(W - T/2, H/2, D/2),
        new THREE.Vector3(80, 0, 0)
    ));
    
    // Shell Bottom
    const bottomGeom = new THREE.BoxGeometry(W - 2*T, T, D - 2*T);
    parts.push(createPart(
        'shell-bottom',
        bottomGeom,
        COLORS.shell,
        new THREE.Vector3(W/2, T/2, D/2),
        new THREE.Vector3(0, -80, 0)
    ));
    
    // Vertical Divider (separates paper from drawers)
    const dividerX = T + paperDepth;
    const dividerGeom = new THREE.BoxGeometry(T, H - T, D - 2*T);
    parts.push(createPart(
        'divider',
        dividerGeom,
        COLORS.divider,
        new THREE.Vector3(dividerX + T/2, T + (H-T)/2, D/2),
        new THREE.Vector3(-40, 50, 0)
    ));
    
    // Horizontal Shelf (in drawer bay, splits into top/bottom drawer)
    const drawerBayWidth = W - 2*T - paperDepth - T;
    const shelfY = T + CONFIG.DRAWER.height + DT;
    const shelfGeom = new THREE.BoxGeometry(drawerBayWidth, T, D - 2*T);
    parts.push(createPart(
        'shelf',
        shelfGeom,
        COLORS.shelf,
        new THREE.Vector3(dividerX + T + drawerBayWidth/2, shelfY + T/2, D/2),
        new THREE.Vector3(50, 30, 0)
    ));
    
    // Bottom Drawer
    const drawerW = CONFIG.DRAWER.width;
    const drawerD = CONFIG.DRAWER.depth;
    const drawerH = CONFIG.DRAWER.height;
    const drawerStartX = dividerX + T + 5; // Small clearance
    
    const bottomDrawerGeom = new THREE.BoxGeometry(drawerW, drawerH, drawerD);
    parts.push(createPart(
        'drawer-bottom',
        bottomDrawerGeom,
        COLORS.drawer,
        new THREE.Vector3(drawerStartX + drawerW/2, T + drawerH/2, T + drawerD/2),
        new THREE.Vector3(100, -20, -100)
    ));
    
    // Top Drawer
    const topDrawerY = shelfY + T;
    const topDrawerGeom = new THREE.BoxGeometry(drawerW, drawerH, drawerD);
    parts.push(createPart(
        'drawer-top',
        topDrawerGeom,
        COLORS.drawer,
        new THREE.Vector3(drawerStartX + drawerW/2, topDrawerY + drawerH/2, T + drawerD/2),
        new THREE.Vector3(100, 20, -100)
    ));
    
    // Sliding Lid (paper compartment)
    const slidingLidW = paperDepth + 15;
    const slidingLidD = D - 2*T - 10;
    const slidingLidGeom = new THREE.BoxGeometry(slidingLidW, DT, slidingLidD);
    parts.push(createPart(
        'lid-sliding',
        slidingLidGeom,
        COLORS.lid,
        new THREE.Vector3(T + slidingLidW/2, H - DT/2, D/2),
        new THREE.Vector3(-60, 100, 0)
    ));
    
    // Flat Tabbed Lid (drawer bay)
    const flatLidW = drawerBayWidth + 10;
    const flatLidD = D - 2*T + 10;
    const flatLidGeom = new THREE.BoxGeometry(flatLidW, DT, flatLidD);
    parts.push(createPart(
        'lid-flat',
        flatLidGeom,
        COLORS.lid,
        new THREE.Vector3(dividerX + T + drawerBayWidth/2, H - DT/2, D/2),
        new THREE.Vector3(60, 100, 0)
    ));
    
    return parts;
}
