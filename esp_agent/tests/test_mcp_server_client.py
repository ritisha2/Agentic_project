"""
MCP Server Stdio Client Integration Test Suite
Tests protocol handshakes, tool listing, and remote MCP tool calls over stdio pipe.
"""

import sys
import os
import pytest
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "api", "mcp", "server.py"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.mark.asyncio
async def test_mcp_server_connection_and_tools():
    """Verify stdio handshake, tool listing, and tool invocation over MCP protocol."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT],
        env={"PYTHONPATH": PROJECT_ROOT, "PATH": os.environ.get("PATH", "")}
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Step 1: Initialize MCP Protocol connection
            await session.initialize()

            # Step 2: List registered tools
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            assert "calculate_tdh" in tool_names
            assert "calculate_bep" in tool_names
            assert "simulate_frequency_change" in tool_names

            # Step 3: Call calculate_tdh tool over MCP
            tdh_res = await session.call_tool(
                name="calculate_tdh",
                arguments={"pdp_psi": 2100.0, "pip_psi": 350.0, "fluid_sg": 1.0}
            )
            assert tdh_res.content is not None
            assert len(tdh_res.content) > 0

            # Step 4: Call calculate_bep tool over MCP
            bep_res = await session.call_tool(
                name="calculate_bep",
                arguments={"current_flow_bpd": 1450.0, "bep_target_bpd": 1750.0}
            )
            assert bep_res.content is not None

            # Step 5: Call simulate_frequency_change tool over MCP
            twin_res = await session.call_tool(
                name="simulate_frequency_change",
                arguments={"asset_id": "FS-031", "current_frequency_hz": 50.0, "target_frequency_hz": 55.0}
            )
            assert twin_res.content is not None
