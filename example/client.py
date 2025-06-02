#!/usr/bin/env python3
import asyncio, math
import websockets
from car_pose_pb2 import CarPose   # latitude, longitude, heading

URI = "ws://localhost:8765"

# Same reference origin you used in the server
LAT0_DEG  = 37.7955
LON0_DEG  = -122.3937
EARTH_R   = 6_378_137.0            # m (mean Earth radius)
LAT0_RAD  = math.radians(LAT0_DEG)

def ll_to_enu(lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """Convert lat/lon back to local East-North metres (small-angle)."""
    d_lat = math.radians(lat_deg - LAT0_DEG)
    d_lon = math.radians(lon_deg - LON0_DEG)
    north = EARTH_R * d_lat
    east  = EARTH_R * d_lon * math.cos(LAT0_RAD)
    return east, north

async def consume():
    async with websockets.connect(URI) as ws:
        print("Connected; waiting for poses…")
        async for raw in ws:
            pose = CarPose()
            pose.ParseFromString(raw)

            east, north = ll_to_enu(pose.latitude, pose.longitude)

            print(f"E={east:7.2f} m   N={north:7.2f} m   "
                  f"θ={pose.heading:+.2f} rad")

asyncio.run(consume())
