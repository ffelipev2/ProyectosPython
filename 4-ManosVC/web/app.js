import {
  FaceLandmarker,
  FilesetResolver,
  HandLandmarker,
} from "./vendor/mediapipe/vision_bundle.mjs";

const video = document.querySelector("#camera");
const canvas = document.querySelector("#scene");
const ctx = canvas.getContext("2d");
const startPanel = document.querySelector("#startPanel");
const startButton = document.querySelector("#startButton");
const statusText = document.querySelector("#statusText");
const effectButtons = [...document.querySelectorAll("[data-effect]")];

const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [0, 9], [9, 10], [10, 11], [11, 12],
  [0, 13], [13, 14], [14, 15], [15, 16],
  [0, 17], [17, 18], [18, 19], [19, 20],
  [5, 9], [9, 13], [13, 17],
];
const FINGER_TIPS = [4, 8, 12, 16, 20];
const PALM_LANDMARKS = [0, 5, 9, 13, 17];

let handLandmarker;
let faceLandmarker;
let activeEffect = "hands";
let lastVideoTime = -1;
let lastResults = null;
let lastFaceResults = null;
let videoFrame = { x: 0, y: 0, width: window.innerWidth, height: window.innerHeight };

function resizeCanvas() {
  const width = Math.max(1, window.innerWidth);
  const height = Math.max(1, window.innerHeight);
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function setStatus(message) {
  statusText.textContent = message;
}

function setEffect(effect) {
  activeEffect = effect;
  effectButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.effect === effect);
  });
}

function landmarkToPoint(landmark) {
  return {
    x: window.innerWidth - (videoFrame.x + landmark.x * videoFrame.width),
    y: videoFrame.y + landmark.y * videoFrame.height,
  };
}

function palmCenter(points) {
  const sum = PALM_LANDMARKS.reduce(
    (acc, index) => ({ x: acc.x + points[index].x, y: acc.y + points[index].y }),
    { x: 0, y: 0 },
  );
  return { x: sum.x / PALM_LANDMARKS.length, y: sum.y / PALM_LANDMARKS.length };
}

function palmRadius(points) {
  const wrist = points[0];
  const middleBase = points[9];
  const distance = Math.hypot(middleBase.x - wrist.x, middleBase.y - wrist.y);
  return Math.max(28, Math.min(96, distance * 0.78));
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function hsl(time, offset, light = 62) {
  return `hsl(${(time * 100 + offset * 360) % 360} 100% ${light}%)`;
}

function drawVideoCover() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const videoRatio = video.videoWidth / video.videoHeight || 16 / 9;
  const canvasRatio = width / height;
  let drawWidth = width;
  let drawHeight = height;
  let x = 0;
  let y = 0;

  if (videoRatio > canvasRatio) {
    drawHeight = height;
    drawWidth = height * videoRatio;
    x = (width - drawWidth) / 2;
  } else {
    drawWidth = width;
    drawHeight = width / videoRatio;
    y = (height - drawHeight) / 2;
  }

  videoFrame = { x, y, width: drawWidth, height: drawHeight };

  ctx.save();
  ctx.translate(width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(video, x, y, drawWidth, drawHeight);
  ctx.restore();
}

function drawNeonLine(a, b, color, width = 2) {
  ctx.save();
  ctx.lineCap = "round";
  ctx.strokeStyle = color;
  ctx.shadowColor = color;
  ctx.shadowBlur = 18;
  ctx.lineWidth = width + 8;
  ctx.globalAlpha = 0.28;
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(b.x, b.y);
  ctx.stroke();
  ctx.globalAlpha = 1;
  ctx.shadowBlur = 0;
  ctx.lineWidth = width;
  ctx.strokeStyle = "#ffffff";
  ctx.stroke();
  ctx.lineWidth = width + 1;
  ctx.strokeStyle = color;
  ctx.stroke();
  ctx.restore();
}

function interpolatePoint(a, b, amount) {
  return {
    x: a.x + (b.x - a.x) * amount,
    y: a.y + (b.y - a.y) * amount,
  };
}

function drawHandSkeleton(points) {
  ctx.save();
  ctx.lineCap = "round";
  ctx.strokeStyle = "rgba(230, 238, 246, 0.46)";
  ctx.lineWidth = 2;
  HAND_CONNECTIONS.forEach(([start, end]) => {
    ctx.beginPath();
    ctx.moveTo(points[start].x, points[start].y);
    ctx.lineTo(points[end].x, points[end].y);
    ctx.stroke();
  });

  points.forEach((point, index) => {
    if (index === 0) return;
    ctx.fillStyle = "rgba(255, 255, 255, 0.72)";
    ctx.beginPath();
    ctx.arc(point.x, point.y, 3.4, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.restore();
}

function drawRainbowCord(a, b, time, seed, width = 2.2, segments = 9) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const length = Math.max(1, Math.hypot(dx, dy));
  const normal = { x: -dy / length, y: dx / length };

  for (let segment = 0; segment < segments; segment += 1) {
    const startT = segment / segments;
    const endT = (segment + 1) / segments;
    const start = interpolatePoint(a, b, startT);
    const end = interpolatePoint(a, b, endT);
    const color = hsl(time, seed + startT * 0.8, 62);

    drawNeonLine(
      {
        x: start.x + normal.x * Math.sin(time * 6 + segment) * 2,
        y: start.y + normal.y * Math.sin(time * 6 + segment) * 2,
      },
      {
        x: end.x + normal.x * Math.sin(time * 6 + segment + 1) * 2,
        y: end.y + normal.y * Math.sin(time * 6 + segment + 1) * 2,
      },
      color,
      width,
    );

    if (segment % 3 === 1) {
      const middle = interpolatePoint(a, b, startT + (endT - startT) * 0.5);
      const wave = Math.sin(time * 7 + seed * 9 + segment) * 4;
      drawSpark(
        { x: middle.x + normal.x * wave, y: middle.y + normal.y * wave },
        7,
        color,
        time,
        seed + segment,
      );
    }
  }
}

function drawSpark(center, size, color, time, seed) {
  const pulse = 0.65 + Math.sin(time * 8 + seed * 9) * 0.28;
  const arm = size * pulse;
  ctx.save();
  ctx.strokeStyle = color;
  ctx.fillStyle = "#ffffff";
  ctx.shadowColor = color;
  ctx.shadowBlur = 14;
  ctx.beginPath();
  ctx.arc(center.x, center.y, Math.max(2, arm * 0.28), 0, Math.PI * 2);
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(center.x - arm, center.y);
  ctx.lineTo(center.x + arm, center.y);
  ctx.moveTo(center.x, center.y - arm);
  ctx.lineTo(center.x, center.y + arm);
  ctx.stroke();
  ctx.restore();
}

function drawHandsEffect(hands, time) {
  const allPoints = [];

  for (const landmarks of hands) {
    const points = landmarks.map(landmarkToPoint);
    allPoints.push(points);
    drawHandSkeleton(points);

    FINGER_TIPS.forEach((tipIndex, index) => {
      drawSpark(points[tipIndex], 12, hsl(time, index / FINGER_TIPS.length), time, index);
    });

    for (let i = 0; i < FINGER_TIPS.length; i += 1) {
      for (let j = i + 1; j < FINGER_TIPS.length; j += 1) {
        drawRainbowCord(
          points[FINGER_TIPS[i]],
          points[FINGER_TIPS[j]],
          time,
          (i * FINGER_TIPS.length + j) / 12,
          2.1,
          9,
        );
      }
    }
  }

  if (allPoints.length >= 2) {
    FINGER_TIPS.forEach((tipIndex, index) => {
      drawRainbowCord(
        allPoints[0][tipIndex],
        allPoints[1][tipIndex],
        time,
        0.7 + index / 8,
        3,
        7,
      );
    });
  }
}

function drawAnimeSpikes(center, radius, time) {
  ctx.save();
  ctx.lineCap = "round";
  ctx.shadowColor = "#fff05d";
  ctx.shadowBlur = 18;
  for (let i = 0; i < 28; i += 1) {
    const angle = i * (Math.PI * 2 / 28) + Math.sin(time * 2) * 0.12;
    const wave = 0.75 + Math.sin(time * 12 + i * 1.7) * 0.25;
    const inner = radius * (0.8 + wave * 0.08);
    const outer = radius * (1.7 + wave * 0.55);
    ctx.strokeStyle = i % 2 ? "#fff7a8" : "#ffffff";
    ctx.lineWidth = i % 3 === 0 ? 4 : 2;
    ctx.beginPath();
    ctx.moveTo(center.x + Math.cos(angle) * inner, center.y + Math.sin(angle) * inner);
    ctx.lineTo(center.x + Math.cos(angle) * outer, center.y + Math.sin(angle) * outer);
    ctx.stroke();
  }
  ctx.restore();
}

function drawLightning(center, radius, time) {
  ctx.save();
  ctx.lineCap = "round";
  ctx.shadowColor = "#fff05d";
  ctx.shadowBlur = 12;
  for (let bolt = 0; bolt < 8; bolt += 1) {
    const angle = time * 1.8 + bolt * (Math.PI * 2 / 8);
    ctx.strokeStyle = bolt % 2 ? "#fff05d" : "#ffffff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let step = 0; step < 5; step += 1) {
      const distance = radius * (0.6 + step * 0.26);
      const jitter = Math.sin(time * 15 + bolt * 2.5 + step * 1.8) * 0.22;
      const x = center.x + Math.cos(angle + jitter) * distance;
      const y = center.y + Math.sin(angle + jitter) * distance;
      if (step === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  ctx.restore();
}

function drawEnergyBeam(point, center, time, seed) {
  ctx.save();
  ctx.lineCap = "round";
  ctx.strokeStyle = "#fff05d";
  ctx.shadowColor = "#fff05d";
  ctx.shadowBlur = 14;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(point.x, point.y);
  const dx = center.x - point.x;
  const dy = center.y - point.y;
  const length = Math.max(1, Math.hypot(dx, dy));
  const normal = { x: -dy / length, y: dx / length };
  for (let segment = 1; segment <= 6; segment += 1) {
    const amount = segment / 6;
    const wave = Math.sin(time * 14 + seed * 7 + segment * 2) * 8;
    ctx.lineTo(point.x + dx * amount + normal.x * wave, point.y + dy * amount + normal.y * wave);
  }
  ctx.stroke();
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 1.5;
  ctx.stroke();
  ctx.restore();
}

function drawEnergyEffect(hands, time) {
  for (const landmarks of hands) {
    const points = landmarks.map(landmarkToPoint);
    const center = palmCenter(points);
    const radius = palmRadius(points);
    const pulse = 0.92 + Math.sin(time * 7.5) * 0.12;

    drawAnimeSpikes(center, radius, time);

    const gradient = ctx.createRadialGradient(center.x, center.y, 0, center.x, center.y, radius * 2.4 * pulse);
    gradient.addColorStop(0, "rgba(255,255,255,1)");
    gradient.addColorStop(0.18, "rgba(255,255,210,0.98)");
    gradient.addColorStop(0.42, "rgba(255,240,93,0.92)");
    gradient.addColorStop(0.7, "rgba(255,151,35,0.34)");
    gradient.addColorStop(1, "rgba(255,151,35,0)");

    ctx.save();
    ctx.fillStyle = gradient;
    ctx.shadowColor = "#fff05d";
    ctx.shadowBlur = 38;
    ctx.beginPath();
    ctx.arc(center.x, center.y, radius * 2.4 * pulse, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#fff9b8";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.ellipse(center.x, center.y, radius * 1.55, radius * 0.52, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.ellipse(center.x, center.y, radius * 1.65, radius * 0.45, Math.PI / 3, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();

    drawLightning(center, radius, time);
    FINGER_TIPS.forEach((tip, index) => drawEnergyBeam(points[tip], center, time, index));
  }
}

function clamp(value, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value));
}

function blendScore(blendshapes, name) {
  return blendshapes?.categories?.find((category) => category.categoryName === name)?.score || 0;
}

function expressionMetrics(points, blendshapes) {
  const leftCheek = points[234];
  const rightCheek = points[454];
  const faceWidth = Math.max(80, distance(leftCheek, rightCheek));
  const mouthTop = points[13];
  const mouthBottom = points[14];
  const leftEyeTop = points[159];
  const leftEyeBottom = points[145];
  const rightEyeTop = points[386];
  const rightEyeBottom = points[374];

  const jawOpen = blendScore(blendshapes, "jawOpen");
  const mouthFunnel = blendScore(blendshapes, "mouthFunnel");
  const mouthPucker = blendScore(blendshapes, "mouthPucker");
  const leftBlink = blendScore(blendshapes, "eyeBlinkLeft");
  const rightBlink = blendScore(blendshapes, "eyeBlinkRight");
  const browDownLeft = blendScore(blendshapes, "browDownLeft");
  const browDownRight = blendScore(blendshapes, "browDownRight");
  const browInnerUp = blendScore(blendshapes, "browInnerUp");
  const hasBlendshapes = Boolean(blendshapes?.categories?.length);

  if (hasBlendshapes) {
    return {
      mouthOpen: clamp((Math.max(jawOpen, mouthFunnel * 0.75, mouthPucker * 0.45) - 0.16) / 0.58),
      leftEyeOpen: clamp(1 - leftBlink * 1.25, 0.04, 1),
      rightEyeOpen: clamp(1 - rightBlink * 1.25, 0.04, 1),
      browTension: clamp((browDownLeft + browDownRight) * 0.6 + browInnerUp * 0.2),
    };
  }

  const mouthRatio = distance(mouthTop, mouthBottom) / faceWidth;
  const leftEyeRatio = distance(leftEyeTop, leftEyeBottom) / faceWidth;
  const rightEyeRatio = distance(rightEyeTop, rightEyeBottom) / faceWidth;

  return {
    mouthOpen: clamp((mouthRatio - 0.022) / 0.08),
    leftEyeOpen: clamp((leftEyeRatio - 0.012) / 0.045, 0.04, 1),
    rightEyeOpen: clamp((rightEyeRatio - 0.012) / 0.045, 0.04, 1),
    browTension: 0.45,
  };
}

function faceMetrics(points, blendshapes) {
  const leftCheek = points[234];
  const rightCheek = points[454];
  const forehead = points[10];
  const chin = points[152];
  const leftEyeOuter = points[33];
  const rightEyeOuter = points[263];
  const faceWidth = Math.max(80, distance(leftCheek, rightCheek));
  const faceHeight = Math.max(95, distance(forehead, chin));
  const expression = expressionMetrics(points, blendshapes);

  return {
    center: {
      x: (leftCheek.x + rightCheek.x + forehead.x + chin.x) / 4,
      y: (leftCheek.y + rightCheek.y + forehead.y + chin.y) / 4,
    },
    scale: faceWidth / 125,
    width: faceWidth,
    height: faceHeight,
    angle: Math.atan2(leftEyeOuter.y - rightEyeOuter.y, leftEyeOuter.x - rightEyeOuter.x),
    ...expression,
  };
}

function drawEye(x, y, openness) {
  const openHeight = Math.max(2.2, 12 * openness);
  ctx.save();
  ctx.fillStyle = "#f8fbff";
  ctx.beginPath();
  ctx.ellipse(x, y, 24, openHeight, -0.12 * Math.sign(x), 0, Math.PI * 2);
  ctx.fill();

  if (openness > 0.18) {
    ctx.fillStyle = "#101215";
    ctx.beginPath();
    ctx.ellipse(x + Math.sign(x) * 2, y + 1, Math.max(2, 6 * openness), Math.max(1.5, 4 * openness), 0, 0, Math.PI * 2);
    ctx.fill();
  } else {
    ctx.strokeStyle = "#101215";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(x - 16, y);
    ctx.lineTo(x + 16, y);
    ctx.stroke();
  }
  ctx.restore();
}

function drawWhiskers(side) {
  ctx.save();
  ctx.strokeStyle = "rgba(245, 248, 255, 0.9)";
  ctx.lineWidth = 3;
  ctx.lineCap = "round";
  for (let i = 0; i < 3; i += 1) {
    const y = 18 + i * 13;
    const endY = y - 8 + i * 8;
    ctx.beginPath();
    ctx.moveTo(side * 18, y);
    ctx.lineTo(side * 88, endY);
    ctx.stroke();
  }
  ctx.restore();
}

function drawRaccoonFace(metrics, time) {
  const leftEyeOpen = metrics.leftEyeOpen;
  const rightEyeOpen = metrics.rightEyeOpen;
  const mouthOpen = metrics.mouthOpen;
  const browLift = metrics.browTension * 8;

  ctx.save();
  ctx.translate(metrics.center.x, metrics.center.y - metrics.height * 0.08);
  ctx.rotate(metrics.angle);
  ctx.scale(metrics.scale, metrics.scale);

  ctx.fillStyle = "#5f6361";
  ctx.beginPath();
  ctx.arc(-58, -64, 22, 0, Math.PI * 2);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#202226";
  ctx.beginPath();
  ctx.arc(-58, -64, 13, 0, Math.PI * 2);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#5f6361";
  ctx.beginPath();
  ctx.arc(58, -64, 22, 0, Math.PI * 2);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#202226";
  ctx.beginPath();
  ctx.arc(58, -64, 13, 0, Math.PI * 2);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = "#8d9091";
  ctx.beginPath();
  ctx.ellipse(0, 0, 84, 92, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#a9abad";
  ctx.beginPath();
  ctx.ellipse(-20, 35, 48, 33, -0.18, 0, Math.PI * 2);
  ctx.ellipse(22, 35, 48, 33, 0.18, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#27292e";
  ctx.beginPath();
  ctx.moveTo(-78, -34);
  ctx.bezierCurveTo(-58, -72, -14, -66, 0, -38);
  ctx.bezierCurveTo(14, -66, 58, -72, 78, -34);
  ctx.bezierCurveTo(55, 8, 20, 13, 0, -2);
  ctx.bezierCurveTo(-20, 13, -55, 8, -78, -34);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = "rgba(255, 255, 255, 0.16)";
  ctx.beginPath();
  ctx.ellipse(-18, -74, 38, 10, -0.08, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#4f5355";
  ctx.beginPath();
  ctx.ellipse(0, -106, 9, 18, -1.0, 0, Math.PI * 2);
  ctx.ellipse(10, -104, 8, 17, -0.45, 0, Math.PI * 2);
  ctx.ellipse(-10, -104, 8, 17, 0.45, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = "#101216";
  ctx.lineWidth = 9;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(-56, -54 - browLift);
  ctx.quadraticCurveTo(-34, -72 - browLift, -12, -58);
  ctx.moveTo(56, -54 - browLift);
  ctx.quadraticCurveTo(34, -72 - browLift, 12, -58);
  ctx.stroke();

  drawEye(-34, -30, leftEyeOpen);
  drawEye(34, -30, rightEyeOpen);

  ctx.fillStyle = "#17191d";
  ctx.beginPath();
  ctx.ellipse(0, 13, 17, 11, 0, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = "#17191d";
  ctx.lineWidth = 3.5;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(0, 23);
  ctx.lineTo(0, 34);
  ctx.stroke();

  if (mouthOpen > 0.08) {
    ctx.fillStyle = "#241315";
    ctx.beginPath();
    ctx.ellipse(0, 49, 18, 4 + mouthOpen * 25, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(255, 128, 128, 0.8)";
    ctx.beginPath();
    ctx.ellipse(0, 55 + mouthOpen * 8, 9, 2 + mouthOpen * 8, 0, 0, Math.PI * 2);
    ctx.fill();
  } else {
    ctx.strokeStyle = "#25262b";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(-24, 49);
    ctx.quadraticCurveTo(0, 58, 24, 49);
    ctx.stroke();
  }

  ctx.restore();
}

function drawFaceEffect(faces, blendshapesList, time) {
  for (const [index, landmarks] of faces.entries()) {
    const points = landmarks.map(landmarkToPoint);
    drawRaccoonFace(faceMetrics(points, blendshapesList[index]), time);
  }
}

function renderLoop() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  ctx.clearRect(0, 0, width, height);

  if (video.readyState >= 2) {
    drawVideoCover();
    if (video.currentTime !== lastVideoTime && handLandmarker && faceLandmarker) {
      if (activeEffect === "face") {
        lastFaceResults = faceLandmarker.detectForVideo(video, performance.now());
      } else {
        lastResults = handLandmarker.detectForVideo(video, performance.now());
      }
      lastVideoTime = video.currentTime;
    }
  } else {
    ctx.fillStyle = "#05070c";
    ctx.fillRect(0, 0, width, height);
  }

  const hands = lastResults?.landmarks || [];
  const faces = lastFaceResults?.faceLandmarks || [];
  const faceBlendshapes = lastFaceResults?.faceBlendshapes || [];
  const time = performance.now() / 1000;
  if (activeEffect === "face") drawFaceEffect(faces, faceBlendshapes, time);
  else if (activeEffect === "energy") drawEnergyEffect(hands, time);
  else drawHandsEffect(hands, time);

  requestAnimationFrame(renderLoop);
}

async function initLandmarker() {
  const vision = await FilesetResolver.forVisionTasks(
    "./vendor/mediapipe/wasm",
  );
  handLandmarker = await HandLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: "../models/hand_landmarker.task",
      delegate: "GPU",
    },
    runningMode: "VIDEO",
    numHands: 2,
    minHandDetectionConfidence: 0.7,
    minHandPresenceConfidence: 0.7,
    minTrackingConfidence: 0.7,
  });

  faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: "../models/face_landmarker.task",
      delegate: "GPU",
    },
    runningMode: "VIDEO",
    numFaces: 2,
    minFaceDetectionConfidence: 0.6,
    minFacePresenceConfidence: 0.6,
    minTrackingConfidence: 0.6,
    outputFaceBlendshapes: true,
  });
}

async function startCamera() {
  try {
    setStatus("Cargando MediaPipe...");
    await initLandmarker();

    setStatus("Solicitando cámara...");
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: "user",
      },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
    startPanel.classList.add("is-hidden");
  } catch (error) {
    setStatus(`No pude iniciar la cámara: ${error.message}`);
  }
}

effectButtons.forEach((button) => {
  button.addEventListener("click", () => setEffect(button.dataset.effect));
});

window.addEventListener("keydown", (event) => {
  if (event.key.toLowerCase() === "e") {
    setEffect(activeEffect === "hands" ? "energy" : "hands");
  }
});

window.addEventListener("resize", resizeCanvas);
startButton.addEventListener("click", startCamera);

resizeCanvas();
renderLoop();
