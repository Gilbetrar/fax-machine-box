/**
 * Fax Machine Box - 3D Preview
 * Three.js scene with assembled box, exploded view, and part selection
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { PARTS, CONFIG, COLORS, getScaledDimensions, getScaledPosition, getExplodedOffset, SCALE } from './box-parts.js';

// Scene state
let scene, camera, renderer, controls;
let partMeshes = {};
let selectedPart = null;
let isExploded = false;
let animationId = null;

// Animation state for smooth transitions
const targetPositions = {};
const currentPositions = {};

// Initialize the scene
function init() {
    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);

    // Camera
    const container = document.getElementById('canvas-container');
    const aspect = container.clientWidth / container.clientHeight;
    camera = new THREE.PerspectiveCamera(50, aspect, 0.1, 1000);
    camera.position.set(5, 3, 5);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 2;
    controls.maxDistance = 15;

    // Lighting
    setupLighting();

    // Create all box parts
    createParts();

    // Grid helper for reference
    const gridHelper = new THREE.GridHelper(10, 20, 0x444466, 0x333355);
    gridHelper.position.y = -1.5;
    scene.add(gridHelper);

    // Event listeners
    setupEventListeners();

    // Start render loop
    animate();
}

function setupLighting() {
    // Ambient light
    const ambient = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambient);

    // Main directional light
    const mainLight = new THREE.DirectionalLight(0xffffff, 0.8);
    mainLight.position.set(5, 10, 5);
    mainLight.castShadow = true;
    mainLight.shadow.mapSize.width = 2048;
    mainLight.shadow.mapSize.height = 2048;
    scene.add(mainLight);

    // Fill light
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
    fillLight.position.set(-5, 5, -5);
    scene.add(fillLight);
}

function createParts() {
    Object.entries(PARTS).forEach(([key, part]) => {
        const dims = getScaledDimensions(key);
        const pos = getScaledPosition(key);
        
        // Create geometry
        const geometry = new THREE.BoxGeometry(dims.width, dims.height, dims.depth);
        
        // Create material
        const material = new THREE.MeshStandardMaterial({
            color: part.color,
            roughness: 0.8,
            metalness: 0.1,
        });
        
        // Create mesh
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(pos.x, pos.y, pos.z);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        
        // Store reference data
        mesh.userData = {
            partKey: key,
            partName: part.name,
            dimensions: part.dimensions,
            originalColor: part.color,
        };
        
        // Add to scene and track
        scene.add(mesh);
        partMeshes[key] = mesh;
        
        // Initialize position tracking
        currentPositions[key] = { x: pos.x, y: pos.y, z: pos.z };
        targetPositions[key] = { x: pos.x, y: pos.y, z: pos.z };
    });

    // Add edge lines to drawers for visibility
    ['drawerTop', 'drawerBottom'].forEach(key => {
        const mesh = partMeshes[key];
        const edges = new THREE.EdgesGeometry(mesh.geometry);
        const line = new THREE.LineSegments(
            edges,
            new THREE.LineBasicMaterial({ color: 0x8b7355 })
        );
        mesh.add(line);
    });
}

function setupEventListeners() {
    // Window resize
    window.addEventListener('resize', onWindowResize);
    
    // Mouse click for selection
    renderer.domElement.addEventListener('click', onMouseClick);
    
    // Buttons
    document.getElementById('toggle-explode').addEventListener('click', toggleExplodedView);
    document.getElementById('reset-view').addEventListener('click', resetView);
}

function onWindowResize() {
    const container = document.getElementById('canvas-container');
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
}

function onMouseClick(event) {
    // Calculate mouse position in normalized device coordinates
    const rect = renderer.domElement.getBoundingClientRect();
    const mouse = new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1
    );
    
    // Raycast
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, camera);
    
    const meshArray = Object.values(partMeshes);
    const intersects = raycaster.intersectObjects(meshArray);
    
    if (intersects.length > 0) {
        selectPart(intersects[0].object);
    } else {
        deselectPart();
    }
}

function selectPart(mesh) {
    // Deselect previous
    if (selectedPart && selectedPart !== mesh) {
        selectedPart.material.color.setHex(selectedPart.userData.originalColor);
        selectedPart.material.emissive.setHex(0x000000);
    }
    
    // Select new
    selectedPart = mesh;
    mesh.material.color.setHex(COLORS.highlight);
    mesh.material.emissive.setHex(0x112233);
    
    // Update info panel
    updateInfoPanel(mesh.userData);
}

function deselectPart() {
    if (selectedPart) {
        selectedPart.material.color.setHex(selectedPart.userData.originalColor);
        selectedPart.material.emissive.setHex(0x000000);
        selectedPart = null;
    }
    
    // Reset info panel to show full box
    document.getElementById('part-name').textContent = 'Fax Machine Box';
    document.getElementById('part-width').textContent = CONFIG.SHELL.width + 'mm';
    document.getElementById('part-depth').textContent = CONFIG.SHELL.depth + 'mm';
    document.getElementById('part-height').textContent = CONFIG.SHELL.height + 'mm';
    document.getElementById('part-material').textContent = CONFIG.MATERIAL_THICKNESS + 'mm plywood';
}

function updateInfoPanel(userData) {
    document.getElementById('part-name').textContent = userData.partName;
    document.getElementById('part-width').textContent = userData.dimensions.width.toFixed(1) + 'mm';
    document.getElementById('part-depth').textContent = userData.dimensions.depth.toFixed(1) + 'mm';
    document.getElementById('part-height').textContent = userData.dimensions.height.toFixed(1) + 'mm';
    document.getElementById('part-material').textContent = CONFIG.MATERIAL_THICKNESS + 'mm plywood';
}

function toggleExplodedView() {
    isExploded = !isExploded;
    
    const button = document.getElementById('toggle-explode');
    button.textContent = isExploded ? 'Assembled View' : 'Exploded View';
    
    // Update target positions
    Object.keys(PARTS).forEach(key => {
        const basePos = getScaledPosition(key);
        const offset = getExplodedOffset(key);
        
        if (isExploded) {
            targetPositions[key] = {
                x: basePos.x + offset.x,
                y: basePos.y + offset.y,
                z: basePos.z + offset.z,
            };
        } else {
            targetPositions[key] = {
                x: basePos.x,
                y: basePos.y,
                z: basePos.z,
            };
        }
    });
}

function resetView() {
    // Reset camera
    camera.position.set(5, 3, 5);
    controls.target.set(0, 0, 0);
    controls.update();
    
    // Deselect any selected part
    deselectPart();
    
    // Reset to assembled view
    if (isExploded) {
        toggleExplodedView();
    }
}

function animate() {
    animationId = requestAnimationFrame(animate);
    
    // Smoothly interpolate positions
    const lerpFactor = 0.08;
    Object.keys(partMeshes).forEach(key => {
        const mesh = partMeshes[key];
        const target = targetPositions[key];
        const current = currentPositions[key];
        
        current.x += (target.x - current.x) * lerpFactor;
        current.y += (target.y - current.y) * lerpFactor;
        current.z += (target.z - current.z) * lerpFactor;
        
        mesh.position.set(current.x, current.y, current.z);
    });
    
    controls.update();
    renderer.render(scene, camera);
}

// Start the application
init();
