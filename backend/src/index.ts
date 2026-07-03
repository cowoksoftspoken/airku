/**
 * Welcome to Cloudflare Workers! This is your first worker.
 *
 * - Run `npm run dev` in your terminal to start a development server
 * - Open a browser tab at http://localhost:8787/ to see your worker in action
 * - Run `npm run deploy` to publish your worker
 *
 * Bind resources to your worker in `wrangler.jsonc`. After adding bindings, a type definition for the
 * `Env` object can be regenerated with `npm run cf-typegen`.
 *
 * Learn more at https://developers.cloudflare.com/workers/
 */

import { Hono } from 'hono';
import { cors } from 'hono/cors';

type Bindings = {
	AIRKU_KV?: KVNamespace;
};

interface TelemetryPayload {
	room: string;
	aqi: number;
	temperature: number;
	humidity: number;
	pm25: number;
	pm10: number;
	co2: number;
	voc: number;
	mq135_raw?: number;
	mq135_ppm?: number;
	espId?: string;
	ip?: string;
}

const app = new Hono<{ Bindings: Bindings }>();

// Enable CORS for the Android application and testing
app.use('*', cors());

// Simple memory-cache fallback if KV Namespace is not bound yet
const memoryCache = new Map<string, string>();

app.get('/', (c) => {
	return c.json({
		status: 'online',
		service: 'AirKu IoT Gateway',
		timestamp: Date.now(),
	});
});

/**
 * GET /api/readings
 * Returns list of latest telemetry readings for all registered rooms.
 */
app.get('/api/readings', async (c) => {
	try {
		const list: TelemetryPayload[] = [];

		if (c.env.AIRKU_KV) {
			// Fetch from Cloudflare KV Namespace
			const keys = await c.env.AIRKU_KV.list({ prefix: 'room:' });
			for (const key of keys.keys) {
				const data = await c.env.AIRKU_KV.get(key.name);
				if (data) {
					list.push(JSON.parse(data));
				}
			}
		} else {
			// Fallback to in-memory store
			for (const value of memoryCache.values()) {
				list.push(JSON.parse(value));
			}
		}

		// Default mock data if no ESP32 has uploaded data yet
		if (list.length === 0) {
			return c.json([
				{
					room: 'Ruang Kelas A (Simulasi)',
					aqi: 42,
					temperature: 24.5,
					humidity: 62,
					pm25: 12,
					pm10: 34,
					co2: 410,
					voc: 0.2,
					mq135_raw: 900,
					mq135_ppm: 25.0,
					espId: 'esp32_class_a',
					ip: '192.168.1.121',
					timestamp: Date.now(),
				},
				{
					room: 'Ruang Meeting Kantor (Simulasi)',
					aqi: 112,
					temperature: 23.8,
					humidity: 61,
					pm25: 42,
					pm10: 75,
					co2: 1150,
					voc: 0.62,
					mq135_raw: 2100,
					mq135_ppm: 145.0,
					espId: 'esp32_meeting',
					ip: '192.168.1.144',
					timestamp: Date.now(),
				},
			]);
		}

		return c.json(list);
	} catch (error: any) {
		return c.json({ error: 'Failed to read database', message: error.message }, 500);
	}
});

/**
 * POST /api/telemetry
 * Receives real-time telemetry from an ESP32.
 * Handled with strict input validation.
 */
app.post('/api/telemetry', async (c) => {
	try {
		const body = await c.req.json<Partial<TelemetryPayload>>();

		// Strict Input Validation
		if (!body.room || body.aqi === undefined || body.temperature === undefined || body.humidity === undefined) {
			return c.json({ error: 'Bad Request', message: 'Missing required telemetry fields: room, aqi, temperature, humidity' }, 400);
		}

		const roomKey = `room:${body.room.trim().toLowerCase().replace(/\s+/g, '_')}`;
		const record: TelemetryPayload & { timestamp: number } = {
			room: body.room.trim(),
			aqi: Math.round(Number(body.aqi)),
			temperature: Number(body.temperature),
			humidity: Math.round(Number(body.humidity)),
			pm25: Math.round(Number(body.pm25 || 0)),
			pm10: Math.round(Number(body.pm10 || 0)),
			co2: Math.round(Number(body.co2 || 400)),
			voc: Number(body.voc || 0.1),
			mq135_raw: body.mq135_raw ? Number(body.mq135_raw) : 1000,
			mq135_ppm: body.mq135_ppm ? Number(body.mq135_ppm) : 30.0,
			espId: body.espId || `esp32_${body.room.trim().toLowerCase().replace(/\s+/g, '_')}`,
			ip: body.ip || '192.168.1.100',
			timestamp: Date.now(),
		};

		const valueStr = JSON.stringify(record);

		if (c.env.AIRKU_KV) {
			// Persist in Cloudflare KV with no expiration (or e.g. TTL of 7 days: { expirationTtl: 604800 })
			await c.env.AIRKU_KV.put(roomKey, valueStr);
		} else {
			// In-memory cache
			memoryCache.set(roomKey, valueStr);
		}

		return c.json({ success: true, message: `Telemetry updated for room: ${record.room}`, record });
	} catch (error: any) {
		return c.json({ error: 'Internal Server Error', message: error.message }, 500);
	}
});

export default app;
