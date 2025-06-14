import os
import sys

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

print("Django setup successful")

try:
    from mlmodels.dkn.model import DKNConfig, DKNModel
    print("DKN model import successful")
except Exception as e:
    print(f"DKN model import failed: {e}")

try:
    from mlmodels.dkn.data_processor import DKNDataProcessor, DKNDataset
    print("DKN data_processor import successful")
except Exception as e:
    print(f"DKN data_processor import failed: {e}")

try:
    from mlmodels.dkn.trainer import AdvancedDKNTrainer, train_dkn_model
    print("DKN trainer import successful")
except Exception as e:
    print(f"DKN trainer import failed: {e}")

print("All imports completed")
