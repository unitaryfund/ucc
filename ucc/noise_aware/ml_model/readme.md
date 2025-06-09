## Create env & installation
```
conda create -n ucc_ai python=3.12
conda activate ucc_ai


pip install ucc
cd ucc
uv sync --all-extras --all-groups
pip install torch
pip install tqdm
```


## Generate Random qasm2 Circuit
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

## My attempt with 8gb intel i8 rtx1050
```
python ucc/noise_aware/ml_model/generate_dataset.py ^
    --num-samples 5000 ^
    --max-qubits 15 ^
    --min-qubits 4 ^
    --output-file C:/Users/junli/ucc/ucc/noise_aware/ml_model/diverse_fidelity_dataset.json ^
    --max-seq-len 512
```
Dataset Composition:
- EfficientSU2: 1211 samples (24.2%)
- random: 1251 samples (25.0%)
- qft: 2034 samples (40.7%)
- qv: 504 samples (10.1%)

model-dim * n-heads must be the same as embed_dim
```
python ucc/noise_aware/ml_model/train_model.py ^
    --dataset-path C:/Users/junli/ucc/ucc/noise_aware/ml_model/diverse_fidelity_dataset.json ^
    --output-dir C:/Users/junli/ucc/ucc/noise_aware/ml_model/ ^
    --epochs 20 ^
    --batch-size 32 ^
    --learning-rate 0.00001 ^
    --model-dim 128 ^
    --n-heads 8 ^
    --n-layers 8 ^
    --max-seq-len 512
```
