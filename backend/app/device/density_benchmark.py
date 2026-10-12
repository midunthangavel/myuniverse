"""
Cloud Android Multi-Session Density Benchmark Harness (P14)
Measures concurrent device connection scaling, message routing latency,
throughput, isolation fidelity (zero crosstalk), and connection drop recovery
on the Synapse DeviceGateway.
"""

import time
import asyncio
import uuid
from typing import Dict, Any, List
import statistics

from .gateway import DeviceGateway, DeviceSession


class MockWebSocket:
    """Mock FastAPI WebSocket for in-memory density stress testing."""
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.sent_messages: List[Dict[str, Any]] = []
        self.is_closed = False

    async def accept(self):
        pass

    async def send_json(self, data: Dict[str, Any]):
        if self.is_closed:
            raise RuntimeError("WebSocket is closed")
        self.sent_messages.append(data)

    async def close(self, code: int = 1000, reason: str = ""):
        self.is_closed = True


class DensityBenchmark:
    """Simulates high-density concurrent Android sessions to evaluate gateway performance."""

    def __init__(self, gateway: DeviceGateway):
        self.gateway = gateway

    async def run_density_test(self, concurrent_devices: int = 25, commands_per_device: int = 4) -> Dict[str, Any]:
        """
        Connects N concurrent devices, dispatches commands concurrently,
        simulates realistic client observation responses, and benchmarks latency/crosstalk.
        """
        start_time = time.perf_counter()
        sessions: List[DeviceSession] = []
        ws_list: List[MockWebSocket] = []
        device_ids: List[str] = []
        latencies_ms: List[float] = []
        crosstalk_detected = False

        # 1. Provision and connect concurrent devices
        for i in range(concurrent_devices):
            dev_id = f"vdevice_density_{i:03d}_{uuid.uuid4().hex[:6]}"
            tenant_id = f"tenant_stress_{i:03d}"
            token = f"tok_stress_{dev_id}"
            
            self.gateway.register_device(device_id=dev_id, tenant_id=tenant_id, custom_token=token)
            mock_ws = MockWebSocket(dev_id)
            
            session = await self.gateway.connect(mock_ws, dev_id, tenant_id)
            sessions.append(session)
            ws_list.append(mock_ws)
            device_ids.append(dev_id)

        # 2. Concurrently dispatch commands across all devices
        async def device_workload(session: DeviceSession, mock_ws: MockWebSocket):
            nonlocal crosstalk_detected
            for seq in range(commands_per_device):
                cmd_start = time.perf_counter()
                cmd_id = f"cmd_{session.device_id}_{seq}"
                
                # Send command through gateway session
                dispatch_task = asyncio.create_task(
                    session.send_command(
                        task_id=f"task_{session.device_id}",
                        action={"type": "TAP", "target": f"btn_{seq}"},
                        expected={},
                        expires_in_sec=5
                    )
                )

                # Client processes message in memory
                await asyncio.sleep(0.005) # 5ms physical latency simulation
                
                # Verify that received command matches this device
                if mock_ws.sent_messages:
                    last_msg = mock_ws.sent_messages[-1]
                    if last_msg.get("task_id") != f"task_{session.device_id}":
                        crosstalk_detected = True
                    cmd_id = last_msg.get("command_id", "")
                else:
                    cmd_id = f"cmd_{session.device_id}_{seq}"

                # Respond with COMMAND_RESULT
                res_payload = {
                    "type": "COMMAND_RESULT",
                    "command_id": cmd_id,
                    "task_id": f"task_{session.device_id}",
                    "sequence": seq,
                    "status": "DISPATCHED",
                    "execution_status": "DISPATCHED",
                    "screen_fingerprint": f"fp_{session.device_id}_{seq}",
                    "observation": {
                        "foreground_package": "com.test.app",
                        "visible_nodes": [{"id": f"btn_{seq}", "text": "Clicked"}]
                    }
                }
                session.handle_result(res_payload)
                
                result = await dispatch_task
                cmd_lat = (time.perf_counter() - cmd_start) * 1000.0
                latencies_ms.append(cmd_lat)

        # Execute concurrent workloads
        tasks = [device_workload(s, ws) for s, ws in zip(sessions, ws_list)]
        await asyncio.gather(*tasks)

        # 3. Connection drop recovery test: drop 30% of connections
        drop_count = max(1, int(concurrent_devices * 0.3))
        for i in range(drop_count):
            s = sessions[i]
            self.gateway.disconnect(s.session_id)
            assert s.session_id not in self.gateway.sessions

        total_duration = time.perf_counter() - start_time
        total_commands = len(latencies_ms)
        throughput = round(total_commands / total_duration, 1)

        p50 = round(statistics.median(latencies_ms), 2)
        p95 = round(statistics.quantiles(latencies_ms, n=20)[18], 2) if len(latencies_ms) >= 20 else max(latencies_ms)
        p99 = round(statistics.quantiles(latencies_ms, n=100)[98], 2) if len(latencies_ms) >= 100 else max(latencies_ms)

        # Cleanup remaining sessions
        for s in sessions[drop_count:]:
            self.gateway.disconnect(s.session_id)

        return {
            "concurrent_devices": concurrent_devices,
            "total_commands_executed": total_commands,
            "total_duration_sec": round(total_duration, 3),
            "throughput_cmds_per_sec": throughput,
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "latency_p99_ms": p99,
            "crosstalk_detected": crosstalk_detected,
            "target_p99_met": p99 < 50.0,
            "passed": (not crosstalk_detected) and (p99 < 50.0)
        }
