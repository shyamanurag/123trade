# ai/cloud_ml_config.py
import os

class CloudMLConfig:
    def __init__(self):
        # Detect cloud environment
        if os.getenv('CLOUD_ENV'):
            # Cloud environment settings
            self.model_storage_path = '/workspace/models'
        else:
            # Local environment settings
            self.model_storage_path = './models'
            
        # Memory limits for cloud
        self.max_memory_gb = 4
