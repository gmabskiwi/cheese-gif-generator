const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env') });
const { fal } = require('@fal-ai/client');

fal.config({ credentials: process.env.FAL_KEY });

async function test() {
  console.log('Key loaded:', !!process.env.FAL_KEY);
  console.log('Key prefix:', process.env.FAL_KEY?.slice(0, 8));

  const models = [
    'fal-ai/flux/schnell',
    'fal-ai/stable-video',
    'fal-ai/kling-video/v1.6/standard/image-to-video',
  ];

  for (const model of models) {
    try {
      console.log(`\nTesting model: ${model}`);
      const queue = await fal.queue.submit(model, {
        input: { prompt: 'a cartoon rat waving' }
      });
      console.log(`  OK - request ID: ${queue.request_id}`);
      // Cancel immediately - we just want to check access
      await fal.queue.cancel(model, { requestId: queue.request_id });
    } catch (err) {
      console.log(`  FAIL: ${err.message}`);
      if (err.body) console.log(`  Body:`, JSON.stringify(err.body));
    }
  }
}

test().catch(console.error);
