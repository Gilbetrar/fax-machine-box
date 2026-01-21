/**
 * Fax Machine Box - 3D Preview
 * Three.js scene with assembled box, exploded view, and part selection
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { createBoxParts, PART_INFO } from './box-parts.js';

// Configuration for camera positioning (mm scale)
const SHELL = { width: 304.8, depth: 165.1, height: 127.0 };

// Scene state
let scene, camera, renderer, controls;
let parts = [];
let selectedPart = null;
let isExploded = false;

// Initialize the scene
function init() {
    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);

    // Camera
    const container = document.getElementById('canvas-container');
    const aspect = container.clientWidth / container.clientHeight;
    camera = new THREE.PerspectiveCamera(50, aspect, 1, 2000);
    camera.position.set(400, 300, 400);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // Controls - orbit around center of the box
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(SHELL.width / 2, SHELL.height / 2, SHELL.depth / 2);
    controls.minDistance = 200;
    controls.maxDistance = 1000;
    controls.update();

    // Lighting
    setupLighting();

    // Create all box parts
    parts = createBoxParts();
    parts.forEach(part => {
        scene.add(part.mesh);
        // Store original position for animation
        part.originalPosition = part.mesh.position.clone();
    });

    // Grid helper for reference
    const gridHelper = new THREE.GridHelper(500, 20, 0x444466, 0x333355);
    gridHelper.position.y = -5;
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
    mainLight.position.set(400, 400, 300);
    scene.add(mainLight);

    // Fill light from back
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
    fillLight.position.set(-300, 200, -300);
    scene.add(fillLight);
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

// Store original materials for highlighting
const originalMaterials = new Map();

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

    const meshArray = parts.map(p => p.mesh);
    const intersects = raycaster.intersectObjects(meshArray);

    // Reset previous selection
    if (selectedPart) {
        const prevMesh = parts.find(p => p.name === selectedPart)?.mesh;
        if (prevMesh && originalMaterials.has(prevMesh)) {
            prevMesh.material = originalMaterials.get(prevMesh);
        }
    }

    if (intersects.length > 0) {
        const clickedMesh = intersects[0].object;
        const part = parts.find(p => p.mesh === clickedMesh);

        if (part) {
            selectedPart = part.name;
            // Store original material if not already stored
            if (!originalMaterials.has(clickedMesh)) {
                originalMaterials.set(clickedMesh, clickedMesh.material);
            }
            // Create highlight material
            clickedMesh.material = new THREE.MeshStandardMaterial({
                color: 0x4cc9f0,
                roughness: 0.5,
                metalness: 0.2,
                emissive: 0x112244,
            });
            updateInfoPanel(part.name);
        }
    } else {
        selectedPart = null;
        resetInfoPanel();
    }
}

function updateInfoPanel(partName) {
    const info = PART_INFO[partName];
    if (info) {
        document.getElementById('part-name').textContent = info.name;
        // Parse dimensions string to extract values
        const dims = info.dimensions.replace('mm', '').split(' x ');
        document.getElementById('part-width').textContent = dims[0] + 'mm';
        document.getElementById('part-depth').textContent = (dims[1] || dims[0]) + 'mm';
        document.getElementById('part-height').textContent = (dims[2] || dims[1] || dims[0]).replace('mm', '') + 'mm';
        document.getElementById('part-material').textContent = '3.175mm plywood';
    }
}

function resetInfoPanel() {
    document.getElementById('part-name').textContent = 'Fax Machine Box';
    document.getElementById('part-width').textContent = SHELL.width + 'mm';
    document.getElementById('part-depth').textContent = SHELL.depth + 'mm';
    document.getElementById('part-height').textContent = SHELL.height + 'mm';
    document.getElementById('part-material').textContent = '3.175mm plywood';
}

function toggleExplodedView() {
    isExploded = !isExploded;

    const button = document.getElementById('toggle-explode');
    button.textContent = isExploded ? 'Assembled View' : 'Exploded View';
    button.classList.toggle('active', isExploded);

    // Animate parts to exploded or assembled positions
    parts.forEach(part => {
        const target = part.originalPosition.clone();
        if (isExploded && part.explodeOffset) {
            target.add(part.explodeOffset);
        }
        animatePosition(part.mesh, target);
    });
}

function animatePosition(mesh, targetPos) {
    const startPos = mesh.position.clone();
    const duration = 500;
    const startTime = Date.now();

    function update() {
        const elapsed = Date.now() - startTime;
        const t = Math.min(elapsed / duration, 1);
        // Ease out cubic
        const eased = 1 - Math.pow(1 - t, 3);

        mesh.position.lerpVectors(startPos, targetPos, eased);

        if (t < 1) {
            requestAnimationFrame(update);
        }
    }
    update();
}

function resetView() {
    // Reset camera
    camera.position.set(400, 300, 400);
    controls.target.set(SHELL.width / 2, SHELL.height / 2, SHELL.depth / 2);
    controls.update();

    // Deselect any selected part
    if (selectedPart) {
        const prevMesh = parts.find(p => p.name === selectedPart)?.mesh;
        if (prevMesh && originalMaterials.has(prevMesh)) {
            prevMesh.material = originalMaterials.get(prevMesh);
        }
        selectedPart = null;
        resetInfoPanel();
    }

    // Reset to assembled view if currently exploded
    if (isExploded) {
        toggleExplodedView();
    }
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

// Start the application
init();
