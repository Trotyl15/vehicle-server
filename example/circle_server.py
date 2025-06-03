#!/usr/bin/env python3
import asyncio, math, time
import websockets, websockets.exceptions
from car_pose_pb2 import CarPose     # using lat, lon, heading

PORT, HZ = 8765, 20
RADIUS_M = 10
LAT0_DEG, LON0_DEG = 37.7955, -122.3937  # origin
EARTH_R = 6_378_137.0
LAT0_RAD = math.radians(LAT0_DEG)
DEG_PER_RAD = 180 / math.pi

# ── pre-12 API uses WebSocketServerProtocol ──
clients: set[websockets.WebSocketServerProtocol] = set()

def enu_to_ll(east, north):
    d_lat = north / EARTH_R
    d_lon = east / (EARTH_R * math.cos(LAT0_RAD))
    return (LAT0_DEG + d_lat * DEG_PER_RAD,
            LON0_DEG + d_lon * DEG_PER_RAD)

async def produce():
    t0 = time.time()
    while True:
        t = time.time() - t0
        east  = RADIUS_M * math.sin(t)
        north = RADIUS_M * math.cos(t)
        lat, lon = enu_to_ll(east, north)

        dx =  RADIUS_M * math.cos(t)
        dy = -RADIUS_M * math.sin(t)
        heading = math.atan2(dx, dy)   # 0 = north, +CW

        msg = CarPose(latitude=lat, longitude=lon, heading=heading)
        data = msg.SerializeToString()

        # broadcast & prune closed sockets
        gone = set()
        for c in clients:
            if not c.open:
                gone.add(c)
                continue
            try:
                await c.send(data)
            except websockets.exceptions.ConnectionClosed:
                gone.add(c)
        clients.difference_update(gone)

        await asyncio.sleep(1 / HZ)

# ── type hint back to protocol ──
async def handler(ws: websockets.WebSocketServerProtocol):
    clients.add(ws)
    try:
        await ws.wait_closed()
    finally:
        clients.discard(ws)

async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"🌎 pose server on ws://localhost:{PORT}")
        await produce()

if __name__ == "__main__":
    asyncio.run(main())