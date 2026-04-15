/**
 * Cheese LoRA Training — PNG version
 *
 * 1. Reads PNGs from training-images/
 * 2. Removes backgrounds via fal.ai birefnet (for consistent transparency)
 * 3. Packages into a zip and uploads to fal.ai storage
 * 4. Triggers Flux LoRA training
 * 5. Saves trained LoRA URL to lora-config.json
 */

const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env') });

const { fal } = require('@fal-ai/client');
const fetch = require('node-fetch');
const fs = require('fs');
const os = require('os');
const archiver = require('archiver');

fal.config({ credentials: process.env.FAL_KEY });

const IMAGES_DIR = path.join(__dirname, 'training-images');
const TRIGGER_WORD = 'CHEESECHAR';
const TRAINING_STEPS = 1500;

// ─── Helpers ────────────────────────────────────────────────────────────────

async function removeBackground(imagePath, outputPath) {
  const buffer = fs.readFileSync(imagePath);
  const blob = new Blob([buffer], { type: 'image/png' });
  const uploadedUrl = await fal.storage.upload(blob);

  const result = await fal.subscribe('fal-ai/birefnet', {
    input: {
      image_url: uploadedUrl,
      model: 'General Use (Light)',
      operating_resolution: '1024x1024',
      output_format: 'png',
    },
  });

  const res = await fetch(result.data.image.url);
  const buf = await res.buffer();
  fs.writeFileSync(outputPath, buf);
}

function createZip(sourceDir, outputPath) {
  return new Promise((resolve, reject) => {
    const output = fs.createWriteStream(outputPath);
    const archive = archiver('zip', { zlib: { level: 9 } });
    output.on('close', resolve);
    archive.on('error', reject);
    archive.pipe(output);
    archive.directory(sourceDir, false);
    archive.finalize();
  });
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main() {
  console.log('\n=== Cheese LoRA Training (PNG) ===\n');

  const images = fs.readdirSync(IMAGES_DIR)
    .filter(f => /\.(png|jpg|jpeg|webp)$/i.test(f));

  if (images.length === 0) {
    console.error('No images found in training-images/');
    process.exit(1);
  }
  console.log(`Found ${images.length} images\n`);

  // Create temp dir for processed images
  const processedDir = path.join(os.tmpdir(), `cheese_training_${Date.now()}`);
  fs.mkdirSync(processedDir, { recursive: true });

  // Step 1: Remove backgrounds
  console.log('Step 1/3 — Removing backgrounds...');
  let succeeded = 0;
  for (let i = 0; i < images.length; i++) {
    const imgPath = path.join(IMAGES_DIR, images[i]);
    const outName = `cheese_${String(i + 1).padStart(3, '0')}.png`;
    const outPath = path.join(processedDir, outName);
    process.stdout.write(`  [${i + 1}/${images.length}] ${images[i].slice(0, 45)}... `);
    try {
      await removeBackground(imgPath, outPath);
      console.log('✓');
      succeeded++;
    } catch (err) {
      // Fall back to original if bg removal fails
      fs.copyFileSync(imgPath, outPath);
      console.log(`~ (bg removal failed, using original)`);
      succeeded++;
    }
  }
  console.log(`\n  ${succeeded} images ready\n`);

  // Step 2: Package and upload
  console.log('Step 2/3 — Packaging and uploading...');
  const zipPath = path.join(os.tmpdir(), `cheese_training_${Date.now()}.zip`);
  await createZip(processedDir, zipPath);

  const zipSize = (fs.statSync(zipPath).size / 1024 / 1024).toFixed(1);
  console.log(`  Zip created: ${zipSize}MB`);

  const zipBuffer = fs.readFileSync(zipPath);
  const zipBlob = new Blob([zipBuffer], { type: 'application/zip' });
  const imagesDataUrl = await fal.storage.upload(zipBlob);
  console.log(`  Uploaded: ${imagesDataUrl}`);

  try { fs.rmSync(processedDir, { recursive: true }); } catch {}
  try { fs.unlinkSync(zipPath); } catch {}

  // Step 3: Train LoRA
  console.log('\nStep 3/3 — Training LoRA (10–20 minutes)...');
  console.log(`  Trigger word : ${TRIGGER_WORD}`);
  console.log(`  Steps        : ${TRAINING_STEPS}`);
  console.log(`  Images       : ${succeeded}\n`);

  const result = await fal.subscribe('fal-ai/flux-lora-fast-training', {
    input: {
      images_data_url: imagesDataUrl,
      trigger_word: TRIGGER_WORD,
      steps: TRAINING_STEPS,
      is_style: false,
      create_masks: true,
    },
    logs: true,
    onQueueUpdate: (update) => {
      if (update.logs?.length) {
        const last = update.logs[update.logs.length - 1].message;
        if (last) process.stdout.write(`\r  ${last.slice(0, 70).padEnd(70)}`);
      }
    },
  });

  console.log('\n');

  const loraUrl = result.data.diffusers_lora_file?.url;
  if (!loraUrl) {
    console.error('Training completed but no LoRA URL returned.');
    console.log('Full result:', JSON.stringify(result.data, null, 2));
    process.exit(1);
  }

  const config = {
    lora_url: loraUrl,
    trigger_word: TRIGGER_WORD,
    trained_at: new Date().toISOString(),
    training_images: succeeded,
  };
  fs.writeFileSync(
    path.join(__dirname, 'lora-config.json'),
    JSON.stringify(config, null, 2)
  );

  console.log('=== Training Complete ===');
  console.log(`LoRA URL : ${loraUrl}`);
  console.log('Saved to lora-config.json\n');
}

main().catch(err => {
  console.error('\nFatal error:', err.message);
  if (err.body) console.error('API:', JSON.stringify(err.body));
  process.exit(1);
});
