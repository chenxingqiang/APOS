import pytest
import requests
import subprocess
import time
import os
import sys
import signal
import logging
import socket
import atexit
from requests.exceptions import HTTPError, ConnectionError
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Find an available port
def find_free_port():
    """Find a free port for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

class ServerManager:
    """Manage server startup and teardown for tests"""
    def __init__(self):
        self.port = find_free_port()
        self.process = None
        self.base_url = f"http://localhost:{self.port}"
        
    def start_server(self):
        """Start the workflow server in a separate process"""
        import subprocess
        import sys
        import time
        import os
        import traceback

        # Construct the command to run the server
        server_script = os.path.join(os.path.dirname(__file__), '..', 'agentflow', 'api', 'workflow_server.py')

        # Start the server process
        self.process = subprocess.Popen(
            [sys.executable, server_script, str(self.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for the server to start
        max_wait_time = 20  # Increased wait time
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                # Try to connect to the server
                response = requests.get(f"{self.base_url}/docs", timeout=2)
                if response.status_code == 200:
                    logger.info(f"Server started successfully on port {self.port}")
                    return
            except (requests.ConnectionError, requests.Timeout) as e:
                # Print out any connection errors
                logger.warning(f"Connection attempt failed: {e}")
                time.sleep(1)

        # Print out process output for debugging
        stdout, stderr = self.process.communicate()
        logger.error(f"Server stdout: {stdout}")
        logger.error(f"Server stderr: {stderr}")

        # If we get here, server didn't start
        raise RuntimeError(f"Server failed to start within {max_wait_time} seconds")
    
    def stop_server(self):
        """Stop the server process"""
        if self.process:
            self.process.terminate()
            try:
                stdout, stderr = self.process.communicate(timeout=5)
                logger.debug(f"Server stdout: {stdout}")
                logger.debug(f"Server stderr: {stderr}")
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

@pytest.fixture(scope="module")
def server():
    """Pytest fixture to manage server lifecycle"""
    server_manager = ServerManager()
    try:
        server_manager.start_server()
        yield server_manager
    finally:
        server_manager.stop_server()

# Global variable to store the base URL
BASE_URL = None

def pytest_configure(config):
    """Configure the test session"""
    global BASE_URL
    # This will be set by the server fixture
    BASE_URL = f"http://localhost:{server().port}" if hasattr(server(), 'port') else None

def test_sync_workflow_execution(server):
    """Test synchronous workflow execution"""
    url = f"{server.base_url}/workflow/execute"
    
    request_data = {
        "workflow": {
            "AGENT": "Academic_Paper_Optimization",
            "ENVIRONMENT": {
                "INPUT": ["STUDENT_NEEDS", "LANGUAGE", "TEMPLATE"],
                "OUTPUT": ["Markdown-formatted academic plan"]
            },
            "WORKFLOW": [
                {
                    "step_id": "step_1",
                    "type": "research",
                    "name": "Research Step",
                    "description": "Perform research on the given topic",
                    "input": ["STUDENT_NEEDS", "LANGUAGE", "TEMPLATE"],
                    "output": {
                        "type": "research_findings",
                        "format": "structured_data"
                    },
                    "agent_config": {
                        "type": "research",
                        "provider": "openai",
                        "model": "gpt-3.5-turbo"
                    }
                },
                {
                    "step_id": "step_2",
                    "type": "document",
                    "name": "Document Generation Step",
                    "description": "Generate document from research findings",
                    "input": ["WORKFLOW.step_1.output"],
                    "output": {
                        "type": "document",
                        "format": "Markdown with LaTeX"
                    },
                    "agent_config": {
                        "type": "document",
                        "provider": "openai",
                        "model": "gpt-3.5-turbo"
                    }
                }
            ]
        },
        "config": {
            "max_retries": 3,
            "retry_backoff": 2.0,
            "retry_delay": 0.1,
            "step_1_config": {
                "max_retries": 3,
                "timeout": 30,
                "preprocessors": [],
                "postprocessors": []
            },
            "step_2_config": {
                "max_retries": 3,
                "timeout": 30,
                "preprocessors": [],
                "postprocessors": []
            },
            "execution": {
                "parallel": False,
                "max_retries": 3
            },
            "distributed": False,
            "timeout": 300,
            "logging_level": "INFO"
        },
        "input_data": {
            "STUDENT_NEEDS": {
                "RESEARCH_TOPIC": "API Testing in Distributed Systems",
                "DEADLINE": "2024-05-15",
                "ACADEMIC_LEVEL": "Master"
            },
            "LANGUAGE": {
                "TYPE": "English",
                "STYLE": "Academic"
            },
            "TEMPLATE": "Research Paper"
        }
    }
    
    response = requests.post(url, json=request_data)
    
    if response.status_code != 200:
        logger.error(f"Full error response: {response.text}")
        raise requests.exceptions.HTTPError(
            f"Request failed with status {response.status_code}: {response.text}"
        )
    
    result = response.json()
    assert "workflow_id" in result
    
    # Check workflow status
    status_url = f"{server.base_url}/workflow/status/{result['workflow_id']}"
    status_response = requests.get(status_url)
    assert status_response.status_code == 200

    status_result = status_response.json()
    assert "status" in status_result
    assert status_result["status"] in ["completed", "running", "pending"]

def test_async_workflow_execution(server):
    """Test asynchronous workflow execution"""
    execute_url = f"{server.base_url}/workflow/execute_async"
    
    request_data = {
        "workflow": {
            "WORKFLOW": [
                {
                    "step": 1,
                    "type": "research",
                    "name": "Research Step",
                    "description": "Perform research on the given topic",
                    "input": ["STUDENT_NEEDS", "LANGUAGE", "TEMPLATE"],
                    "output": {
                        "type": "research_findings",
                        "format": "structured_data"
                    },
                    "agent_config": {
                        "type": "research",
                        "provider": "openai",
                        "model": "gpt-3.5-turbo"
                    }
                },
                {
                    "step": 2,
                    "type": "document",
                    "name": "Document Generation Step",
                    "description": "Generate document from research findings",
                    "input": ["WORKFLOW.1.output"],
                    "output": {
                        "type": "document",
                        "format": "Markdown with LaTeX"
                    },
                    "agent_config": {
                        "type": "document",
                        "provider": "openai",
                        "model": "gpt-3.5-turbo"
                    }
                }
            ]
        },
        "config": {
            "max_iterations": 3,
            "logging_level": "INFO",
            "distributed": True,
            "timeout": 300,
            "execution": {
                "parallel": True,
                "max_retries": 3
            },
            "agents": {
                "research": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7
                },
                "document": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7
                }
            }
        },
        "input_data": {
            "STUDENT_NEEDS": {
                "RESEARCH_TOPIC": "Distributed Computing Systems",
                "DEADLINE": "2024-05-15",
                "ACADEMIC_LEVEL": "Master"
            },
            "LANGUAGE": {
                "TYPE": "English",
                "STYLE": "Academic"
            },
            "TEMPLATE": "Research Paper"
        }
    }
    
    async_response = requests.post(execute_url, json=request_data)
    
    if async_response.status_code != 200:
        logger.error(f"Full async error response: {async_response.text}")
        raise requests.exceptions.HTTPError(
            f"Async request failed with status {async_response.status_code}: {async_response.text}"
        )
    
    result = async_response.json()
    assert "workflow_id" in result
    
    # Check workflow status
    status_url = f"{server.base_url}/workflow/status/{result['workflow_id']}"
    max_retries = 5
    retry_delay = 2
    
    for _ in range(max_retries):
        status_response = requests.get(status_url)
        assert status_response.status_code == 200
        
        status_result = status_response.json()
        assert "status" in status_result
        
        if status_result["status"] == "completed":
            break
            
        time.sleep(retry_delay)
    
    assert status_result["status"] in ["completed", "running", "pending"]

def test_invalid_workflow(server):
    """Test handling of invalid workflow configuration"""
    url = f"{server.base_url}/workflow/execute"

    invalid_workflow_config = {
        "workflow": {
            "workflow_steps": []  # Empty workflow steps
        },
        "input_data": {}
    }

    try:
        response = requests.post(url, json=invalid_workflow_config)
        logger.debug(f"Invalid Workflow Response Status: {response.status_code}")
        logger.debug(f"Invalid Workflow Response Content: {response.text}")

        # Verify error response
        assert response.status_code == 422  # Validation error status code
        error_data = response.json()
        assert "detail" in error_data
        assert any("No workflow steps found" in str(detail) for detail in error_data["detail"])

    except Exception as e:
        logger.error(f"Invalid workflow request failed: {str(e)}")
        raise

if __name__ == "__main__":
    pytest.main([__file__])
