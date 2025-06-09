
## Generate Random qasm2 Circuit
ROOT = "C:/Users/junli/ucc/ucc/noise_aware/ml_model/"
```
# Generate 5000 samples with default settings (max 15 qubits)
python scripts/generate_dataset.py --num-samples 5000

# Generate a smaller test dataset with smaller circuits
python ucc\noise_aware\ml_model\generate_dataset.py --num-samples 1000 --max-qubits 8 --output-file small_test_dataset.json
```

## Train
```
# Create the output directory first
mkdir -p trained_models

# Run the training script
python ucc\noise_aware\ml_model\train_model.py --dataset-path diverse_fidelity_dataset.json --epochs 50 --batch-size 128 --learning-rate 0.0001
```

## My attempt
```
python ucc\noise_aware\ml_model\generate_dataset.py --num-samples 1000 --max-qubits 8 --output-file C:/Users/junli/ucc/ucc/noise_aware/ml_model/small_diverse_fidelity_dataset.json

python ucc\noise_aware\ml_model\train_model.py --dataset-path C:/Users/junli/ucc/ucc/noise_aware/ml_model/small_diverse_fidelity_dataset.json --output-dir C:/Users/junli/ucc/ucc/noise_aware/ml_model/ --epochs 50 --batch-size 128 --learning-rate 0.0001
```
