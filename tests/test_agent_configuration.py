import unittest
import json
import os
import tempfile
import logging
from typing import Dict, Any, Union, Optional

import pandas as pd
import numpy as np

from agentflow.agents.agent import Agent
from agentflow.agents.agent_factory import AgentFactory
from agentflow.transformations.pipeline import TransformationPipeline
from agentflow.transformations.advanced_strategies import (
    OutlierRemovalStrategy,
    FeatureEngineeringStrategy,
    TextTransformationStrategy
)
from agentflow.agents.agent_types import AgentConfig, AgentType, AgentMode
from agentflow.core.config import ModelConfig
from agentflow.core.workflow_types import WorkflowConfig

class TestAgentConfiguration(unittest.TestCase):
    """Test cases for agent configuration and initialization."""

    def setUp(self):
        """Set up test cases."""
        # Define agent classes
        class ResearchAgent(Agent):
            def __init__(self, config: Union[Dict[str, Any], str, AgentConfig]):
                super().__init__(config)
                self.research_domains = self.domain_config.get("research_domains", [])

            def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
                return {"result": "research_processed"}

        class DataScienceAgent(Agent):
            def __init__(self, config: Union[Dict[str, Any], str, AgentConfig]):
                super().__init__(config)
                self.metrics = self.domain_config.get("metrics", [])
                self.model_type = self.domain_config.get("model_type")

            def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
                return {"result": "data_science_processed"}

        # Register agent types
        AgentFactory.register_agent(AgentType.RESEARCH.value, ResearchAgent)
        AgentFactory.register_agent(AgentType.DATA_SCIENCE.value, DataScienceAgent)

        # Set up configurations
        self.research_config = {
            "AGENT": {
                "type": AgentType.RESEARCH.value,
                "name": "QuantumResearchAgent",
                "mode": AgentMode.SEQUENTIAL.value,
                "version": "1.0.0"
            },
            "MODEL": {
                "provider": "default",
                "name": "default",
                "temperature": 0.7
            },
            "WORKFLOW": {
                "name": "research_workflow",
                "max_iterations": 10,
                "timeout": 300,
                "steps": []
            },
            "TRANSFORMATIONS": {
                "input": [
                    {
                        "type": "outlier_removal",
                        "params": {
                            "method": "z_score",
                            "threshold": 3.0
                        }
                    }
                ]
            },
            "DOMAIN_CONFIG": {
                "research_domains": ["quantum computing"]
            }
        }

        self.data_science_config = {
            "AGENT": {
                "type": AgentType.DATA_SCIENCE.value,
                "name": "FinancialDataAgent",
                "mode": AgentMode.SEQUENTIAL.value,
                "version": "1.0.0"
            },
            "MODEL": {
                "provider": "default",
                "name": "default",
                "temperature": 0.7
            },
            "WORKFLOW": {
                "name": "data_science_workflow",
                "max_iterations": 10,
                "timeout": 300,
                "steps": []
            },
            "TRANSFORMATIONS": {
                "input": [
                    {
                        "type": "feature_engineering",
                        "params": {
                            "strategy": "polynomial",
                            "degree": 2
                        }
                    }
                ]
            },
            "DOMAIN_CONFIG": {
                "metrics": ["r2_score", "mse"],
                "model_type": "regression"
            }
        }

    def test_research_agent_configuration(self):
        """Test research agent configuration and initialization."""
        # Create agent using factory
        research_agent = AgentFactory.create_agent(self.research_config)

        # Verify agent configuration
        self.assertEqual(research_agent.name, "QuantumResearchAgent")
        self.assertEqual(research_agent.type, AgentType.RESEARCH.value)
        self.assertEqual(research_agent.mode, "sequential")
        self.assertEqual(research_agent.research_domains, ["quantum computing"])

    def test_data_science_agent_configuration(self):
        """Test data science agent configuration and initialization."""
        # Create agent using factory
        data_science_agent = AgentFactory.create_agent(self.data_science_config)

        # Verify agent configuration
        self.assertEqual(data_science_agent.name, "FinancialDataAgent")
        self.assertEqual(data_science_agent.type, AgentType.DATA_SCIENCE.value)
        self.assertEqual(data_science_agent.mode, "sequential")
        self.assertEqual(data_science_agent.metrics, ["r2_score", "mse"])
        self.assertEqual(data_science_agent.model_type, "regression")

    def test_agent_factory_registration(self):
        """Test agent factory registration and agent creation."""
        # Register a custom agent type
        class CustomAgent(Agent):
            def __init__(self, config: Union[Dict[str, Any], str, AgentConfig]):
                super().__init__(config)
                self.custom_attribute = "custom"

            def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
                return {"result": "custom_processed"}

        AgentFactory.register_agent(AgentType.CUSTOM.value, CustomAgent)

        # Create a configuration for the custom agent
        custom_config = {
            "AGENT": {
                "type": AgentType.CUSTOM.value,
                "name": "CustomTestAgent",
                "mode": AgentMode.SEQUENTIAL.value,
                "version": "1.0.0"
            },
            "MODEL": {
                "provider": "default",
                "name": "default",
                "temperature": 0.7
            },
            "WORKFLOW": {
                "name": "custom_workflow",
                "max_iterations": 10,
                "timeout": 300,
                "steps": []
            }
        }

        # Create custom agent
        custom_agent = AgentFactory.create_agent(custom_config)

        # Verify agent configuration and functionality
        self.assertEqual(custom_agent.name, "CustomTestAgent")
        self.assertEqual(custom_agent.type, AgentType.CUSTOM.value)
        self.assertEqual(custom_agent.mode, "sequential")
        self.assertEqual(custom_agent.custom_attribute, "custom")

        # Test processing
        result = custom_agent.process({"input": "test"})
        self.assertEqual(result, {"result": "custom_processed"})

    def test_transformation_pipeline(self):
        """Test transformation pipeline configuration and execution."""
        # Create a sample transformation pipeline
        pipeline = TransformationPipeline()

        # Add strategies
        outlier_strategy = OutlierRemovalStrategy(method="z_score", threshold=3.0)
        feature_strategy = FeatureEngineeringStrategy(strategy="polynomial", degree=2)
        text_strategy = TextTransformationStrategy(method="normalize", remove_stopwords=True)

        pipeline.add_strategy(outlier_strategy)
        pipeline.add_strategy(feature_strategy)
        pipeline.add_strategy(text_strategy)

        # Verify pipeline configuration
        self.assertEqual(len(pipeline.strategies), 3)

        # Sample data for transformation
        sample_data = pd.DataFrame({
            'A': [1, 2, 100, 4, 5],
            'B': ['hello world', 'test data', 'another example', 'text processing', 'nlp']
        })

        # Transform data
        transformed_data = pipeline.transform(sample_data)

        # Verify transformation results
        self.assertIsInstance(transformed_data, pd.DataFrame)
        self.assertTrue(transformed_data.shape[1] > sample_data.shape[1])

if __name__ == '__main__':
    unittest.main()
