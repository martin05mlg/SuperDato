import fs from 'fs';
import path from 'path';
import sharp from 'sharp';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const publicDir = path.resolve(__dirname, '../public');

// SVG for standard icon (purpose: "any", iOS apple-touch-icon, favicon)
const anySvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="superdato-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10B981" />
      <stop offset="100%" stop-color="#047857" />
    </linearGradient>
  </defs>
  <!-- Rounded Rect Tile -->
  <rect width="512" height="512" rx="112" fill="url(#superdato-grad)" />
  <!-- Shopping Bag centered -->
  <g transform="translate(106, 117) scale(10.7)" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4 1.5 1 6v17a2.5 2.5 0 0 0 2.5 2.5h21a2.5 2.5 0 0 0 2.5-2.5V6l-3-4.5Z" />
    <path d="M1 6h26" />
    <path d="M19 11a5 5 0 0 1-10 0" />
  </g>
</svg>
`;

// SVG for maskable icon (purpose: "maskable" on Android / Adaptive Icons)
// Must have 100% full-bleed background without rounded corners, and icon inside the 80% safe circle
const maskableSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="superdato-grad-maskable" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10B981" />
      <stop offset="100%" stop-color="#047857" />
    </linearGradient>
  </defs>
  <!-- Full-bleed background -->
  <rect width="512" height="512" fill="url(#superdato-grad-maskable)" />
  <!-- Shopping Bag centered inside the safe-zone -->
  <g transform="translate(142, 150) scale(8.1)" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4 1.5 1 6v17a2.5 2.5 0 0 0 2.5 2.5h21a2.5 2.5 0 0 0 2.5-2.5V6l-3-4.5Z" />
    <path d="M1 6h26" />
    <path d="M19 11a5 5 0 0 1-10 0" />
  </g>
</svg>
`;

async function generate() {
  console.log('Generating PWA and App icons into:', publicDir);

  const targets = [
    { name: 'pwa-512x512.png', size: 512, svg: anySvg },
    { name: 'pwa-192x192.png', size: 192, svg: anySvg },
    { name: 'pwa-maskable-512x512.png', size: 512, svg: maskableSvg },
    { name: 'pwa-maskable-192x192.png', size: 192, svg: maskableSvg },
    { name: 'apple-touch-icon.png', size: 180, svg: anySvg },
    { name: 'favicon-32x32.png', size: 32, svg: anySvg },
    { name: 'favicon-16x16.png', size: 16, svg: anySvg },
  ];

  for (const t of targets) {
    const outPath = path.join(publicDir, t.name);
    await sharp(Buffer.from(t.svg))
      .resize(t.size, t.size)
      .png({ quality: 100, compressionLevel: 9 })
      .toFile(outPath);
    console.log(`✓ Generated ${t.name} (${t.size}x${t.size})`);
  }

  console.log('All icons generated successfully!');
}

generate().catch((err) => {
  console.error('Error generating icons:', err);
  process.exit(1);
});

