const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env') });
const express = require('express');
const { fal } = require('@fal-ai/client');
const { execFile } = require('child_process');
const ffmpegPath = require('ffmpeg-static');
const fetch = require('node-fetch');
const fs = require('fs');
const os = require('os');

fal.config({ credentials: process.env.FAL_KEY });

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));
app.use('/assets', express.static(path.join(__dirname, 'assets')));

// Cache the uploaded image URL so we only upload once per session
let cachedImageUrl = null;

async function getCheeseUrl() {
  if (cachedImageUrl) return cachedImageUrl;

  const imgPath = path.join(__dirname, 'assets', 'cheese.png');
  if (!fs.existsSync(imgPath)) {
    throw new Error('Character image not found. Add cheese.png to the assets/ folder.');
  }

  const scaledPath = path.join(os.tmpdir(), 'cheese_scaled.png');
  await new Promise((resolve, reject) => {
    execFile(ffmpegPath, [
      '-i', imgPath, '-vf', 'scale=512:-1', '-y', scaledPath
    ], (err, _stdout, stderr) => {
      if (err) reject(new Error(stderr || err.message));
      else resolve();
    });
  });

  console.log('Uploading character image to fal.ai storage...');
  const buffer = fs.readFileSync(scaledPath);
  try { fs.unlinkSync(scaledPath); } catch {}
  const blob = new Blob([buffer], { type: 'image/png' });
  cachedImageUrl = await fal.storage.upload(blob);
  console.log('Character uploaded:', cachedImageUrl);
  return cachedImageUrl;
}

function videoToGif(videoPath, gifPath) {
  return new Promise((resolve, reject) => {
    // High-quality GIF using palette optimization
    const filter = 'fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse';
    execFile(ffmpegPath, [
      '-i', videoPath,
      '-vf', filter,
      '-loop', '0',
      '-y',
      gifPath
    ], (err, _stdout, stderr) => {
      if (err) reject(new Error(stderr || err.message));
      else resolve();
    });
  });
}

// Ensure temp dir exists and clean up old GIFs on startup
function cleanTempGifs() {
  const tempDir = path.join(__dirname, 'public', 'temp');
  fs.mkdirSync(tempDir, { recursive: true });
  const files = fs.readdirSync(tempDir);
  files.forEach(f => {
    try { fs.unlinkSync(path.join(tempDir, f)); } catch {}
  });
}

cleanTempGifs();

// SSE endpoint — streams status updates then returns a GIF URL
app.get('/generate-stream', async (req, res) => {
  const prompt = (req.query.prompt || '').trim();
  if (!prompt) {
    res.status(400).end();
    return;
  }

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  const send = (event, data) => {
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  try {
    send('status', { message: 'Uploading character...' });
    const imageUrl = await getCheeseUrl();

    send('status', { message: 'Queued for animation...' });

    const enhancedPrompt = `Cheese the cartoon rat character ${prompt}, 2D cartoon animation, clean line art, consistent character design, smooth looping animation`;

    console.log(`\nGenerating: "${enhancedPrompt}"`);

    const result = await fal.subscribe('fal-ai/kling-video/v1.6/standard/image-to-video', {
      input: {
        image_url: imageUrl,
        prompt: enhancedPrompt,
        negative_prompt: 'moving teeth, morphing mouth, changing teeth, extra teeth, three teeth, deformed face, changing features, distorted eyes, melting, morphing body, extra limbs, blurry',
        duration: '5',
        aspect_ratio: '1:1',
      },
      logs: true,
      onQueueUpdate: (update) => {
        if (update.status === 'IN_QUEUE') {
          send('status', { message: 'In queue...' });
        } else if (update.status === 'IN_PROGRESS') {
          const log = update.logs?.[update.logs.length - 1]?.message;
          send('status', { message: log ? `Animating: ${log}` : 'Animating...' });
        }
      },
    });

    const videoUrl = result.data.video.url;
    console.log('Video ready:', videoUrl);

    send('status', { message: 'Downloading video...' });

    const tempId = Date.now();
    const videoPath = path.join(os.tmpdir(), `cheese_${tempId}.mp4`);
    const gifFilename = `cheese_${tempId}.gif`;
    const gifPath = path.join(__dirname, 'public', 'temp', gifFilename);

    const videoRes = await fetch(videoUrl);
    const videoBuffer = await videoRes.buffer();
    fs.writeFileSync(videoPath, videoBuffer);

    send('status', { message: 'Converting to GIF...' });
    await videoToGif(videoPath, gifPath);

    // Cleanup video
    try { fs.unlinkSync(videoPath); } catch {}

    const stats = fs.statSync(gifPath);
    const sizeMb = (stats.size / 1024 / 1024).toFixed(1);
    console.log(`GIF ready: ${gifFilename} (${sizeMb}MB)`);

    send('complete', { gifUrl: `/temp/${gifFilename}`, filename: `cheese_${prompt.replace(/\s+/g, '_')}.gif` });
    res.end();

  } catch (err) {
    console.error('Error:', err.message);
    if (err.body) console.error('API response:', JSON.stringify(err.body));
    const userMsg = err.body?.detail || err.message || 'Generation failed';
    send('error', { message: userMsg });
    res.end();
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`\n  Cheese GIF Generator`);
  console.log(`  http://localhost:${PORT}\n`);
});
