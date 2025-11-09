import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

let scene, camera, renderer, controls, labelRenderer;
let blockWireframe = null;
let itemMeshes = [];
let itemLabels = [];
let currentBlockDims = [0, 0, 0];
let currentOpacity = 1.0;

// Генерация цвета для каждой заготовки на основе ID (уникальные яркие цвета)
function getItemColor(itemId, itemIndex = 0) {
    // Используем индекс для последовательности цветов
    const hues = [0, 30, 60, 120, 180, 210, 240, 270, 300, 330]; // Разные оттенки
    const hue = hues[itemIndex % hues.length];
    
    // Добавляем вариацию на основе ID для уникальности
    let hash = 0;
    for (let i = 0; i < itemId.length; i++) {
        hash = itemId.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hueOffset = (Math.abs(hash) % 20) - 10; // -10 до +10 градусов
    
    const saturation = 75 + (Math.abs(hash) % 20); // 75-95%
    const lightness = 50 + (Math.abs(hash) % 15); // 50-65%
    
    return new THREE.Color().setHSL((hue + hueOffset) / 360, saturation / 100, lightness / 100);
}

// Карта цветов для заготовок
const itemColorMap = {};

function init3D() {
    const canvas = document.getElementById('canvas');
    if (!canvas) {
        console.error('Canvas element not found!');
        return;
    }
    console.log('Initializing 3D scene...');
    renderer = new THREE.WebGLRenderer({canvas, antialias: true});
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    
    // CSS2D Renderer для текста
    labelRenderer = new CSS2DRenderer();
    labelRenderer.setSize(canvas.clientWidth, canvas.clientHeight);
    labelRenderer.domElement.style.position = 'absolute';
    labelRenderer.domElement.style.top = '0';
    labelRenderer.domElement.style.pointerEvents = 'none';
    canvas.parentElement.appendChild(labelRenderer.domElement);
    
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8f9fa);
    
    const aspect = canvas.clientWidth / canvas.clientHeight;
    camera = new THREE.PerspectiveCamera(45, aspect, 1, 100000);
    
    // Начальная позиция камеры
    camera.position.set(2000, 2000, 2000);
    camera.lookAt(0, 0, 0);
    
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enabled = true; // Включаем вращение мышкой
    controls.target.set(0, 0, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    
    // Улучшенное освещение
    const light1 = new THREE.DirectionalLight(0xffffff, 1.0);
    light1.position.set(1000, 2000, 1000);
    light1.castShadow = true;
    light1.shadow.mapSize.width = 2048;
    light1.shadow.mapSize.height = 2048;
    scene.add(light1);
    
    const light2 = new THREE.DirectionalLight(0xffffff, 0.4);
    light2.position.set(-1000, 500, -1000);
    scene.add(light2);
    
    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    
    // Настройка ползунков
    setupControls();

    // Экспорт в window для app_patch.js
    window.scene = scene;
    window.camera = camera;
    window.renderer = renderer;
    window.controls = controls;
    window.labelRenderer = labelRenderer;
    window.currentOpacity = currentOpacity;
    window.currentBlockDims = currentBlockDims;
    window.itemMeshes = itemMeshes;
    window.itemLabels = itemLabels;
    window.blockWireframe = blockWireframe;

    // Экспорт функций
    window.clearScene = clearScene;
    window.addBlockWireframe = addBlockWireframe;
    window.addBox = addBox;
    window.visualizeSubBlocks = visualizeSubBlocks;
    window.getItemColor = getItemColor;
    window.buildCuttingTreeHTML = buildCuttingTreeHTML;

    animate();
}

function setupControls() {
    const opacitySlider = document.getElementById('opacity-slider');
    const opacityValue = document.getElementById('opacity-value');
    
    opacitySlider.addEventListener('input', (e) => {
        currentOpacity = parseInt(e.target.value) / 100;
        opacityValue.textContent = Math.round(currentOpacity * 100) + '%';
        updateOpacity(currentOpacity);
    });
}

function updateOpacity(opacity) {
    itemMeshes.forEach(mesh => {
        if (mesh.material) {
            // Обновляем прозрачность для материалов
            if (mesh.material.opacity !== undefined) {
                mesh.material.opacity = opacity;
                mesh.material.transparent = opacity < 1.0;
            }
            // Для LineSegments (ребер) тоже обновляем прозрачность
            if (mesh instanceof THREE.LineSegments) {
                mesh.material.opacity = opacity;
                mesh.material.transparent = opacity < 1.0;
            }
        }
    });
}

function animate() {
    requestAnimationFrame(animate);
    if (controls) controls.update();
    if (renderer && scene && camera) {
        renderer.render(scene, camera);
    }
    if (labelRenderer && scene && camera) {
        labelRenderer.render(scene, camera);
    }
}

function clearScene() {
    if (!scene) return;
    
    // Удаляем все объекты кроме света
    const toRemove = [];
    for (let i = 0; i < scene.children.length; i++) {
        const obj = scene.children[i];
        if (!(obj instanceof THREE.Light)) {
            toRemove.push(obj);
        }
    }
    toRemove.forEach(obj => {
        scene.remove(obj);
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
            if (Array.isArray(obj.material)) {
                obj.material.forEach(m => m.dispose());
            } else {
                obj.material.dispose();
            }
        }
    });
    
    itemMeshes = [];
    itemLabels = [];
    blockWireframe = null;
    
    // Восстанавливаем свет, если его нет
    if (scene.children.filter(c => c instanceof THREE.Light).length === 0) {
        const light1 = new THREE.DirectionalLight(0xffffff, 1.0);
        light1.position.set(1000, 2000, 1000);
        scene.add(light1);
        const light2 = new THREE.DirectionalLight(0xffffff, 0.4);
        light2.position.set(-1000, 500, -1000);
        scene.add(light2);
        scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    }
}

// Создание проволочной рамки блока (штрихпунктирная)
function addBlockWireframe(x, y, z, L, W, H) {
    if (!scene) return null;
    
    // Используем LineDashedMaterial для пунктирных линий
    const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(L, H, W));
    const material = new THREE.LineDashedMaterial({ 
        color: 0x888888, 
        linewidth: 2,
        dashSize: 20,
        gapSize: 10,
        scale: 1
    });
    
    const wireframe = new THREE.LineSegments(edges, material);
    wireframe.computeLineDistances(); // Необходимо для LineDashedMaterial
    wireframe.position.set(x + L/2, z + H/2, y + W/2);
    scene.add(wireframe);
    
    return wireframe;
}

function addBox(x, y, z, L, W, H, color, opacity = 1.0, itemId = null, isSubBlock = false) {
    if (!scene) return null;
    if (L <= 0 || W <= 0 || H <= 0) return null;

    const geo = new THREE.BoxGeometry(L, H, W);

    // Для sub-blocks используем серый прозрачный материал
    const mat = isSubBlock
        ? new THREE.MeshPhongMaterial({
            color: 0xaaaaaa,  // Серый цвет для заготовок
            transparent: true,
            opacity: 0.15,  // Низкая прозрачность
            shininess: 10,
            specular: 0x111111,
            flatShading: false,
            wireframe: false
        })
        : new THREE.MeshPhongMaterial({
            color: color,
            transparent: true,
            opacity: opacity,
            shininess: 30,
            specular: 0x222222,
            flatShading: false
        });

    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(x + L/2, z + H/2, y + W/2);
    mesh.castShadow = !isSubBlock;  // Sub-blocks не отбрасывают тени
    mesh.receiveShadow = true;

    if (itemId) {
        mesh.userData.itemId = itemId;
    }
    mesh.userData.isSubBlock = isSubBlock;

    scene.add(mesh);
    itemMeshes.push(mesh);

    // Добавляем ребра (для sub-blocks серые пунктирные, для items черные сплошные)
    const edges = new THREE.EdgesGeometry(geo);
    const edgeMaterial = isSubBlock
        ? new THREE.LineDashedMaterial({
            color: 0x888888,
            linewidth: 1,
            dashSize: 10,
            gapSize: 5
        })
        : new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 2 });

    const edgeLines = new THREE.LineSegments(edges, edgeMaterial);
    if (isSubBlock) {
        edgeLines.computeLineDistances();  // Для пунктирных линий
    }
    edgeLines.position.copy(mesh.position);
    scene.add(edgeLines);
    itemMeshes.push(edgeLines);

    // ID labels УБРАНЫ по просьбе пользователя - мешают визуализации
    // Цвет детали определяется по item_id, смотри таблицу для соответствия

    if (isSubBlock) {
        // Для sub-blocks показываем размеры
        const labelDiv = document.createElement('div');
        labelDiv.className = 'subblock-label';
        labelDiv.textContent = `${Math.round(L)}×${Math.round(W)}×${Math.round(H)}`;
        labelDiv.style.color = '#666666';
        labelDiv.style.fontSize = '11px';
        labelDiv.style.fontWeight = 'normal';
        labelDiv.style.textAlign = 'center';
        labelDiv.style.background = 'rgba(255,255,255,0.5)';
        labelDiv.style.padding = '1px 4px';
        labelDiv.style.borderRadius = '2px';
        labelDiv.style.pointerEvents = 'none';
        labelDiv.style.userSelect = 'none';

        const label = new CSS2DObject(labelDiv);
        label.position.set(0, 0, 0); // В центре заготовки
        mesh.add(label);
        itemLabels.push(label);
    }

    return mesh;
}

// Визуализация sub-blocks из cutting_tree
function visualizeSubBlocks(cuttingTree) {
    if (!cuttingTree || !cuttingTree.nodes) return;

    // Рекурсивная функция для обхода дерева узлов
    function renderNode(node) {
        if (!node) return;

        // Визуализируем только sub-blocks (промежуточные заготовки)
        if (node.type === 'sub-block') {
            const dims = node.dimensions;
            const origin = node.origin;

            // Добавляем серую прозрачную заготовку
            addBox(
                origin.x,
                origin.y,
                origin.z,
                dims.L,
                dims.W,
                dims.H,
                0xaaaaaa,  // Серый цвет (не используется из-за isSubBlock=true)
                0.15,      // Низкая прозрачность
                null,      // Нет itemId
                true       // isSubBlock = true
            );
        }

        // Рекурсивно обрабатываем дочерние узлы
        if (node.children && node.children.length > 0) {
            node.children.forEach(child => renderNode(child));
        }
    }

    // Начинаем с корневого узла
    if (cuttingTree.nodes.length > 0) {
        renderNode(cuttingTree.nodes[0]);
    }
}

// Построение дерева резов с последовательностью (новый формат с cutting_tree)
function buildCuttingTreeHTML(cuttingTree) {
    if (!cuttingTree || !cuttingTree.sequence) return '';

    let html = '<div style="font-family: monospace; font-size: 12px;">';

    // Заголовок
    html += `<div style="background: #2196F3; color: white; padding: 10px; border-radius: 3px; margin-bottom: 10px;">`;
    html += `<strong>Программа раскроя (Cutting Program)</strong><br>`;
    html += `<small>Всего операций: ${cuttingTree.total_nodes || 0} | Резов: ${cuttingTree.total_cuts || 0} | Деталей: ${cuttingTree.total_items || 0}</small>`;
    html += `</div>`;

    // Проверка конфликтов
    if (cuttingTree.conflicts && cuttingTree.conflicts.length > 0) {
        html += `<div style="background: #ff9800; color: white; padding: 8px; border-radius: 3px; margin-bottom: 10px;">`;
        html += `<strong>⚠️ Обнаружены конфликты резов: ${cuttingTree.conflicts.length}</strong><br>`;
        cuttingTree.conflicts.forEach(conflict => {
            html += `<small>${conflict.description}</small><br>`;
        });
        html += `</div>`;
    } else {
        html += `<div style="background: #4caf50; color: white; padding: 8px; border-radius: 3px; margin-bottom: 10px;">`;
        html += `<strong>✓ Конфликтов резов не обнаружено</strong>`;
        html += `</div>`;
    }

    // Последовательность операций
    html += `<table style="width: 100%; border-collapse: collapse; background: white;">`;
    html += `<thead style="background: #f5f5f5; font-weight: bold;">`;
    html += `<tr>`;
    html += `<th style="padding: 8px; border: 1px solid #ddd; text-align: center; width: 40px;">№</th>`;
    html += `<th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Операция</th>`;
    html += `<th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Описание</th>`;
    html += `<th style="padding: 8px; border: 1px solid #ddd; text-align: right; width: 100px;">Объем (mm³)</th>`;
    html += `</tr>`;
    html += `</thead>`;
    html += `<tbody>`;

    cuttingTree.sequence.forEach((step, index) => {
        const node = step.node;
        const bgColor = index % 2 === 0 ? '#ffffff' : '#f9f9f9';
        let operationColor = '#000';
        let operationIcon = '';

        if (step.operation === 'START') {
            operationColor = '#2196F3';
            operationIcon = '📦';
        } else if (step.operation === 'CUT') {
            operationColor = '#ff5722';
            operationIcon = '✂️';
        } else if (step.operation === 'SUB-BLOCK') {
            operationColor = '#9c27b0';
            operationIcon = '📐';
        } else if (step.operation === 'ITEM') {
            operationColor = '#4caf50';
            operationIcon = '✓';
        }

        const indent = '  '.repeat(node.depth || 0);
        const volume = node.volume ? node.volume.toFixed(0) : '—';

        html += `<tr style="background: ${bgColor};">`;
        html += `<td style="padding: 6px 8px; border: 1px solid #ddd; text-align: center; font-weight: bold; color: ${operationColor};">${step.seq}</td>`;
        html += `<td style="padding: 6px 8px; border: 1px solid #ddd; font-weight: bold; color: ${operationColor};">${operationIcon} ${step.operation}</td>`;
        html += `<td style="padding: 6px 8px; border: 1px solid #ddd; font-family: monospace; font-size: 11px;">${indent}${step.description}</td>`;
        html += `<td style="padding: 6px 8px; border: 1px solid #ddd; text-align: right; font-size: 11px;">${volume}</td>`;
        html += `</tr>`;
    });

    html += `</tbody>`;
    html += `</table>`;
    html += `</div>`;

    return html;
}

// Рекурсивное построение дерева реза (новый формат)
function buildTreeHTMLNew(tree, level = 0, prefix = '') {
    if (!tree) return '';
    
    let html = '';
    const indent = '  '.repeat(level);
    
    // Новый формат
    if (tree.item_id && !tree.cut_dir) {
        const L = tree.length || 0;
        const W = tree.width || 0;
        const H = tree.height || 0;
        html += `${indent}${prefix}Item ${tree.item_id} ${L}x${W}x${H}\n`;
    } else if (tree.cut_dir) {
        const axis = tree.cut_dir || '?';
        const pos = tree.cut_pos || 0;
        const L = tree.length || 0;
        const W = tree.width || 0;
        const H = tree.height || 0;
        html += `${indent}${prefix}<${axis}> ${L}x${W}x${H} (${pos})\n`;
        
        if (tree.left_pattern) {
            html += buildTreeHTMLNew(tree.left_pattern, level + 1, '');
        }
        if (tree.right_pattern) {
            html += buildTreeHTMLNew(tree.right_pattern, level + 1, '');
        }
    }
    
    return html;
}

// Старая функция для совместимости
function buildTreeHTML(tree, level = 0, prefix = '') {
    if (!tree) return '';
    
    // Проверяем формат
    if (tree.length !== undefined || tree.cut_dir !== undefined) {
        return buildTreeHTMLNew(tree, level, prefix);
    }
    
    // Старый формат
    let html = '';
    const indent = '  '.repeat(level);
    
    if (tree.kind === 'leaf' && tree.item_id) {
        const [L, W, H] = tree.box || [0, 0, 0];
        html += `${indent}${prefix}${tree.item_id} ${L}x${W}x${H}\n`;
    } else if (tree.kind === 'cut') {
        const axis = tree.axis || '?';
        const pos = tree.pos || 0;
        const [L, W, H] = tree.box || [0, 0, 0];
        
        html += `${indent}${prefix}<${axis}> ${L}x${W}x${H} (${pos})\n`;
        
        if (tree.children && tree.children.length >= 2) {
            html += buildTreeHTML(tree.children[0], level + 1, '');
            html += buildTreeHTML(tree.children[1], level + 1, '');
        }
    }
    
    return html;
}

// Новая функция для работы с новым форматом дерева
function drawTreeNew(tree, blockDims, kerf, origin = [0, 0, 0], itemColorMap = {}, itemIndexMap = {}) {
    if (!tree) return;
    
    const [L, W, H] = [tree.length || blockDims[0], tree.width || blockDims[1], tree.height || blockDims[2]];
    
    // Лист с деталью
    if (tree.item_id && !tree.cut_dir) {
        let color;
        if (itemColorMap[tree.item_id]) {
            color = itemColorMap[tree.item_id];
        } else {
            itemIndexMap[tree.item_id] = Object.keys(itemColorMap).length;
            color = getItemColor(tree.item_id, itemIndexMap[tree.item_id]);
            itemColorMap[tree.item_id] = color;
        }
        addBox(origin[0], origin[1], origin[2], L, W, H, color, currentOpacity, tree.item_id);
        return;
    }
    
    // Разрез
    if (tree.cut_dir && (tree.left_pattern || tree.right_pattern)) {
        const cutDir = tree.cut_dir;
        const pos = tree.cut_pos || 0;
        
        if (tree.left_pattern) {
            drawTreeNew(tree.left_pattern, blockDims, kerf, origin, itemColorMap, itemIndexMap);
        }
        
        if (tree.right_pattern) {
            let newOrigin = [...origin];
            if (cutDir === 'V') {  // Разрез по длине (X)
                newOrigin[0] = origin[0] + pos + kerf;
            } else if (cutDir === 'D') {  // Разрез по ширине (Y)
                newOrigin[1] = origin[1] + pos + kerf;
            } else if (cutDir === 'H') {  // Разрез по высоте (Z)
                newOrigin[2] = origin[2] + pos + kerf;
            }
            drawTreeNew(tree.right_pattern, blockDims, kerf, newOrigin, itemColorMap, itemIndexMap);
        }
    }
}

// Старая функция для совместимости
function drawTree(tree, blockDims, kerf, origin = [0, 0, 0], itemColorMap = {}, itemIndexMap = {}) {
    if (!tree) return;
    
    // Проверяем формат дерева
    if (tree.length !== undefined || tree.cut_dir !== undefined) {
        // Новый формат
        return drawTreeNew(tree, blockDims, kerf, origin, itemColorMap, itemIndexMap);
    }
    
    // Старый формат
    const [L, W, H] = tree.box || blockDims;
    
    if (tree.kind === 'leaf' && tree.item_id) {
        let color;
        if (itemColorMap[tree.item_id]) {
            color = itemColorMap[tree.item_id];
        } else {
            itemIndexMap[tree.item_id] = Object.keys(itemColorMap).length;
            color = getItemColor(tree.item_id, itemIndexMap[tree.item_id]);
            itemColorMap[tree.item_id] = color;
        }
        addBox(origin[0], origin[1], origin[2], L, W, H, color, currentOpacity, tree.item_id);
        return;
    }
    
    if (tree.kind === 'cut' && tree.children && tree.children.length >= 2) {
        const axis = tree.axis;
        const pos = tree.pos || 0;
        
        if (axis === 'H') {
            drawTree(tree.children[0], blockDims, kerf, origin, itemColorMap, itemIndexMap);
            drawTree(tree.children[1], blockDims, kerf, [origin[0] + pos + kerf, origin[1], origin[2]], itemColorMap, itemIndexMap);
        } else if (axis === 'V') {
            drawTree(tree.children[0], blockDims, kerf, origin, itemColorMap, itemIndexMap);
            drawTree(tree.children[1], blockDims, kerf, [origin[0], origin[1] + pos + kerf, origin[2]], itemColorMap, itemIndexMap);
        } else if (axis === 'D') {
            drawTree(tree.children[0], blockDims, kerf, origin, itemColorMap, itemIndexMap);
            drawTree(tree.children[1], blockDims, kerf, [origin[0], origin[1], origin[2] + pos + kerf], itemColorMap, itemIndexMap);
        }
    }
}

// Подсчет статистики по заготовкам (новый формат)
function calculateStatisticsNew(tree, items, blockDims) {
    const stats = {
        items: {},
        totalFilled: 0,
        totalWaste: 0,
        totalVolume: blockDims[0] * blockDims[1] * blockDims[2]
    };
    
    function countItems(node) {
        // Новый формат
        if (node.item_id && !node.cut_dir) {
            const volume = (node.length || 0) * (node.width || 0) * (node.height || 0);
            if (!stats.items[node.item_id]) {
                stats.items[node.item_id] = {
                    id: node.item_id,
                    count: 0,
                    volume: 0
                };
            }
            stats.items[node.item_id].count++;
            stats.items[node.item_id].volume += volume;
            stats.totalFilled += volume;
        }
        
        // Старый формат
        if (node.kind === 'leaf' && node.item_id) {
            const [L, W, H] = node.box || [0, 0, 0];
            const volume = L * W * H;
            if (!stats.items[node.item_id]) {
                stats.items[node.item_id] = {
                    id: node.item_id,
                    count: 0,
                    volume: 0
                };
            }
            stats.items[node.item_id].count++;
            stats.items[node.item_id].volume += volume;
            stats.totalFilled += volume;
        }
        
        if (node.left_pattern) countItems(node.left_pattern);
        if (node.right_pattern) countItems(node.right_pattern);
        if (node.children) {
            node.children.forEach(countItems);
        }
    }
    
    if (tree) {
        countItems(tree);
    }
    
    stats.totalWaste = stats.totalVolume - stats.totalFilled;
    stats.fillPercent = stats.totalVolume > 0 ? (stats.totalFilled / stats.totalVolume * 100) : 0;
    stats.wastePercent = stats.totalVolume > 0 ? (stats.totalWaste / stats.totalVolume * 100) : 0;
    
    return stats;
}

// Старая функция для совместимости
function calculateStatistics(tree, items, blockDims) {
    return calculateStatisticsNew(tree, items, blockDims);
}

document.getElementById('run').onclick = async () => {
    try {
        const blockL = parseFloat(document.getElementById('blockL').value);
        const blockW = parseFloat(document.getElementById('blockW').value);
        const blockH = parseFloat(document.getElementById('blockH').value);
        const kerf = parseFloat(document.getElementById('kerf').value);
        const allowRotations = document.getElementById('allowRotations').checked;
        const iterations = parseInt(document.getElementById('iterations').value) || 1;
        
        const itemsText = document.getElementById('items').value;
        const items = itemsText.split('\n').filter(l => l.trim()).map(line => {
            const parts = line.split(',');
            const [id, l, w, h, qty] = parts;
            return {
                id: parseInt(id.trim()), 
                l: parseFloat(l), 
                w: parseFloat(w), 
                h: parseFloat(h), 
                qty: parseInt(qty || 1)
            };
        });
        
        document.getElementById('run').disabled = true;
        document.getElementById('run').textContent = 'Вычисление...';
        
        const response = await fetch('/optimize', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                block: {L: blockL, W: blockW, H: blockH},
                items: items,
                tech: {
                    kerf, 
                    allow_rotations: allowRotations
                },
                iterations: iterations
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('API Error:', response.status, errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const result = await response.json();
        console.log('API Response:', result);
        
        if (!result) {
            throw new Error('Не получен ответ от сервера');
        }
        
        // Очистка сцены
        clearScene();
        currentBlockDims = [blockL, blockW, blockH];
        
        // Добавляем проволочную рамку блока
        blockWireframe = addBlockWireframe(0, 0, 0, blockL, blockW, blockH);
        
        // Отрисовка деталей из items_placed (новый формат API)
        const itemColorMap = {};
        const itemIndexMap = {};
        
        if (result.items_placed && result.items_placed.length > 0) {
            // Используем готовые позиции из API
            result.items_placed.forEach(item => {
                const itemId = item.item_id;
                const pos = item.position;
                const dims = item.dimensions;
                
                // Получаем цвет
                if (!itemColorMap[itemId]) {
                    itemIndexMap[itemId] = Object.keys(itemColorMap).length;
                    itemColorMap[itemId] = getItemColor(itemId, itemIndexMap[itemId]);
                }
                
                addBox(pos.x, pos.y, pos.z, dims.l, dims.w, dims.h, 
                       itemColorMap[itemId], currentOpacity, itemId);
            });
        } else if (result.tree) {
            // Fallback: используем дерево (адаптированное для нового формата)
            drawTreeNew(result.tree, [blockL, blockW, blockH], kerf, [0, 0, 0], itemColorMap, itemIndexMap);
        }
        
        // Обновляем позицию камеры
        const maxDim = Math.max(blockL, blockW, blockH);
        camera.position.set(maxDim * 1.5, maxDim * 1.5, maxDim * 1.5);
        controls.target.set(blockL/2, blockH/2, blockW/2);
        controls.update();
        
        // Подсчет статистики из API или из дерева
        let stats;
        if (result.items_placed && result.items_placed.length > 0) {
            // Используем статистику из API
            const totalVolume = blockL * blockW * blockH;
            const totalFilled = result.filled_volume || 0;
            stats = {
                fillPercent: result.utilization || 0,
                wastePercent: 100 - (result.utilization || 0),
                totalFilled: totalFilled,
                totalWaste: result.waste || 0,
                totalVolume: totalVolume,
                items: {}
            };
            
            // Подсчитываем детали
            if (result.item_counts) {
                Object.keys(result.item_counts).forEach(itemId => {
                    stats.items[itemId] = {
                        id: itemId,
                        count: result.item_counts[itemId],
                        volume: 0
                    };
                });
            }
        } else if (result.tree) {
            stats = calculateStatisticsNew(result.tree, items, [blockL, blockW, blockH]);
        } else {
            stats = {
                fillPercent: 0,
                wastePercent: 100,
                totalFilled: 0,
                totalWaste: blockL * blockW * blockH,
                totalVolume: blockL * blockW * blockH,
                items: {}
            };
        }
        
        // Отчет (только проценты)
        let reportHTML = `
            <h3>Отчет по раскладке</h3>
            <div style="background: #fff; padding: 10px; border-radius: 3px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span><strong>Заполнение:</strong></span>
                    <span style="color: #28a745; font-weight: bold; font-size: 18px;">${stats.fillPercent.toFixed(2)}%</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span><strong>Отходы:</strong></span>
                    <span style="color: #dc3545; font-weight: bold; font-size: 18px;">${stats.wastePercent.toFixed(2)}%</span>
                </div>
            </div>
        `;
        
        // Статистика по заготовкам
        if (Object.keys(stats.items).length > 0) {
            reportHTML += `<h4 style="margin-top: 15px; margin-bottom: 8px; font-size: 13px;">Заготовки (ID / Количество):</h4>`;
            reportHTML += `<div style="font-size: 11px; max-height: 200px; overflow-y: auto;">`;
            
            // Сортируем по ID
            const itemsArray = items.map(item => ({
                ...item,
                stats: stats.items[item.id] || { count: 0, volume: 0 }
            })).sort((a, b) => a.id - b.id);
            
            itemsArray.forEach(item => {
                const percent = (item.stats.volume / stats.totalVolume * 100).toFixed(1);
                const color = itemColorMap[item.id] || new THREE.Color(0x888888);
                const colorHex = '#' + color.getHexString();
                reportHTML += `
                    <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #eee; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="display: inline-block; width: 12px; height: 12px; background: ${colorHex}; border-radius: 2px;"></span>
                            <span><strong>Item ${item.id}</strong>: ${item.stats.count} шт.</span>
                        </div>
                        <div style="text-align: right;">
                            <div>${percent}%</div>
                        </div>
                    </div>
                `;
            });
            reportHTML += `</div>`;
        }
        
        // Информация о проверке пересечений
        reportHTML += `
            <div style="margin-top: 15px; padding: 10px; background: #e7f3ff; border-radius: 3px; border-left: 3px solid #2196F3;">
                <h4 style="margin: 0 0 8px 0; font-size: 12px; color: #1976D2;">Проверка пересечений при резе:</h4>
                <p style="margin: 0; font-size: 11px; color: #555;">
                    Алгоритм DP3UK гарантирует отсутствие пересечений:
                </p>
                <ul style="margin: 5px 0 0 0; padding-left: 20px; font-size: 11px; color: #555;">
                    <li>Каждый рез выполняется строго по одной оси (H, V или D)</li>
                    <li>R-points (reduced raster points) гарантируют корректные позиции резов</li>
                    <li>Учитывается количество доступных деталей</li>
                    <li>Дерево реза показывает порядок выполнения всех резов</li>
                </ul>
            </div>
        `;
        
        document.getElementById('result').innerHTML = reportHTML;
        
        // Дерево реза с последовательностью (новое)
        if (result.cutting_tree) {
            const cuttingTreeHTML = buildCuttingTreeHTML(result.cutting_tree);
            if (cuttingTreeHTML) {
                document.getElementById('tree-container').innerHTML = cuttingTreeHTML;
                document.getElementById('tree-view').style.display = 'block';
            }
        } else if (result.tree) {
            // Fallback к старому формату
            const treeHTML = buildTreeHTMLNew(result.tree);
            if (treeHTML) {
                document.getElementById('tree-container').textContent = treeHTML;
                document.getElementById('tree-view').style.display = 'block';
            }
        }
        
    } catch (error) {
        console.error('Error during optimization:', error);
        alert('Ошибка: ' + error.message);
        document.getElementById('result').innerHTML = `
            <h3 style="color: red;">Ошибка</h3>
            <p>${error.message}</p>
        `;
    } finally {
        document.getElementById('run').disabled = false;
        document.getElementById('run').textContent = 'Сгенерировать';
    }
};

window.addEventListener('resize', () => {
    if (renderer && camera) {
        const canvas = document.getElementById('canvas');
        renderer.setSize(canvas.clientWidth, canvas.clientHeight);
        if (labelRenderer) {
            labelRenderer.setSize(canvas.clientWidth, canvas.clientHeight);
        }
        camera.aspect = canvas.clientWidth / canvas.clientHeight;
        camera.updateProjectionMatrix();
    }
});

// Инициализация после загрузки DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init3D);
} else {
    init3D();
}
