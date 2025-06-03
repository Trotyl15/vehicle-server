import asyncio, math, random, time, websockets
from car_pose_pb2 import CarPose

PORT      = 8765

V_BASE    = 3.0           # mean forward speed  (m/s)
A_V       = 1.5           # ± swing             (m/s)
FREQ_HZ   = 0.05          # speed wiggle freq   (Hz)  → 20 s period
NOISE_SD  = 0.4           # extra Gaussian jitter (m/s)

A_M       = 8.0           # side-to-side amplitude (m)
WAVELEN_M = 50.0          # crest-to-crest distance (m)

LAT0      = 37.7955
LON0      = -122.3937
EARTH_R   = 6_378_137.0
LAT0_RAD  = math.radians(LAT0)
DEG_PER_RAD = 180 / math.pi

clients: set[websockets.WebSocketServerProtocol] = set()


def enu_to_ll(east: float, north: float) -> tuple[float, float]:
    d_lat = north / EARTH_R
    d_lon = east  / (EARTH_R * math.cos(LAT0_RAD))
    return (LAT0 + d_lat * DEG_PER_RAD,
            LON0 + d_lon * DEG_PER_RAD)


async def produce():
    k        = 2 * math.pi / WAVELEN_M
    omega    = 2 * math.pi * FREQ_HZ
    t_prev   = time.time()
    north    = 0.0

    while True:
        t_now = time.time()
        dt    = t_now - t_prev
        t_prev = t_now

        # variable forward speed (≥ 0 m/s)
        v_n = max(0.0,
                  V_BASE
                + A_V * math.sin(omega * t_now)
                + random.gauss(0.0, NOISE_SD))

        north += v_n * dt
        east   = A_M * math.sin(k * north)

        # lateral velocity (for heading)
        v_e = A_M * k * v_n * math.cos(k * north)
        heading = math.atan2(v_e, v_n)          # 0 = North, +clockwise

        lat, lon = enu_to_ll(east, north)

        pkt  = CarPose(latitude=lat, longitude=lon, heading=heading)
        data = pkt.SerializeToString()

        for ws in set(clients):
            try:
                await ws.send(data)
            except websockets.ConnectionClosed:
                clients.discard(ws)

        await asyncio.sleep(0.05)               # ~20 Hz


async def handler(ws):
    clients.add(ws)
    try:
        await ws.wait_closed()
    finally:
        clients.discard(ws)


async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"🚚  Variable-speed pose server at ws://localhost:{PORT}")
        await produce()


if __name__ == "__main__":
    asyncio.run(main())
