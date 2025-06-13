#!/usr/bin/env python3
"""
AI Model Deployment Script for Professional Trading System
Deploy trained models to production serving infrastructure
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
import boto3
from botocore.exceptions import ClientError
import mlflow
import mlflow.sklearn
import mlflow.tensorflow
from mlflow.tracking import MlflowClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModelDeploymentManager:
    """Manage AI model deployment to production infrastructure"""
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.model_registry_url = os.getenv('MODEL_REGISTRY_URL')
        self.model_serving_endpoint = os.getenv('MODEL_SERVING_ENDPOINT')
        self.model_serving_token = os.getenv('MODEL_SERVING_TOKEN')
        self.mlflow_tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'sqlite:///mlflow.db')
        
        # Initialize MLflow
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        self.mlflow_client = MlflowClient()
        
        # Model configurations
        self.model_configs = {
            'price_prediction': {
                'model_type': 'ensemble',
                'framework': 'sklearn+tensorflow',
                'input_schema': 'trading_features_v1',
                'output_schema': 'price_prediction_v1',
                'resource_requirements': {
                    'cpu': '1000m',
                    'memory': '2Gi',
                    'gpu': '0'
                },
                'scaling': {
                    'min_replicas': 2,
                    'max_replicas': 10,
                    'target_cpu': 70
                }
            },
            'sentiment_analysis': {
                'model_type': 'classification',
                'framework': 'sklearn',
                'input_schema': 'text_input_v1',
                'output_schema': 'sentiment_output_v1',
                'resource_requirements': {
                    'cpu': '500m',
                    'memory': '1Gi',
                    'gpu': '0'
                },
                'scaling': {
                    'min_replicas': 1,
                    'max_replicas': 5,
                    'target_cpu': 60
                }
            },
            'risk_assessment': {
                'model_type': 'classification',
                'framework': 'sklearn',
                'input_schema': 'risk_features_v1',
                'output_schema': 'risk_assessment_v1',
                'resource_requirements': {
                    'cpu': '800m',
                    'memory': '1.5Gi',
                    'gpu': '0'
                },
                'scaling': {
                    'min_replicas': 2,
                    'max_replicas': 8,
                    'target_cpu': 70
                }
            },
            'portfolio_optimization': {
                'model_type': 'optimization',
                'framework': 'sklearn+scipy',
                'input_schema': 'portfolio_input_v1',
                'output_schema': 'portfolio_weights_v1',
                'resource_requirements': {
                    'cpu': '1500m',
                    'memory': '3Gi',
                    'gpu': '0'
                },
                'scaling': {
                    'min_replicas': 1,
                    'max_replicas': 3,
                    'target_cpu': 80
                }
            }
        }
    
    async def deploy_all_models(self) -> Dict[str, bool]:
        """Deploy all models to production serving infrastructure"""
        deployment_results = {}
        
        logger.info(f"Starting model deployment for environment: {self.environment}")
        
        for model_name, config in self.model_configs.items():
            try:
                logger.info(f"Deploying model: {model_name}")
                
                # Get latest model version
                model_version = await self._get_latest_model_version(model_name)
                
                if not model_version:
                    logger.warning(f"No trained model found for {model_name}")
                    deployment_results[model_name] = False
                    continue
                
                # Deploy model
                success = await self._deploy_single_model(model_name, model_version, config)
                deployment_results[model_name] = success
                
                if success:
                    logger.info(f"Successfully deployed {model_name} v{model_version}")
                else:
                    logger.error(f"Failed to deploy {model_name}")
                    
            except Exception as e:
                logger.error(f"Error deploying {model_name}: {e}")
                deployment_results[model_name] = False
        
        # Log deployment summary
        successful_deployments = sum(deployment_results.values())
        total_models = len(self.model_configs)
        
        logger.info(f"Deployment Summary: {successful_deployments}/{total_models} models deployed successfully")
        
        return deployment_results
    
    async def _get_latest_model_version(self, model_name: str) -> Optional[str]:
        """Get the latest version of a model from MLflow registry"""
        try:
            # Get registered model
            registered_model = self.mlflow_client.get_registered_model(model_name)
            
            # Get latest version in production stage
            latest_versions = self.mlflow_client.get_latest_versions(
                model_name, 
                stages=["Production"]
            )
            
            if latest_versions:
                return latest_versions[0].version
            
            # Fallback to latest version in any stage
            all_versions = self.mlflow_client.get_latest_versions(model_name)
            if all_versions:
                return all_versions[0].version
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting model version for {model_name}: {e}")
            return None
    
    async def _deploy_single_model(self, model_name: str, version: str, config: Dict) -> bool:
        """Deploy a single model to serving infrastructure"""
        try:
            deployment_config = {
                'model_name': model_name,
                'model_version': version,
                'environment': self.environment,
                'framework': config['framework'],
                'resource_requirements': config['resource_requirements'],
                'scaling_config': config['scaling'],
                'input_schema': config['input_schema'],
                'output_schema': config['output_schema'],
                'deployment_timestamp': datetime.now().isoformat(),
                'metadata': {
                    'deployed_by': 'ci_cd_pipeline',
                    'model_type': config['model_type']
                }
            }
            
            # Deploy based on serving infrastructure type
            if self._is_kubernetes_deployment():
                return await self._deploy_to_kubernetes(model_name, deployment_config)
            elif self._is_cloud_deployment():
                return await self._deploy_to_cloud(model_name, deployment_config)
            else:
                return await self._deploy_to_local_serving(model_name, deployment_config)
                
        except Exception as e:
            logger.error(f"Error in single model deployment for {model_name}: {e}")
            return False
    
    def _is_kubernetes_deployment(self) -> bool:
        """Check if deployment target is Kubernetes"""
        return self.model_serving_endpoint and 'k8s' in self.model_serving_endpoint
    
    def _is_cloud_deployment(self) -> bool:
        """Check if deployment target is cloud (AWS SageMaker, etc.)"""
        return self.model_serving_endpoint and any(
            cloud in self.model_serving_endpoint 
            for cloud in ['amazonaws.com', 'sagemaker', 'azure', 'gcp']
        )
    
    async def _deploy_to_kubernetes(self, model_name: str, config: Dict) -> bool:
        """Deploy model to Kubernetes cluster"""
        try:
            # Create Kubernetes deployment manifest
            k8s_manifest = await self._create_k8s_manifest(model_name, config)
            
            # Apply manifest using kubectl
            manifest_file = f"/tmp/{model_name}-deployment.yaml"
            with open(manifest_file, 'w') as f:
                f.write(k8s_manifest)
            
            import subprocess
            result = subprocess.run([
                'kubectl', 'apply', '-f', manifest_file,
                '--namespace', f'trading-{self.environment}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Kubernetes deployment successful for {model_name}")
                
                # Wait for deployment to be ready
                await self._wait_for_k8s_deployment(model_name)
                return True
            else:
                logger.error(f"Kubernetes deployment failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error deploying to Kubernetes: {e}")
            return False
    
    async def _create_k8s_manifest(self, model_name: str, config: Dict) -> str:
        """Create Kubernetes deployment manifest for model serving"""
        namespace = f"trading-{self.environment}"
        
        manifest = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {model_name}-serving
  namespace: {namespace}
  labels:
    app: {model_name}
    component: model-serving
    environment: {self.environment}
spec:
  replicas: {config['scaling_config']['min_replicas']}
  selector:
    matchLabels:
      app: {model_name}
      component: model-serving
  template:
    metadata:
      labels:
        app: {model_name}
        component: model-serving
        environment: {self.environment}
    spec:
      containers:
      - name: model-server
        image: tensorflow/serving:2.15.0
        ports:
        - containerPort: 8501
          name: http
        - containerPort: 8500
          name: grpc
        env:
        - name: MODEL_NAME
          value: "{model_name}"
        - name: MODEL_BASE_PATH
          value: "/models/{model_name}"
        resources:
          requests:
            cpu: {config['resource_requirements']['cpu']}
            memory: {config['resource_requirements']['memory']}
          limits:
            cpu: {config['resource_requirements']['cpu']}
            memory: {config['resource_requirements']['memory']}
        volumeMounts:
        - name: model-storage
          mountPath: /models
        livenessProbe:
          httpGet:
            path: /v1/models/{model_name}
            port: 8501
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /v1/models/{model_name}
            port: 8501
          initialDelaySeconds: 15
          periodSeconds: 10
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: models-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: {model_name}-service
  namespace: {namespace}
spec:
  selector:
    app: {model_name}
    component: model-serving
  ports:
  - name: http
    port: 8501
    targetPort: 8501
  - name: grpc
    port: 8500
    targetPort: 8500
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {model_name}-hpa
  namespace: {namespace}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {model_name}-serving
  minReplicas: {config['scaling_config']['min_replicas']}
  maxReplicas: {config['scaling_config']['max_replicas']}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {config['scaling_config']['target_cpu']}
"""
        return manifest
    
    async def _wait_for_k8s_deployment(self, model_name: str, timeout: int = 300) -> bool:
        """Wait for Kubernetes deployment to be ready"""
        import subprocess
        import time
        
        start_time = time.time()
        namespace = f"trading-{self.environment}"
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run([
                    'kubectl', 'rollout', 'status', 
                    f'deployment/{model_name}-serving',
                    '--namespace', namespace,
                    '--timeout=60s'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"Deployment {model_name} is ready")
                    return True
                    
            except Exception as e:
                logger.warning(f"Waiting for deployment: {e}")
            
            await asyncio.sleep(10)
        
        logger.error(f"Timeout waiting for {model_name} deployment")
        return False
    
    async def _deploy_to_cloud(self, model_name: str, config: Dict) -> bool:
        """Deploy model to cloud serving platform (AWS SageMaker, etc.)"""
        try:
            if 'sagemaker' in self.model_serving_endpoint:
                return await self._deploy_to_sagemaker(model_name, config)
            else:
                logger.warning(f"Cloud deployment not implemented for {self.model_serving_endpoint}")
                return False
                
        except Exception as e:
            logger.error(f"Error deploying to cloud: {e}")
            return False
    
    async def _deploy_to_sagemaker(self, model_name: str, config: Dict) -> bool:
        """Deploy model to AWS SageMaker"""
        try:
            import boto3
            
            sagemaker_client = boto3.client('sagemaker')
            
            # Create SageMaker model
            model_response = sagemaker_client.create_model(
                ModelName=f"{model_name}-{self.environment}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                PrimaryContainer={
                    'Image': self._get_sagemaker_image(config['framework']),
                    'ModelDataUrl': f"s3://trading-models/{model_name}/{config['model_version']}/model.tar.gz",
                    'Environment': {
                        'SAGEMAKER_PROGRAM': 'inference.py',
                        'SAGEMAKER_SUBMIT_DIRECTORY': f"s3://trading-models/{model_name}/code/"
                    }
                },
                ExecutionRoleArn=os.getenv('SAGEMAKER_EXECUTION_ROLE_ARN')
            )
            
            logger.info(f"SageMaker model created: {model_response['ModelArn']}")
            
            # Create endpoint configuration
            endpoint_config_response = sagemaker_client.create_endpoint_config(
                EndpointConfigName=f"{model_name}-{self.environment}-config",
                ProductionVariants=[
                    {
                        'VariantName': 'primary',
                        'ModelName': model_response['ModelArn'].split('/')[-1],
                        'InitialInstanceCount': config['scaling_config']['min_replicas'],
                        'InstanceType': self._get_sagemaker_instance_type(config['resource_requirements']),
                        'InitialVariantWeight': 1
                    }
                ]
            )
            
            # Create or update endpoint
            endpoint_name = f"{model_name}-{self.environment}"
            try:
                sagemaker_client.create_endpoint(
                    EndpointName=endpoint_name,
                    EndpointConfigName=f"{model_name}-{self.environment}-config"
                )
                logger.info(f"SageMaker endpoint created: {endpoint_name}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationException':
                    # Endpoint exists, update it
                    sagemaker_client.update_endpoint(
                        EndpointName=endpoint_name,
                        EndpointConfigName=f"{model_name}-{self.environment}-config"
                    )
                    logger.info(f"SageMaker endpoint updated: {endpoint_name}")
                else:
                    raise
            
            return True
            
        except Exception as e:
            logger.error(f"Error deploying to SageMaker: {e}")
            return False
    
    def _get_sagemaker_image(self, framework: str) -> str:
        """Get appropriate SageMaker Docker image for framework"""
        framework_images = {
            'sklearn': '246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-scikit-learn:1.0-1-cpu-py3',
            'tensorflow': '246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-tensorflow-serving:2.8-cpu',
            'sklearn+tensorflow': '246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-tensorflow-serving:2.8-cpu'
        }
        return framework_images.get(framework, framework_images['sklearn'])
    
    def _get_sagemaker_instance_type(self, resources: Dict) -> str:
        """Get appropriate SageMaker instance type based on resource requirements"""
        memory_mb = int(resources['memory'].rstrip('Gi')) * 1024
        cpu_cores = int(resources['cpu'].rstrip('m')) / 1000
        
        if memory_mb <= 2048 and cpu_cores <= 1:
            return 'ml.t3.medium'
        elif memory_mb <= 4096 and cpu_cores <= 2:
            return 'ml.t3.large'
        elif memory_mb <= 8192 and cpu_cores <= 4:
            return 'ml.m5.xlarge'
        else:
            return 'ml.m5.2xlarge'
    
    async def _deploy_to_local_serving(self, model_name: str, config: Dict) -> bool:
        """Deploy model to local serving infrastructure"""
        try:
            # Create deployment request
            deployment_data = {
                'model_name': model_name,
                'model_config': config,
                'environment': self.environment
            }
            
            # Send deployment request to local serving API
            headers = {
                'Authorization': f'Bearer {self.model_serving_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.model_serving_endpoint}/deploy",
                json=deployment_data,
                headers=headers,
                timeout=300
            )
            
            if response.status_code == 200:
                logger.info(f"Local deployment successful for {model_name}")
                return True
            else:
                logger.error(f"Local deployment failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error deploying to local serving: {e}")
            return False
    
    async def validate_deployments(self, models: List[str]) -> Dict[str, bool]:
        """Validate that deployed models are working correctly"""
        validation_results = {}
        
        for model_name in models:
            try:
                # Test model endpoint
                test_result = await self._test_model_endpoint(model_name)
                validation_results[model_name] = test_result
                
                if test_result:
                    logger.info(f"Model {model_name} validation passed")
                else:
                    logger.error(f"Model {model_name} validation failed")
                    
            except Exception as e:
                logger.error(f"Error validating {model_name}: {e}")
                validation_results[model_name] = False
        
        return validation_results
    
    async def _test_model_endpoint(self, model_name: str) -> bool:
        """Test model endpoint with sample data"""
        try:
            # Get sample test data
            test_data = self._get_test_data(model_name)
            
            # Make prediction request
            endpoint_url = f"{self.model_serving_endpoint}/predict/{model_name}"
            headers = {
                'Authorization': f'Bearer {self.model_serving_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                endpoint_url,
                json={'data': test_data},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Validate response structure
                return 'predictions' in result and len(result['predictions']) > 0
            else:
                logger.error(f"Endpoint test failed for {model_name}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error testing endpoint for {model_name}: {e}")
            return False
    
    def _get_test_data(self, model_name: str) -> List[List[float]]:
        """Get sample test data for model validation"""
        # Return appropriate test data based on model type
        test_data_samples = {
            'price_prediction': [[1.0, 2.0, 3.0, 4.0, 5.0] * 10],  # 50 features
            'sentiment_analysis': [["This is a positive trading signal"]],
            'risk_assessment': [[0.5, 0.3, 0.8, 0.2, 0.9] * 8],  # 40 features
            'portfolio_optimization': [[0.1, 0.2, 0.15, 0.25, 0.3]]  # 5 assets
        }
        
        return test_data_samples.get(model_name, [[1.0, 2.0, 3.0]])

async def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description='Deploy AI models to production serving infrastructure')
    parser.add_argument('--environment', 
                       choices=['staging', 'production'], 
                       default='production',
                       help='Deployment environment')
    parser.add_argument('--models', 
                       nargs='+',
                       help='Specific models to deploy (optional)')
    parser.add_argument('--validate', 
                       action='store_true',
                       help='Validate deployments after completion')
    
    args = parser.parse_args()
    
    # Initialize deployment manager
    deployment_manager = ModelDeploymentManager(environment=args.environment)
    
    try:
        # Deploy models
        if args.models:
            # Deploy specific models
            deployment_results = {}
            for model_name in args.models:
                if model_name in deployment_manager.model_configs:
                    config = deployment_manager.model_configs[model_name]
                    version = await deployment_manager._get_latest_model_version(model_name)
                    if version:
                        success = await deployment_manager._deploy_single_model(model_name, version, config)
                        deployment_results[model_name] = success
                    else:
                        logger.error(f"No version found for model {model_name}")
                        deployment_results[model_name] = False
                else:
                    logger.error(f"Unknown model: {model_name}")
                    deployment_results[model_name] = False
        else:
            # Deploy all models
            deployment_results = await deployment_manager.deploy_all_models()
        
        # Validate deployments if requested
        if args.validate:
            successful_models = [name for name, success in deployment_results.items() if success]
            if successful_models:
                logger.info("Validating deployed models...")
                validation_results = await deployment_manager.validate_deployments(successful_models)
                
                # Log validation summary
                passed_validations = sum(validation_results.values())
                total_validations = len(validation_results)
                logger.info(f"Validation Summary: {passed_validations}/{total_validations} models passed validation")
        
        # Exit with appropriate code
        successful_deployments = sum(deployment_results.values())
        total_deployments = len(deployment_results)
        
        if successful_deployments == total_deployments:
            logger.info("🚀 All model deployments completed successfully!")
            sys.exit(0)
        else:
            logger.error(f"❌ {total_deployments - successful_deployments} deployments failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Deployment failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 